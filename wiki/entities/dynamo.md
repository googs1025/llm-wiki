---
title: Dynamo
tags: [entity, ai-infra, llm-inference, llm-serving, distributed-serving, kv-cache, kubernetes, autoscaling, nvidia]
date: 2026-10-03
sources: [src-dynamo-architecture]
related: ["[[llm-inference]]", "[[inference-routing]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]", "[[model-serving-operator]]", "[[ai-gateway]]", "[[sglang]]", "[[vllm]]", "[[llm-serving-performance]]", "[[llm-serving-reliability]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# Dynamo

NVIDIA Dynamo 是 engine 上方可模块化采用的分布式 serving runtime，协调请求路由、worker 发现、P/D、KV transfer 与容量控制；模型前向和本地 KV 仍由 vLLM、SGLang 等 backend engine 负责。

## 当前核验（2026-10-03）

核验 release 为 [v1.5.0](https://github.com/ai-dynamo/dynamo/releases/tag/v1.5.0)，发布于 2026-09-21（GitHub UTC 日期）。其依赖矩阵固定 vLLM **0.28.0**、SGLang **0.5.18**；[[vllm]] 和 [[sglang]] 的独立最新版不自动具备兼容性。该版本还将 AIConfigurator 更名为 AISimulate，升级规划工具时应检查新包与 CLI。

[[src-dynamo-architecture]] 保存较早的文档与实现分析。下文引用的 dev 文档是本次核验时看到的架构边界，不能把它的全部配置或默认值外推为 v1.5.0 的保证。

## 架构与状态边界

| 路径 | 主要职责 |
|---|---|
| Request plane | Frontend / Router 接收与协调请求，backend workers 执行；P/D 模式传递阶段结果与 transfer metadata |
| Discovery / event plane | 发现 worker，传播 KV events 和运行信号，支持路由与观测 |
| Control connections | Planner 根据指标更新期望 worker 数；Kubernetes Operator 负责收敛资源和生命周期 |
| KV 数据路径 | engine 维护本地 KV，所选 connector / transport 协调实际跨 worker 传输 |

以上区分依据 [Dynamo dev 架构文档](https://docs.nvidia.com/dynamo/dev/knowledge-base/concepts/architecture)。请求、事件和控制连接可使用不同机制；Operator 不逐请求选点，locality index 也不代替 engine KV 数据。

[[disaggregated-serving]] 的 prefill/decode 是服务角色；backend 内部 TP/PP/EP/DP 是执行并行方式。选择角色池规模与选择单个 worker 内的并行拓扑是不同决策，最终都需用 [[llm-serving-performance]] 的目标负载验证。

## KVBM 迁移边界

> [!warning] Conflict
> KVBM 在 v1.5.0 已被标记为 deprecated，目标在 v1.6.0 移除；host/disk offload 应转向 engine-native integrations。早期 KV Cache Runner（KVCR）面向跨节点 KV sharing，**不是 KVBM 的直接替代品**。[官方 v1.5.0 迁移说明](https://github.com/ai-dynamo/dynamo/releases/tag/v1.5.0)

[[src-dynamo-architecture]] 的 KVBM 四级层次是历史快照，用于设计理解与迁移，不能继续作为当前主推能力。[[kv-cache-offload]] 进一步区分数据副本、tier residency、外部索引和直接 P/D transfer。

## 适用与采用成本

- 适合：需要跨 worker 请求协调、KV-aware routing、P/D 角色池与 Planner 容量闭环，且能承担 engine/connector/runtime 版本管理的团队。
- 不适合：只有单模型单实例推理，或只需标准模型生命周期而没有分布式 runtime 需求。前者直接使用 engine 更简，后者可比较 [[kserve]] / [[ome]]。
- 下一步核验：锁定 backend pins、GPU/互联和部署模式，检查传输、路由事件、readiness 与取消/故障恢复路径；KVBM 用户还需单独验证 offload 迁移。可靠性检查入口见 [[llm-serving-reliability]]。

## 与同类及模块地图的关系

[[llm-d]] 更围绕 Kubernetes Proxy/EPP、InferencePool 和 Model Server 组合；[[gateway-api-inference-extension]] 提供入口选点契约；[[kserve]] / [[ome]] 聚焦模型服务生命周期。它们和 Dynamo 可能组合，采用前要明确哪些组件拥有路由、KV transfer 和扩缩写入权。

Dynamo 在 M4 位于分布式 runtime 层，并提供可选控制组件。职责见 [[llm-inference-serving-project-map]]，组合与运维成本见 [[llm-serving-engine-selection-map]]。
