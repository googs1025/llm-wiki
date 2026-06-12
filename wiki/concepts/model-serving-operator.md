---
title: Model Serving Operator
tags: [concept, model-serving, kubernetes, operator, llm-serving]
date: 2026-06-12
sources: [kserve-architecture-analysis.md, ome-architecture-analysis.md, kubeai-architecture-analysis.md, gpustack-architecture-analysis.md]
related: [[kserve]], [[llm-inference]], [[inference-routing]], [[kubernetes]], [[vllm]]
---

# Model Serving Operator

Model serving operator 是在 Kubernetes 上声明式管理模型、runtime、endpoint、autoscaling、GPU 资源和推理服务生命周期的控制面。

## 代表项目

| 项目 | 重点 |
|---|---|
| [[kserve]] | 标准化 InferenceService / LLMISvc / LocalModel 平台 |
| OME | Open Model Engine，CRD/controller + runtime selector + accelerator configs |
| KubeAI | Model CRD + OpenAI-compatible proxy + autoscaler + model loader |
| GPUStack | GPU cluster manager + vLLM/SGLang 编排 + observability |

## 和 engine 的区别

[[vllm]] / [[sglang]] 是推理 engine；model serving operator 管的是 engine 在集群里的部署、扩缩、路由、模型生命周期和 API 暴露。
