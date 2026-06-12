---
title: OME
tags: [entity, model-serving, kubernetes, operator, llm-serving]
date: 2026-06-12
sources: [ome-architecture-analysis.md]
related: [[model-serving-operator]], [[llm-inference]], [[kserve]], [[kubeai]], [[gpustack]]
---

# OME

OME（Open Model Engine）是 Kubernetes model serving operator，围绕 CRD/controller、model-agent、ome-agent、runtime selector 和 accelerator configs 组织模型部署。详见 [[src-ome-architecture]]。

## 架构边界

OME 是 model serving control plane，不是推理 engine。它与 [[kserve]] / [[kubeai]] 同属 [[model-serving-operator]] 比较集合，重点在 operator 如何抽象 runtime、accelerator 和模型生命周期。

## 选型判断

适合研究 K8s operator 如何封装模型部署、runtime selector 和加速器配置。不适合只做流量路由或 KV cache 算法；这些看 [[inference-routing]] 和 [[kv-cache-offload]]。
