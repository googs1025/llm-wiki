---
title: AI Gateway
tags: [concept, ai-gateway, gateway-api, llm, mcp]
date: 2026-06-12
sources: [agentgateway-architecture-analysis.md, ai-gateway-architecture-analysis.md, kgateway-architecture-analysis.md, higress-architecture-analysis.md, plano-architecture-analysis.md]
related: [[agentgateway]], [[gateway-api]], [[inference-routing]], [[agent-credential-isolation]], [[mcp-gateway-tooling-map]]
---

# AI Gateway

AI Gateway 是面向 LLM/MCP/Agent 流量的入口治理层，通常处理 provider 适配、认证、凭据托管、rate limit、routing、redaction、guardrails、telemetry 和 policy。

## 当前项目族

| 项目 | 定位 |
|---|---|
| [[agentgateway]] | LLM/MCP/A2A 三协议 Rust 数据面 + Gateway API 控制面 |
| Envoy AI Gateway | Envoy Gateway 上的 GenAI provider translator / extproc / policy |
| kgateway | Gateway API / Envoy xDS / API+AI Gateway 能力分支 |
| Higress | AI Native API Gateway，和 HiClaw/凭据托管强相关 |
| Plano | AI-native proxy/data plane，偏 model routing / guardrails / agent orchestration |

## 和 inference routing 的关系

[[inference-routing]] 是 AI Gateway 的一个子问题：请求应该去哪个模型、哪个 endpoint、哪个 pod。AI Gateway 还要处理凭据、安全、协议转换和治理。
