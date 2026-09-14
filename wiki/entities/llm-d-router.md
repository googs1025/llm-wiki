---
title: llm-d Router
tags: [entity, llm-serving, inference-routing, gateway-api, endpoint-picking]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[llm-d]], [[inference-routing]], [[gateway-api-inference-extension]], [[semantic-router]], [[dynamo]], [[kserve]]
---

# llm-d Router

llm-d Router 是面向 LLM serving 的 intelligent entry point，由 Envoy/ext-proc 或 Gateway API 接入，并通过 Endpoint Picker 对 InferencePool endpoint 执行 filter → score → pick。

## 解决的问题

普通负载均衡只知道连接和健康状态，不知道 KV locality、推理负载、请求优先级、模型重写和 P/D 目标。llm-d Router 把这些 runtime signal 注入 Gateway 数据面，减少错误 endpoint 选择和 KV 重算。

## 核心抽象

EPP 是决策引擎；filters、scorers、scrapers 是插件化信号处理框架；InferenceObjective 和 InferenceModelRewrite 把请求目标、优先级、模型重写与 canary/A-B 策略显式化。

## 边界与选型

它选择 Kubernetes inference endpoint，不负责 provider 凭据和全局 quota；这些属于 [[envoy-ai-gateway]]。它也不负责语义模型选择，后者看 [[semantic-router]] / [[routellm]]。适合 Gateway API、InferencePool、KV-aware 和分布式 serving 场景。

详见 [[src-llm-d-router-architecture]]、[[src-k8s-gateway-routing-comparison]]。
