---
title: Higress
tags: [entity, ai-gateway, api-gateway, wasm, kubernetes]
date: 2026-06-13
sources: [higress-architecture-analysis.md]
related: [[ai-gateway]], [[mcp-gateway-tooling-map]], [[agentgateway]], [[gateway-api]], [[agent-credential-isolation]], [[HiClaw]]
---

# Higress

Higress 是阿里系 AI Native API Gateway，基于 Envoy/Istio 控制面和多语言 WASM plugins。它在当前 wiki 中主要用于理解 AI gateway、模型路由、MCP/HTTP 策略和凭据治理，尤其是 [[HiClaw]] 背景中的网关能力。详见 [[src-higress-architecture]]。

## 架构边界

Higress 是通用 API Gateway 产品向 AI Gateway 扩展，不是只服务 LLM 的窄代理。它的优势来自成熟 API gateway 能力、服务发现、插件生态和 WASM 扩展。

## 关键设计

- `cmd/higress`、`pkg/**` 承载控制面和网关逻辑。
- `plugins/**` 提供 Go/Rust/C++/AssemblyScript 等多语言 WASM 插件。
- Envoy/Istio 基础设施负责通用 L7 流量治理。
- model-router、credential governance、MCP/LLM 插件把网关扩展到 AI 工作负载。

## 选型判断

需要传统 API gateway 和 AI gateway 合一时看 Higress；需要 GenAI 专用 Envoy Gateway 方案看 [[ai-gateway|Envoy AI Gateway]]；需要 Kubernetes Gateway API 原生通用网关看 [[kgateway]]；需要 agent-side LLM/MCP/A2A 出口治理看 [[agentgateway]]。

