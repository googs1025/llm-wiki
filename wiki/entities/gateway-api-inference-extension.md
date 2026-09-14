---
title: Gateway API Inference Extension
tags: [entity, kubernetes, inference-routing, gateway-api, llm-serving, endpoint-picking]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[gateway-api]], [[inference-routing]], [[model-serving-operator]], [[llm-d]], [[llm-d-router]], [[kserve]]
---

# Gateway API Inference Extension

Gateway API Inference Extension 是 Kubernetes Gateway API 的推理扩展，定义 InferencePool、Endpoint Picker interaction 和 inference endpoint picking 的协议/控制面边界。

## 解决的问题

通用 Service/负载均衡不理解模型身份、推理协议和 endpoint 级运行状态。Inference Extension 让 Gateway 在转发请求前询问模型感知的 Endpoint Picker，从而为 LLM serving 提供标准化选择接口。

## 核心边界

它是协议和 API 扩展，不是完整模型服务平台、推理 engine 或具体路由算法。[[llm-d-router]] 是其重要生产化实现之一；[[kserve]]、[[kthena]] 等平台可以在这条标准边界上集成。

## 适用场景

适合希望复用 Gateway API、把 endpoint picking 从具体 proxy 中解耦的 Kubernetes 平台。语义/成本/质量模型选择应放在它之前，由 [[semantic-router]] 或 [[routellm]] 完成。

详见 [[src-gateway-api-inference-extension-architecture]]、[[src-k8s-gateway-routing-comparison]]。
