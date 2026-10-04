---
title: Model Serving Operator
tags: [concept, model-serving, kubernetes, operator, llm-serving]
date: 2026-10-03
sources: [src-dynamo-architecture, src-kserve-architecture, src-ome-architecture, src-kubeai-architecture, src-gpustack-architecture, src-llm-d-workload-variant-autoscaler-architecture, src-llm-d-batch-gateway-architecture, src-openkruise-projects-current-state]
related: ["[[kserve]]", "[[llm-inference]]", "[[inference-routing]]", "[[kubernetes]]", "[[vllm]]", "[[llm-d]]", "[[llm-d-router]]", "[[llm-d-kv-cache]]", "[[llm-d-workload-variant-autoscaler]]", "[[llm-d-batch-gateway]]", "[[batch-inference]]", "[[kubernetes-workload-automation]]", "[[llm-serving-reliability]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# Model Serving Operator

Model serving operator 把模型服务的 desired state 转成 Kubernetes 资源，并通过 reconcile 持续推进实例启动、模型加载、readiness、更新与缩容。它属于异步控制面；请求选点和 token stream 转发分别由 router/EPP 与 proxy/engine 承担，operator 不在每个请求的数据热路径中。

## 扩缩、执行与就绪的所有权

HPA 根据指标计算期望副本数并写入目标 workload 的 `/scale`；Deployment 等 workload controllers 再收敛 Pods。模型服务 operator 可以管理这些 workload，或把平台角色池目标转换成底层资源，但不能把 HPA 的目标计算与 Pod 收敛写成同一个动作。[Kubernetes HPA](https://kubernetes.io/docs/concepts/workloads/autoscaling/horizontal-pod-autoscale/)

在 llm-d 的 EPP metrics → KEDA → HPA 路径中，KEDA 的 Prometheus scaler 接入外部指标，KEDA 配置并拥有 HPA，非零副本扩缩决策由 HPA 执行；零副本激活需另按 KEDA 配置核验。[llm-d dev autoscaling](https://llm-d.ai/docs/dev/architecture/advanced/autoscaling)、[KEDA 概念](https://keda.sh/docs/2.18/concepts/)

Pod 存在或期望副本增加不代表模型可服务。GPU 资源就位后还要加载权重、warmup，通过 readiness 并传播到 endpoint discovery，router 才能使用新容量；缩容则需要停止新选点并排空请求。职责图见 [[llm-inference-serving-project-map#A4 · Kubernetes Serving 控制面|A4 · Kubernetes Serving 控制面]]，传播时序见 [[llm-inference-serving-project-map#S3 · 扩缩与就绪传播时序|S3 · 扩缩与就绪传播时序]]，故障行为见 [[llm-serving-reliability]]。

## Operator 与相邻组件

以下是既有 Source 中的角色对照，不表示每个项目都是 Kubernetes operator，也不把旧 API 清单视为当前版本保证；版本与采用条件沿各实体页核验。

| 项目 | 重点 |
|---|---|
| [[kserve]] | 标准化 InferenceService / LLMISvc / LocalModel 平台 |
| [[ome]] | Open Model Engine，CRD/controller + runtime selector + accelerator configs |
| [[kubeai]] | Model CRD + OpenAI-compatible proxy + autoscaler + model loader |
| [[gpustack]] | GPU cluster manager + vLLM/SGLang 编排 + observability |
| [[llm-d-workload-variant-autoscaler]] | Deprecated 的历史 variant autoscaling 设计，仅供迁移/设计参考 |
| [[llm-d-batch-gateway]] | 不管理模型部署，但把 batch job lifecycle 接到 model serving endpoint |
| [[rbg]] | 用 RoleBasedGroup / RoleInstance / CoordinatedPolicy 表达多角色、有状态、跨角色协调的 inference workload |
| [[kthena]] | 组合模型服务生命周期、多角色 workload 与路由能力；控制面和请求面分别部署与核验 |
| [[openkruise-kruise]] | 不直接管理模型服务，但提供 workload enhancement、image preheat、workload spread 等可借鉴的 K8s workload automation 模式 |

## 和 engine 的区别

[[vllm]] / [[sglang]] 管请求的 iteration 调度、模型执行、并行配置和本地 KV。Model serving operator 管 engine 实例的生命周期，以及路由配置与 API 暴露所需的声明式资源；实际逐请求选点见 [[inference-routing]]。两者通过 readiness、状态和 metrics 连接。

## 和 llm-d 外围组件的关系

[[llm-d-batch-gateway]]、[[llm-d-benchmark]]、[[llm-d-inference-sim]]，以及 deprecated/历史的 [[llm-d-workload-variant-autoscaler]]，说明 model serving operator 周围还有一圈工程能力：

| 能力 | 代表 | 和 operator 的边界 |
|---|---|---|
| Batch job control plane | [[llm-d-batch-gateway]] | 不创建模型服务，复用已有 endpoint 执行异步 JSONL job。 |
| Variant autoscaling（历史） | [[llm-d-workload-variant-autoscaler]] | Deprecated 设计曾为多个 variant 计算 desired allocation；现仅供迁移/设计参考。 |
| Benchmark lifecycle | [[llm-d-benchmark]] | 不是生产 controller，而是部署、运行、收集和分析实验。 |
| Simulator | [[llm-d-inference-sim]] | 不是真实模型服务，用于验证 controller/router/benchmark 闭环。 |

选型时不要把这些都归类成“serving operator”。operator 管声明式生命周期；batch、benchmark 和 simulator 分别补异步任务、评测和测试替身。对新部署，llm-d 当前路径是 [EPP metrics → KEDA Prometheus scaler → HPA](https://llm-d.ai/docs/dev/architecture/advanced/autoscaling)；[[llm-d-workload-variant-autoscaler]] 的 Entity Conflict 注记及历史设计仅用于迁移/设计参考。


## 和 Kubernetes 调度/指标外围的关系

[[dynamo]] 展示了分离的 Planner/Operator 边界：Planner 更新期望 worker 数，Operator 在 Kubernetes 中收敛，Router 留在请求路径。[Dynamo dev control connections](https://docs.nvidia.com/dynamo/dev/knowledge-base/concepts/architecture#control-connections) 中的控制连接不意味着 operator 执行 GPU kernel 或 KV transfer。

[[kueue]] 负责 workload admission；[[jobset]] / [[lws]] 表达并收敛批作业或多进程服务组；[[karpenter]] 管节点容量；[[metrics-server]] / [[prometheus-adapter]] 提供不同种类的指标接入。它们不替 engine 选择本轮 token，也不替路由器选择请求 endpoint。整体视角见 [[kubernetes-workload-automation]]，组件组合和控制权冲突检查见 [[llm-serving-engine-selection-map]]。
