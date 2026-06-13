---
title: Envoy AI Gateway
tags: [entity, ai-gateway, envoy, llm, mcp, kubernetes]
date: 2026-06-13
sources: [ai-gateway-architecture-analysis.md]
related: [[ai-gateway]], [[mcp-gateway-tooling-map]], [[agentgateway]], [[gateway-api]], [[mcp]], [[higress]], [[kgateway]]
---

# Envoy AI Gateway

Envoy AI Gateway 是 Envoy Gateway 生态的 GenAI gateway。它包含 CRD API、controller、extproc、provider translators、backend auth、body/header mutator、rate limit、redaction、MCP proxy、metrics/tracing 和 data-plane/e2e tests。详见 [[src-ai-gateway-architecture]]。

## 架构边界

Envoy AI Gateway 解决的是 LLM/API 访问治理，不是模型 serving engine。它建立在 Envoy Gateway 上，通过 External Processing 和 provider translator 处理 OpenAI、Bedrock 等模型 API 差异，再叠加鉴权、限流、脱敏和观测。

## 关键设计

- CRD/API 描述 GenAI gateway 所需后端、策略和路由能力。
- Controller 把声明式配置转成 Envoy Gateway 可执行配置。
- extproc 数据面处理请求/响应修改、校验、治理和路由。
- translator 隔离不同 provider 协议差异。
- MCP proxy 说明边界正在从 LLM gateway 扩展到 tool gateway。

## 选型判断

已经使用 Envoy Gateway 并希望 GenAI 专用治理时看 Envoy AI Gateway。需要 LLM/MCP/A2A 三协议统一 Rust 数据面看 [[agentgateway]]；需要通用 Gateway API + AI policy 看 [[kgateway]]；需要阿里系 API gateway 与 WASM 插件生态看 [[higress]]。

