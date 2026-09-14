---
title: vLLM Semantic Router
tags: [entity, inference-routing, ai-gateway, llm-serving, vllm, mixture-of-models]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[inference-routing]], [[ai-gateway]], [[llm-d-router]], [[routellm]], [[llm-inference]]
---

# vLLM Semantic Router

Semantic Router 是 vLLM 生态的 programmable Mixture-of-Models routing and control layer。应用通过稳定的 OpenAI/Anthropic-compatible endpoint 访问它，Router 根据请求特征选择或组合能力路径。

## 解决的问题

应用不应把“简单问题走便宜模型、复杂问题升级、敏感内容走安全路径、需要工具/检索/验证时组合能力”硬编码在业务代码中。Semantic Router 将 intent、difficulty、context、modality、identity、risk 和 system state 统一放在请求路径。

## 核心抽象

Recipe/virtual model 可以指向单模型、specialist、cascade 或 bounded multi-model workflow，并附加 retrieval、memory、tools、caching、guardrails 和 verification。

## 边界与选型

它决定 model/ability/recipe，不替代 Envoy 或模型 server，也不直接负责 K8s pod endpoint picking。需要成本/质量算法基线看 [[routellm]]；需要 KV、队列、InferencePool endpoint 看 [[llm-d-router]]。

详见 [[src-semantic-router-architecture]]、[[src-k8s-gateway-routing-comparison]]。
