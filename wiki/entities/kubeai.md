---
title: KubeAI
tags: [entity, model-serving, kubernetes, operator, openai-api]
date: 2026-06-12
sources: [kubeai-architecture-analysis.md]
related: [[model-serving-operator]], [[llm-inference]], [[kserve]], [[ome]], [[vllm]]
---

# KubeAI

KubeAI 是 Kubernetes AI inference operator，用 Model CRD、OpenAI-compatible server/model proxy、model autoscaler 和 loader 管理 LLM、VLM、embedding、speech 等推理工作负载。详见 [[src-kubeai-architecture]]。

## 架构边界

KubeAI 更偏“把模型暴露成 OpenAI-compatible inference service”的 operator。与 [[kserve]] 相比，它聚焦 AI inference / OpenAI API 体验；与 [[ome]] 相比，它的入口和 proxy 形态更面向应用调用。

## 选型判断

适合需要 Kubernetes 上快速运行 OpenAI-compatible 模型服务的场景。不适合追求最底层推理内核优化；那应看 [[vllm]]、[[sglang]]。
