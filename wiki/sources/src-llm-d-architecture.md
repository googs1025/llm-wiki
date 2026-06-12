---
title: llm-d 架构与设计思路分析
tags: [architecture, llm-serving, kubernetes, inference, ai-infra]
date: 2026-06-12
sources: [llm-d-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[llm-inference-serving-project-map]], [[vllm]], [[kubernetes]], [[kv-cache-offload]], [[disaggregated-serving]], [[dynamo]]]
---

# llm-d 架构与设计思路分析

`llm-d/llm-d` 是 Kubernetes 上的分布式 LLM serving stack 总入口。它本身更像 docs/guides/recipes/architecture hub，把 `llm-d-router`、Gateway API Inference Extension 的 `InferencePool`、vLLM/SGLang model server、KV cache management、P/D disaggregation、latency predictor、batch gateway、autoscaling 等组件组织成 well-lit paths。

## 核心架构图

```text
┌──────────────────────────── client / gateway ────────────────────────────────┐
│ OpenAI-compatible request · Gateway API · Envoy/agentgateway/Istio/kgateway    │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ llm-d Router                                                                  │
│ proxy + Endpoint Picker(EPP): load/prefix/SLO aware scheduling                │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ InferencePool / variants      │  │ advanced components                         │
│ model server pods             │  │ KV index/offload · P/D · WVA · batch         │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ vLLM / SGLang on GPU/TPU/HPU clusters, with reproducible guide recipes         │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `docs/architecture/**` | 核心架构文档：Router、InferencePool、Model Server、KV cache、disaggregation、autoscaling、batch。 |
| `guides/**` | 可复现实验/部署路径：optimized baseline、P/D、wide EP、tiered prefix cache、flow control、batch、observability。 |
| `docs/proposals/**` | 仍在演进的设计：autoscaler、batch gateway、planner、resilience operator 等。 |
| `release/**`, `guides/recipes/**` | 发行和 Kustomize/Helm recipe 入口。 |

## 关键数据流

1. 请求经 Gateway API 进入 Router；proxy 用 ext-proc 咨询 EPP。
2. EPP 按 InferencePool 发现可用 model server pods，并结合 load、KV affinity、priority/SLO profile 打分。
3. 高级路径中，P/D disaggregation 先选 prefill 再选 decode，KV cache 通过 index/offload 提高 reuse。

## 设计决策

- llm-d 把“架构标准化 + 组件拆分 + well-lit path”作为主要交付，而不是一个大二进制。
- 它承认 model server 是 vLLM/SGLang 等外部 engine，llm-d 只做其上的 orchestration 和优化。
- InferencePool 是核心抽象：像 LLM-optimized Service，用 labels/variants 表达模型、角色和性能差异。

## 对比定位

和 AIBrix 相比，llm-d 更标准化/生态化，组件分仓；和 [[dynamo]] 相比，它更 Kubernetes/Gateway API first；和 [[vllm]]/[[sglang]] 相比，它不是 engine，而是 engine 之上的 serving system。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
