---
title: Dynamo
tags: [entity, ai-infra, llm-inference, llm-serving, distributed-serving, kv-cache, kubernetes, autoscaling, nvidia]
date: 2026-09-13
sources: [dynamo-architecture-analysis.md]
related: [[llm-inference]], [[inference-routing]], [[disaggregated-serving]], [[kv-cache-offload]], [[model-serving-operator]], [[ai-gateway]], [[sglang]], [[vllm]]
---

# Dynamo

NVIDIA 开源的数据中心级 LLM 推理编排层。Dynamo 位于推理 engine 之上，负责入口、路由、P/D 协调、KV 传输、容量控制、Kubernetes 部署与故障连续性；不替代 SGLang、vLLM 或 TensorRT-LLM 的 GPU 执行内核。

## 架构边界

Frontend / Gateway EPP → KV-aware Router → backend workers 是请求路径；DGDR / Profiler / AIConfigurator → DGD / DCD → Operator 是部署路径；Planner → connector / Operator 是运行时容量路径。三条路径通过 Runtime 的 discovery、request 和 event planes 连接。

## 什么时候用

- 多 GPU、多节点或长上下文在线推理。
- 需要独立扩缩 prefill/decode、KV-aware routing 或高速 KV transfer。
- 需要按 TTFT/ITL/SLA 和 TCO 做容量规划与自动扩缩。
- 需要 Gateway API 入口、请求迁移、canary health check 或 topology-aware deployment。

## 什么时候不用

单模型、单 GPU、没有跨节点协调和 SLA 控制需求时，直接使用 [[vllm]] 或 [[sglang]] 更简单。若只需要标准 Kubernetes 模型生命周期而不需要 Dynamo 的 P/D、KV 和 Planner，应优先比较 [[kserve]]、[[ome]] 等 Operator。

## 与同类比较

| 项目 | 主要边界 | 与 Dynamo 的差异 |
|---|---|---|
| [[vllm]] / [[sglang]] | 推理 engine | 更靠近单机/多 GPU 执行与 batching |
| [[llm-d]] | K8s inference stack、router、pool | 更强调云原生入口与组件生态，Dynamo 更强调 engine 上方的端到端编排 |
| [[gateway-api-inference-extension]] | Gateway API inference endpoint picking | 可作为 Dynamo 的入口承载，不能替代完整 P/D/KV/Planner |
| [[kserve]] / [[ome]] | 模型服务 CRD/operator | 更偏声明式生命周期，Dynamo 提供更深的 serving runtime 协调 |

详细架构与业务问题见 [[src-dynamo-architecture]]。
