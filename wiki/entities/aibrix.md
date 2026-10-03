---
title: AIBrix
tags: [entity, llm-serving, kubernetes, vllm, ai-infra, kv-cache]
date: 2026-10-03
sources: [src-k8s-serving-stack-comparison, src-aibrix-architecture]
related: ["[[llm-inference]]", "[[inference-routing]]", "[[model-serving-operator]]", "[[vllm]]", "[[sglang]]", "[[dynamo]]", "[[llm-d]]", "[[kv-cache-offload]]", "[[disaggregated-serving]]", "[[batch-inference]]", "[[llm-serving-reliability]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# AIBrix

AIBrix 是可组合的多引擎推理基础设施，提供 Kubernetes 控制能力、Gateway/routing、KV 集成、P/D 和异步 batch；engine 仍拥有模型执行与本地 KV。

## 当前核验（2026-10-03）

核验 release 为 [v0.7.0](https://github.com/vllm-project/aibrix/releases/tag/v0.7.0)，发布于 2026-06-18（GitHub UTC 日期）。该版本明确支持 vLLM、SGLang、TensorRT-LLM 的多引擎接入，覆盖 KV-cache-centric P/D、Batch API 与 highly-available gateway；不能再将它限定为仅 vLLM fleet 的外围工具。

同一 release 的 maturity note 将 **Console、Batch API、Resource Manager / Cloud GPU execution 标为 preview**，API 和行为仍可能变化。“production”措辞不代表这些组件都已提供稳定兼容承诺。[v0.7.0 release](https://github.com/vllm-project/aibrix/releases/tag/v0.7.0)

[[src-aibrix-architecture]] 和 [[src-k8s-serving-stack-comparison]] 保留此前的架构分析；当前能力范围与成熟度以本次官方核验为准，旧 Source 不自动证明新组件已完成生产验证。

## 架构与状态边界

| 层 | 主要职责 |
|---|---|
| Control plane / controllers | 物化模型与多角色 workload、adapter 生命周期及容量目标，驱动后续就绪过程 |
| Gateway / routing | 请求处理、按 engine 能力与负载/KV 信号选点，以及多副本网关协作 |
| Runtime / KV integrations | 对接 engine 管理、指标与 connector，协调 KV 副本和 P/D 数据交接 |
| Batch / Console / Resource Manager | 异步任务、操作入口与资源供给；成熟度按上述 preview 提示处理 |
| Model engine | 负责 iteration 调度、TP/PP/EP/DP、权重与本地 KV 布局/有效性 |

版本化组件能力见 [AIBrix v0.7.0 release](https://github.com/vllm-project/aibrix/releases/tag/v0.7.0)，控制器和请求路径的总体划分见 [官方组件概览](https://aibrix.readthedocs.io/latest/getting_started/overview.html)（2026-10-03 核验）。

[[inference-routing]] 的 locality metadata、[[kv-cache-offload]] 的数据副本和 engine 的本地 KV 是不同状态。KV-centric P/D 需要按所选 engine/connector 验证数据交接；平台角色池与引擎内部并行配置也分别管理。Controller 不逐请求选点，HA gateway 也不自动保证流式输出失败后可无损续传，见 [[llm-serving-reliability]]。

## 适用与采用成本

- 适合：需要逐步组合路由、adapter 管理、KV/P-D、多引擎或 batch 能力，并能验证组件依赖和运维边界的团队。
- 不适合：只需单实例 engine，或要求新增 Console/Batch/Resource Manager API 已稳定冻结的场景。
- 下一步核验：固定目标 engine、KV connector 和 AIBrix 版本，验证支持矩阵、路由与状态同步、readiness/故障剔除；使用 [[batch-inference]] 时另测持久化、取消、重试与输出归档。引入 preview 组件要估算升级和数据迁移成本。

## 在 M4 模块地图中的位置

AIBrix 跨 Kubernetes 推理控制面与请求数据面，组件化提供 routing、生命周期、KV 和多角色编排。与 [[llm-d]]、[[dynamo]] 的职责交集见 [[llm-inference-serving-project-map]]，组合与采用成本见 [[llm-serving-engine-selection-map]]。
