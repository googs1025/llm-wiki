---
title: AI Gateway
tags: [concept, ai-gateway, gateway-api, llm, mcp]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md, agentgateway-architecture-analysis.md, ai-gateway-architecture-analysis.md, kgateway-architecture-analysis.md, higress-architecture-analysis.md, plano-architecture-analysis.md]
related: [[agentgateway]], [[envoy-ai-gateway]], [[llm-d-router]], [[semantic-router]], [[routellm]], [[gateway-api-inference-extension]], [[gateway-api]], [[inference-routing]], [[agent-credential-isolation]], [[mcp-gateway-tooling-map]]
---

# AI Gateway

AI Gateway 是面向 LLM/MCP/Agent 流量的入口治理层，通常处理 provider 适配、认证、凭据托管、rate limit、routing、redaction、guardrails、telemetry 和 policy。

## 当前项目族

| 项目 | 定位 |
|---|---|
| [[agentgateway]] | LLM/MCP/A2A 三协议 Rust 数据面 + Gateway API 控制面 |
| [[envoy-ai-gateway]] | Envoy Gateway 上的 GenAI provider translator / extproc / policy |
| kgateway | Gateway API / Envoy xDS / API+AI Gateway 能力分支 |
| Higress | AI Native API Gateway，和 HiClaw/凭据托管强相关 |
| Plano | AI-native proxy/data plane，偏 model routing / guardrails / agent orchestration |
| [[gateway-api-inference-extension]] | Gateway API 的 inference endpoint picking 协议与 InferencePool API |
| [[semantic-router]] | 按 intent、difficulty、risk、capability 和 system state 选择 model/recipe 的控制层 |
| [[routellm]] | 用 strong/weak model threshold 做质量-成本路由并提供离线评测 |
| [[llm-d-router]] | 面向 InferencePool endpoint 的 EPP，按 KV、load、priority、health 做 pod/worker 选择 |

## 和 inference routing 的关系

[[inference-routing]] 是 AI Gateway 的一个子问题：请求应该去哪个模型、哪个 endpoint、哪个 pod。AI Gateway 还要处理凭据、安全、协议转换和治理。

不要把“网关”理解成一个单一组件：Envoy AI Gateway 偏 edge/provider governance，Semantic Router/RouteLLM 偏 model or capability selection，Gateway API Inference Extension 偏标准协议，llm-d Router 偏 K8s inference endpoint picking。完整对比见 [[src-k8s-gateway-routing-comparison]]。
