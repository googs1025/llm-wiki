---
title: Model Serving Operator
tags: [concept, model-serving, kubernetes, operator, llm-serving]
date: 2026-06-12
sources: [kserve-architecture-analysis.md, ome-architecture-analysis.md, kubeai-architecture-analysis.md, gpustack-architecture-analysis.md, llm-d-workload-variant-autoscaler-architecture-analysis.md, llm-d-batch-gateway-architecture-analysis.md]
related: [[kserve]], [[llm-inference]], [[inference-routing]], [[kubernetes]], [[vllm]], [[llm-d]], [[llm-d-workload-variant-autoscaler]], [[llm-d-batch-gateway]], [[batch-inference]]
---

# Model Serving Operator

Model serving operator 是在 Kubernetes 上声明式管理模型、runtime、endpoint、autoscaling、GPU 资源和推理服务生命周期的控制面。

## 代表项目

| 项目 | 重点 |
|---|---|
| [[kserve]] | 标准化 InferenceService / LLMISvc / LocalModel 平台 |
| [[ome]] | Open Model Engine，CRD/controller + runtime selector + accelerator configs |
| [[kubeai]] | Model CRD + OpenAI-compatible proxy + autoscaler + model loader |
| [[gpustack]] | GPU cluster manager + vLLM/SGLang 编排 + observability |
| [[llm-d-workload-variant-autoscaler]] | 针对同一模型多个 serving variant 的全局 autoscaling 决策层 |
| [[llm-d-batch-gateway]] | 不管理模型部署，但把 batch job lifecycle 接到 model serving endpoint |

## 和 engine 的区别

[[vllm]] / [[sglang]] 是推理 engine；model serving operator 管的是 engine 在集群里的部署、扩缩、路由、模型生命周期和 API 暴露。

## 和 llm-d 外围组件的关系

[[llm-d-batch-gateway]]、[[llm-d-benchmark]]、[[llm-d-workload-variant-autoscaler]]、[[llm-d-inference-sim]] 说明 model serving operator 周围还有一圈工程能力：

| 能力 | 代表 | 和 operator 的边界 |
|---|---|---|
| Batch job control plane | [[llm-d-batch-gateway]] | 不创建模型服务，复用已有 endpoint 执行异步 JSONL job。 |
| Variant autoscaling | [[llm-d-workload-variant-autoscaler]] | 不替代 HPA/KEDA，而是为多个 variant 计算 desired allocation。 |
| Benchmark lifecycle | [[llm-d-benchmark]] | 不是生产 controller，而是部署、运行、收集和分析实验。 |
| Simulator | [[llm-d-inference-sim]] | 不是真实模型服务，用于验证 controller/router/benchmark 闭环。 |

选型时不要把这些都归类成“serving operator”。operator 管声明式生命周期；batch、benchmark、simulator、variant autoscaling 分别补异步任务、评测、测试替身和资源经济。


## 和 Kubernetes 调度/指标外围的关系

模型服务 operator 只管理模型服务生命周期还不够。[[kueue]] / [[jobset]] / [[lws]] 决定 batch 和分布式 workload 怎么表达与入队；[[karpenter]] 决定节点容量怎样按 pending pods 扩出；[[metrics-server]] / [[prometheus-adapter]] 决定 autoscaling 能看到哪些指标；[[inference-perf]] / [[llm-d-prism]] 决定实验结果怎样被复现和分析。
