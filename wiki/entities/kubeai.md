---
title: KubeAI
tags: [entity, model-serving, kubernetes, operator, openai-api, llm-serving]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[model-serving-operator]], [[llm-inference]], [[kserve]], [[ome]], [[gpustack]], [[vllm]], [[sglang]]
---

# KubeAI

KubeAI 是轻量 Kubernetes AI inference operator，使用 Model CRD、OpenAI-compatible model proxy、model loader 和 autoscaler 管理 LLM、VLM、embedding、speech-to-text 等服务。

## 解决的问题

把“模型文件 + 推理 engine”快速转换成 Kubernetes 内可调用的 OpenAI-compatible endpoint，并在模型闲置或流量变化时执行加载、卸载和扩缩，降低自托管 AI 服务的上手成本。

## 核心边界

KubeAI 偏应用友好和快速部署，不负责重新实现 vLLM/SGLang kernel，也不是以多角色 P/D、复杂 KV locality 或 GPU topology 为中心的编排层。复杂场景通常需要额外的 Gateway、调度或 serving stack。

## 适用场景

适合中小规模自托管、模型种类较多、希望 scale-from-zero 和统一 API 的团队。需要 predictive + GenAI 统一平台看 [[kserve]]；需要 enterprise vLLM 组件看 [[aibrix]]；需要深度 P/D/KV 看 [[dynamo]] 或 [[kthena]]。

详见 [[src-kubeai-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
