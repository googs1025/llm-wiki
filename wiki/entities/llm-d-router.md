---
title: llm-d Router
tags: [entity, llm-serving, inference-routing, gateway-api, llm-d]
date: 2026-06-16
sources: [llm-d-router-architecture-analysis.md]
related: [[llm-d]], [[inference-routing]], [[llm-d-kv-cache]], [[gateway-api-inference-extension]], [[gateway-api]], [[disaggregated-serving]]
---

# llm-d Router

llm-d Router 是 [[llm-d]] 的智能入口层，通过 Envoy ext-proc、Gateway API Inference Extension 或 standalone mode 接入请求，再用 Endpoint Picker (EPP) 对 InferencePool endpoints 做过滤、打分和选择。详见 [[src-llm-d-router-architecture]]。

## 架构边界

它不是推理引擎，也不是通用 AI Gateway。它的核心职责是把请求、模型目标、runtime metrics、KV locality、scheduling profile 和 Kubernetes endpoint 状态合成一次 endpoint picking 决策。

## 核心抽象

| 抽象 | 作用 |
|---|---|
| EPP | Endpoint Picker server/controller，承接 ext-proc 或 GIE 请求。 |
| filters / scorers / scrapers | 插件化过滤、打分和指标采集框架。 |
| EndpointPickerConfig | 把 scheduling profiles、plugins 和权重配置化。 |
| InferenceObjective / InferenceModelRewrite | 把请求目标、模型重写和控制面策略从硬编码路由中拆出来。 |
| disaggregation sidecar | 协调 encode/prefill/decode 多阶段推理。 |

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 想理解 llm-d 在线请求路径 | 优先看它，Router/EPP 是 [[llm-d]] 请求入口。 |
| 想做 Gateway API / InferencePool endpoint picking | 适合，它贴近 [[gateway-api-inference-extension]]。 |
| 想研究 prompt 语义路由 | 先看 [[semantic-router]] / [[routellm]]，再和 llm-d Router 区分。 |
| 想研究 KV cache 命中索引 | 需要配合 [[llm-d-kv-cache]]。 |

## 选型提示

把 [[llm-d-router]] 放在 [[inference-routing]] 的 Kubernetes endpoint picking 层评估。它和 [[ai-gateway]] 的区别在于：AI Gateway 管 provider/auth/policy/protocol governance；llm-d Router 管 model server pod 如何被选择。
