---
title: agentgateway
tags: [ai-gateway, llm, mcp, a2a, rust, kubernetes]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[mcp]], [[gateway-api]], [[xds]], [[hbone]], [[cel]], [[istio]], [[HiClaw]], [[agent-sandbox]]
---

# agentgateway

> Stub — 待充实

Solo.io / Istio 系出品的 **AI-native L7 网关**（Apache 2.0）。把三种 AI 流量统一在一个 Rust 数据面里：

- **LLM Gateway**：OpenAI / Anthropic / Gemini / Bedrock / Vertex / Azure / Copilot 七家 provider 统一为 OpenAI 兼容 API + guardrails
- **MCP Gateway**：stdio / HTTP Streamable / SSE 三种 transport + OpenAPI 自动转 MCP 工具 + 多 MCP server federation
- **A2A Gateway**：Google Agent-to-Agent 协议代理，通过重写 Agent Card 让所有调用走回 gateway

## 架构骨架

- **控制面**（Go）：[[gateway-api|Gateway API]] + 自家 CRD（`AgentgatewayPolicy` / `AgentgatewayBackend` / `AgentgatewayParameters`），KRT 反应式表，[[xds|xDS Delta ADS]] 分发
- **数据面**（Rust）：tokio + hyper + rustls，proxy/gateway → http/route → llm|mcp|a2a → upstream，[[cel|CEL]] 做策略 IR，[[hbone|HBONE]] 跟 [[istio|Istio]] mesh 互操作
- **UI**（TypeScript）：Next.js 管理界面

## 核心设计哲学

1. **沿用 Istio 基建做 AI Gateway**：Gateway API + KRT + xDS + HBONE 全套复用，只把数据面换成专为 AI 协议优化的 Rust 代理
2. **三协议共享同一条 pipeline**：Route / Policy / Backend / CEL 求值统一，差别只在 `Backend.kind` 决定走哪个 provider 适配器
3. **凭据托管**：LLM provider 真凭据放在 backend secret，Agent 只面对 gateway 自身认证，参见 [[agent-credential-isolation]]
4. **跟 [[agent-sandbox]] 互补**：前者出口流量治理，后者运行时隔离，并集 = AI 工作负载完整治理面

详见 [[src-agentgateway-architecture]]。

## TODO

- [ ] 写 LLM provider 适配器的完整对照表（请求 / 响应 / streaming 差异）
- [ ] 写 MCP federation 的命名空间策略与 CEL RBAC 实战
- [ ] 写跟 LiteLLM / OpenRouter / Portkey 的对比
- [ ] 写部署 walkthrough（with kueue / cilium / Gateway API examples）
