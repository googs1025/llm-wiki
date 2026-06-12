---
title: KServe
tags: [entity, model-serving, kubernetes, inference, operator]
date: 2026-06-12
sources: [kserve-architecture-analysis.md]
related: [[model-serving-operator]], [[llm-inference]], [[kubernetes]], [[inference-routing]], [[vllm]]
---

# KServe

Kubernetes 标准化 model serving 平台，围绕 InferenceService、LLMInferenceService、LocalModel、controllers、webhooks 和 router 组织。详见 [[src-kserve-architecture]]。

## 架构边界

KServe 是模型服务平台和 operator，不是推理 engine。它把预测式模型服务与 GenAI/LLM serving 放到统一 K8s API 下，适合和 [[ome]]、[[kubeai]]、[[gpustack]] 放在 [[model-serving-operator]] 概念下比较。

## 选型判断

适合：需要成熟 K8s model serving API、controller/webhook、Knative/RawDeployment 等部署形态。

不适合：只想优化单模型推理 kernel 或 KV cache 算法；这些看 [[vllm]]、[[sglang]]、[[kv-cache-offload]]。
