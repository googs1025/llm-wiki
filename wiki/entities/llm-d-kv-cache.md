---
title: llm-d KV Cache
tags: [entity, llm-serving, kv-cache, inference-routing, llm-d]
date: 2026-06-16
sources: [llm-d-kv-cache-architecture-analysis.md]
related: [[llm-d]], [[llm-d-router]], [[kv-cache-offload]], [[inference-routing]], [[vllm]], [[sglang]], [[dynamo]]
---

# llm-d KV Cache

llm-d KV Cache 是 [[llm-d]] 的 KV cache locality index / scoring library。它从 vLLM/SGLang KV events 获取 block create/evict 信号，把 prompt/token block 映射到 pod 或 tier 的命中情况，再给 [[llm-d-router]] 的 scorer 返回 cache-hit 分数。详见 [[src-llm-d-kv-cache-architecture]]。

## 架构边界

它不负责模型执行，也不等同于 [[kv-cache-offload]]。它更像一个 router 可查询的 KV locality control plane：把 cache event、tokenization、block key、backend index 和 scoring 串起来。

## 核心抽象

| 抽象 | 作用 |
|---|---|
| `kvcache.Indexer` | 根据 prompt/tokens 生成 block keys，并对候选 pods 评分。 |
| `kvblock.Index` | KV block 索引，支持 in-memory、Redis/Valkey 等 backend。 |
| `kvevents` | 订阅 vLLM/SGLang KV events 并标准化为 index 更新。 |
| tokenizer service | 提供 Tokenize / RenderChatTemplate / RenderCompletion 等接口。 |
| PVC/FS connectors | 为不同 KV 存储或文件路径接入提供示例。 |

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 想做 KV-aware endpoint routing | 适合，核心就是把 KV locality 变成 scorer 输入。 |
| 想实现多级 KV offload | 先看 [[dynamo]] / [[kv-cache-offload]]；llm-d KV Cache 更偏索引和评分。 |
| 想验证无 GPU router 行为 | 配合 [[llm-d-inference-sim]] 使用。 |
| 只关心单机 engine 内 KV 管理 | 先看 [[vllm]] / [[sglang]]。 |

## 选型提示

[[llm-d-kv-cache]] 说明 KV cache 在分布式 serving 中已经从 engine 内部细节变成路由信号。选型时要分清三层：engine 内 block 管理、跨 worker KV transfer/offload、router 查询 KV locality。
