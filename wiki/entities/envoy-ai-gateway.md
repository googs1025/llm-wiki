---
title: Envoy AI Gateway
tags: [entity, ai-gateway, envoy, kubernetes, llm, provider-routing]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[ai-gateway]], [[inference-routing]], [[gateway-api]], [[gateway-api-inference-extension]], [[llm-d-router]], [[semantic-router]]
---

# Envoy AI Gateway

Envoy AI Gateway 是基于 Envoy Gateway 的开源 GenAI traffic gateway，用于把应用请求接入多个 hosted provider 或 self-hosted model serving cluster。

## 解决的问题

企业需要统一处理 provider 认证、顶层路由、global rate limit、协议和失败边界，同时又希望把自托管集群内部的细粒度 endpoint picking 交给专用 inference router。

## 核心架构

README 采用 two-tier gateway：Tier One 负责 authentication、top-level routing 和 global rate limiting；Tier Two 负责 self-hosted model access，并可接 endpoint picker / LLM-aware routing。它支持 OpenAI、Azure OpenAI、Gemini、Bedrock、Anthropic 等 provider 方向。

## 边界与选型

它是 edge/provider governance，不是 P/D worker router，也不是模型质量路由算法。典型组合是 Envoy AI Gateway → [[semantic-router]]（可选）→ [[llm-d-router]] / [[gateway-api-inference-extension]] → model server。

详见 [[src-ai-gateway-architecture]]、[[src-k8s-gateway-routing-comparison]]。
