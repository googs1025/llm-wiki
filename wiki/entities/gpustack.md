---
title: GPUStack
tags: [entity, model-serving, gpu, kubernetes, llm-serving]
date: 2026-06-12
sources: [gpustack-architecture-analysis.md]
related: [[model-serving-operator]], [[llm-inference]], [[gpu-sharing]], [[vllm]], [[sglang]]
---

# GPUStack

GPUStack 是 GPU cluster manager / model serving platform，用 Python server/worker/scheduler/gateway 组织 vLLM / SGLang 等后端，并提供 GPU 资源管理、模型服务和 observability。详见 [[src-gpustack-architecture]]。

## 架构边界

它更偏一体化 GPU 集群与模型服务平台；[[kserve]] 更偏 Kubernetes 标准 model serving API，[[ome]] / [[kubeai]] 更偏 operator/control plane。GPUStack 的重点是把资源发现、调度和服务入口打包成可直接使用的平台。

## 选型判断

适合希望从 GPU 资源管理直接走到 LLM serving 的团队。不适合只研究 Kubernetes 原生 CRD/operator 标准形态，此时看 [[kserve]]、[[ome]] 或 [[kubeai]]。
