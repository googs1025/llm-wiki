---
title: GPUStack
tags: [entity, model-serving, gpu, kubernetes, llm-serving, multi-cloud, maas]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[model-serving-operator]], [[llm-inference]], [[gpu-sharing]], [[vllm]], [[sglang]], [[kserve]], [[kthena]]
---

# GPUStack

GPUStack 是 GPU cluster manager 与 Model-as-a-Service 平台，能够跨本地服务器、Kubernetes 和云环境管理 GPU，配置 vLLM、SGLang、TensorRT-LLM 或自定义 inference engine，并提供模型服务和 GPU 运维能力。

## 解决的问题

GPU 资源、模型部署、engine 参数、认证、监控和计量通常分散在不同系统。GPUStack 把 GPU 调度、模型服务、engine 选择、故障恢复、访问控制、token/API 计量和多集群可见性整合起来。

## 核心边界

GPUStack 更像一体化 GPU/MaaS 平台，而不是单纯 K8s CRD 库或专用 P/D router。它的价值在资源与服务的整体运营；如果组织已有成熟 K8s/Gateway/Operator，只想补一个模型生命周期层，[[kserve]] 或 [[ome]] 可能更贴合。

## 适用场景

适合 GPU 云、私有 GPU 集群、跨环境 Model-as-a-Service、需要多种加速器和统一计量运维的团队。需要 Gateway API/InferencePool 标准化看 [[llm-d]]；需要深度 P/D/KV 编排看 [[dynamo]] 或 [[kthena]]。

详见 [[src-gpustack-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
