---
title: Gateway API Inference Extension
tags: [entity, kubernetes, inference-routing, gateway-api, llm-serving]
date: 2026-06-12
sources: [gateway-api-inference-extension-architecture-analysis.md]
related: [[gateway-api]], [[inference-routing]], [[model-serving-operator]], [[llm-d]], [[kserve]]
---

# Gateway API Inference Extension

Gateway API Inference Extension 是 Kubernetes Gateway API 的推理扩展，核心对象是 InferencePool 和 Endpoint Picker，用于标准化模型服务 endpoint picking、conformance 和 benchmark。详见 [[src-gateway-api-inference-extension-architecture]]。

## 架构边界

它不是完整 model serving 平台，也不是推理引擎；它定义的是 gateway 到推理后端之间的选择协议和控制面 API。[[llm-d]]、[[kserve]] 等项目可以围绕它实现更完整的 serving stack。

## 选型判断

适合研究 Kubernetes Gateway API 如何进入 LLM inference routing 标准层。若需要完整 serving 平台，看 [[kserve]] / [[llm-d]]；若要语义或成本质量路由算法，看 [[semantic-router]] / [[routellm]]。
