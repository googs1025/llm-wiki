---
title: KServe
tags: [entity, model-serving, kubernetes, inference, operator, genai]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[model-serving-operator]], [[llm-inference]], [[kubernetes]], [[inference-routing]], [[vllm]], [[llm-d]], [[kubeai]], [[ome]]
---

# KServe

KServe 是 Kubernetes-native 的标准化 distributed generative and predictive AI inference platform。它用 InferenceService、LLMInferenceService、InferenceGraph、controller 和 webhook 把传统 ML 与 GenAI 放到同一个服务平台。

## 解决的问题

平台团队往往同时承载 TensorFlow/PyTorch/XGBoost 等 predictive workload 和 vLLM/llm-d 等 LLM workload。KServe 提供统一 API、部署模式、模型缓存、OpenAI-compatible GenAI 接口、KV offload、request-based autoscaling、canary 和 scale-to-zero 能力。

## 核心边界

KServe 是模型服务标准化与生命周期 control plane，不是推理 kernel，也不是专门的 KV router。它可以选择 serverless/Knative、RawDeployment、ModelMesh 等路径；不同模式在冷启动、scale-to-zero、canary 和运维复杂度上有差异。

## 适用场景

适合 Kubeflow/Kubernetes 生态、需要 predictive + generative 统一 API 和成熟 operator 治理的组织。若只做专用 LLM P/D serving，比较 [[llm-d]]、[[dynamo]]、[[kthena]]；若只想快速自托管模型，比较 [[kubeai]]。

详见 [[src-kserve-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
