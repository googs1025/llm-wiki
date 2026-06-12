---
title: llm-d KV Cache 架构与设计思路分析
tags: [architecture, kv-cache, llm-serving, vllm, ai-infra]
date: 2026-06-12
sources: [llm-d-kv-cache-architecture-analysis.md]
related: [[[kv-cache-offload]], [[disaggregated-serving]], [[llm-serving-engine-selection-map]], [[vllm]], [[dynamo]], [[kubernetes]]]
---

# llm-d KV Cache 架构与设计思路分析

`llm-d/llm-d-kv-cache` 是 llm-d 的 KV cache 智能路由/索引库。它不直接跑模型，而是从 vLLM/SGLang KV events 获取 block locality，把 prompt/token block 映射到 pod/tier 命中情况，给 router/scorer 返回 cache-hit 分数；同时包含 tokenizer gRPC、KV index service examples、Valkey/Redis/in-memory backend、PVC/FS connectors。

## 核心架构图

```text
┌──────────────────────────── scheduler / router ──────────────────────────────┐
│ Score(prompt or tokens, candidate pods)                                       │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ kvcache.Indexer                                                               │
│ token processing · block key generation · scorer · metrics/tracing            │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │ read path                     │ write path
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ kvblock.Index                 │  │ kvevents.Pool / subscribers                 │
│ in-memory · Redis/Valkey      │  │ vLLM/SGLang adapters · ZMQ event stream     │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ vLLM/SGLang pods: KV block create/evict events, GPU/CPU/FS/object tiers       │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `pkg/kvcache/**` | Indexer、backend、score types、metrics collector。 |
| `pkg/kvcache/kvblock/**` | 核心索引：in-memory、Redis/Valkey、cost-aware memory、HMA、token processor。 |
| `pkg/kvevents/**` | 事件订阅池、ZMQ subscriber、vLLM/SGLang adapter、event realignment。 |
| `pkg/tokenization/**`, `api/tokenizerpb/**` | tokenizer pool/service，提供 Tokenize/RenderChatTemplate/RenderCompletion 等接口。 |

## 关键数据流

1. 写路径：vLLM pod 产生 KVEvents，subscriber pool 消费后经 engine adapter 标准化，更新 kvblock index。
2. 读路径：router/scorer 传入 prompt/tokens 和候选 pods，Indexer 生成 block keys，查询哪些 pods/tier 命中。
3. score 返回每个 pod 的 KV hit 分数，供 Router 与 load/SLO 等其他 scorers 融合。

## 设计决策

- 把 KV cache locality 做成独立库/服务，是 llm-d 拆分式架构的关键。
- 事件驱动比主动轮询更接近实时，但依赖 vLLM/SGLang event 格式稳定。
- 索引 backend 可本地/Redis/Valkey，方便从单机实验到分布式 router。

## 对比定位

和 [[dynamo]] 的 KVBM/KV offload 相比，llm-d-kv-cache 更像 router 可用的 KV locality index；和 AIBrix 的 `pkg/cache` 相比，它独立成库并提供 tokenizer/proto/examples；和 semantic router 相比，它按 token block/cache 命中路由，不按语义意图路由。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
