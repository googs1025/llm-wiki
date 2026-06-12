---
title: vLLM Semantic Router
tags: [entity, inference-routing, ai-gateway, llm-serving, vllm]
date: 2026-06-12
sources: [semantic-router-architecture-analysis.md]
related: [[inference-routing]], [[ai-gateway]], [[llm-d]], [[gateway-api-inference-extension]], [[routellm]]
---

# vLLM Semantic Router

vLLM 生态的 system-level intelligent router，重点是按请求语义、模型能力、PII/prompt guard 和 mixture-of-models 策略做路由。详见 [[src-semantic-router-architecture]]。

## 架构边界

它与 `llm-d-router` 的差异很关键：semantic-router 偏语义分类和模型选择，llm-d-router 偏 K8s runtime metrics、Endpoint Picker 和 InferencePool。与 [[routellm]] 相比，它更工程化/系统化，而 RouteLLM 更像成本/质量路由算法基线。

## 选型判断

- 语义/安全/模型能力维度路由：看 semantic-router。
- Gateway API endpoint picking：看 [[gateway-api-inference-extension]] / [[llm-d]]。
- 成本/质量算法基线：看 [[routellm]]。
