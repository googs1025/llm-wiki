---
title: llm-d
tags: [entity, llm-serving, kubernetes, gateway-api, inference-routing, distributed-inference]
date: 2026-10-03
sources: [src-k8s-serving-stack-comparison, src-llm-d-architecture]
related: ["[[llm-inference]]", "[[inference-routing]]", "[[model-serving-operator]]", "[[gateway-api]]", "[[kserve]]", "[[aibrix]]", "[[dynamo]]", "[[vllm]]", "[[sglang]]", "[[disaggregated-serving]]", "[[llm-serving-reliability]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# llm-d

llm-d 是 Kubernetes 上的分布式推理 serving stack，围绕 Proxy/EPP、InferencePool 和 Model Server 组合路由、P/D、缓存集成与扩缩能力。

## 当前核验（2026-10-03）

核验 release 为 [v0.10.0](https://github.com/llm-d/llm-d/releases/tag/v0.10.0)，发布于 2026-09-29（GitHub UTC 日期）。[公开架构页](https://llm-d.ai/docs/architecture)仍标 v0.9 latest，而 [dev 架构页](https://llm-d.ai/docs/dev/architecture)已包含新的扩缩说明；不能把公开网页的版本标签当成最新 release，也不能将 dev 配置直接视为已发布契约。

该 release 明确两项迁移：**llm-d-kv-cache 已迁入 llm-d-router**，旧仓库废弃尚在收尾；**WVA guides 已 deprecated**，原 llm-d-workload-variant-autoscaler 仓库更名为 **llm-d-autoscaling**。这是仓库整合与指南状态的说明，不等于所有历史 WVA 代码都已移除。[v0.10.0 migration notes](https://github.com/llm-d/llm-d/releases/tag/v0.10.0)

## 架构与状态边界

| 对象或组件 | 责任 |
|---|---|
| Proxy | 接受连接、咨询 EPP、向选定 Model Server 转发请求与 stream |
| EPP | 根据指标、KV affinity 和 policy 选择 endpoint；不必承载 token stream |
| InferencePool | 通过 selector 表达 Model Server Pod 集合与发现契约 |
| Model Server | vLLM/SGLang 等 engine，负责调度、模型执行与本地 KV |
| EPP metrics / KEDA / HPA | EPP 暴露信号，KEDA 对接指标与 HPA，HPA 计算并写入副本目标 |

前三类核心对象见 [dev 架构说明](https://llm-d.ai/docs/dev/architecture)。具体扩缩路径见 [dev autoscaling](https://llm-d.ai/docs/dev/architecture/advanced/autoscaling)：workload controllers 在目标写入后收敛 Pods，模型加载和 readiness 完成后才形成可路由容量。EPP 在请求路径，HPA 与 controllers 在异步控制路径；见 [[model-serving-operator]]。

KV locality index 维护位置元数据，offload / P2P sharing 搬运实际 KV，engine 验证可用性。代码进入同一仓库不改变这些所有权边界；P/D 角色编排也不等于 Model Server 内部 TP/PP/EP/DP。

## 历史证据与迁移阅读

> [!warning] Conflict
> [[llm-d-workload-variant-autoscaler]] 和 [[src-llm-d-workload-variant-autoscaler-architecture]] 是历史设计与迁移资料；当前采用应以目标 release 与 KEDA/HPA 指南为准。[[llm-d-kv-cache]] 与 [[src-llm-d-kv-cache-architecture]] 保留迁入 router 之前的组件边界，当前代码位置需沿 [[llm-d-router]] 查阅。

整体旧分析继续保留在 [[src-llm-d-architecture]] 和 [[src-k8s-serving-stack-comparison]]，其部署路径与版本矩阵不能直接用于 v0.10.0。

## 适用与采用成本

- 适合：已有 Kubernetes 与 Gateway API 基础，希望通过 InferencePool/EPP 标准化多 endpoint 入口，并按需加入 [[disaggregated-serving]] 或缓存路由的团队。
- 不适合：仅需单实例 engine，或无法维护 Gateway、EPP、模型服务与指标/扩缩组件间版本矩阵的场景；简单部署可比较 [[kubeai]]，集群模型服务管理可比较 [[gpustack]]。
- 下一步核验：对照所选 release 的组件与 model-server image 矩阵，验证 P/D connector、cache event schema、EPP 指标、扩缩唯一写入者、readiness 和 draining。失败与重试入口见 [[llm-serving-reliability]]。

## 在 M4 模块地图中的位置

llm-d 位于 Kubernetes routing/serving stack 层，连接流量入口、选点与 Model Server。与 [[dynamo]]、[[aibrix]] 的责任交集见 [[llm-inference-serving-project-map]]，组合选择见 [[llm-serving-engine-selection-map]]。
