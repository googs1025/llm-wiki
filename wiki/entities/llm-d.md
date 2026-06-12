---
title: llm-d
tags: [entity, llm-serving, kubernetes, gateway-api, inference-routing]
date: 2026-06-12
sources: [llm-d-architecture-analysis.md, llm-d-router-architecture-analysis.md, llm-d-kv-cache-architecture-analysis.md]
related: [[inference-routing]], [[kv-cache-offload]], [[model-serving-operator]], [[gateway-api]], [[vllm]]
---

# llm-d

CNCF Sandbox 分布式 LLM inference serving stack，围绕 Router/EPP、InferencePool、model server、KV cache management、P/D disaggregation 和 autoscaling 组织。详见 [[src-llm-d-architecture]]。

## 架构边界

llm-d 是 serving system，不是推理 engine。`llm-d-router` 负责 LLM-aware entry point，`llm-d-kv-cache` 负责 KV cache aware routing/indexing library。它与 [[aibrix]] 同属 K8s serving control plane，与 [[dynamo]] 同属分布式 serving 系统，但更贴近 Gateway API / InferencePool 标准化路线。

## 选型判断

| 需求 | 关注点 |
|---|---|
| Gateway API/InferencePool 路由 | [[src-llm-d-router-architecture]] |
| KV cache aware route/index | [[src-llm-d-kv-cache-architecture]] |
| 完整 K8s serving stack | [[src-llm-d-architecture]] |
