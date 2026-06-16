---
title: llm-d
tags: [entity, llm-serving, kubernetes, gateway-api, inference-routing]
date: 2026-06-12
sources: [llm-d-architecture-analysis.md, llm-d-router-architecture-analysis.md, llm-d-kv-cache-architecture-analysis.md, llm-d-batch-gateway-architecture-analysis.md, llm-d-benchmark-architecture-analysis.md, llm-d-workload-variant-autoscaler-architecture-analysis.md, llm-d-inference-sim-architecture-analysis.md]
related: [[inference-routing]], [[kv-cache-offload]], [[model-serving-operator]], [[gateway-api]], [[vllm]], [[llm-d-router]], [[llm-d-kv-cache]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]]
---

# llm-d

CNCF Sandbox 分布式 LLM inference serving stack，围绕 Router/EPP、InferencePool、model server、KV cache management、P/D disaggregation、autoscaling、batch、benchmark 和 simulator 组织。详见 [[src-llm-d-architecture]]。

## 架构边界

llm-d 是 serving system，不是推理 engine。[[llm-d-router]] 负责 LLM-aware entry point，[[llm-d-kv-cache]] 负责 KV cache aware routing/indexing library；外围项目继续补齐 [[llm-d-batch-gateway]]、[[llm-d-benchmark]]、[[llm-d-workload-variant-autoscaler]] 和 [[llm-d-inference-sim]]。它与 [[aibrix]] 同属 K8s serving control plane，与 [[dynamo]] 同属分布式 serving 系统，但更贴近 Gateway API / InferencePool 标准化路线。

## 选型判断

| 需求 | 关注点 |
|---|---|
| Gateway API/InferencePool 路由 | [[llm-d-router]] / [[src-llm-d-router-architecture]] |
| KV cache aware route/index | [[llm-d-kv-cache]] / [[src-llm-d-kv-cache-architecture]] |
| 完整 K8s serving stack | [[src-llm-d-architecture]] |
| OpenAI Batch API / 离线推理 | [[src-llm-d-batch-gateway-architecture]] |
| serving benchmark / 实验复现 | [[src-llm-d-benchmark-architecture]] |
| 多 variant autoscaling | [[src-llm-d-workload-variant-autoscaler-architecture]] |
| 无 GPU 控制面与路由验证 | [[src-llm-d-inference-sim-architecture]] |
