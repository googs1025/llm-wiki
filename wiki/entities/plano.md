---
title: Plano
tags: [entity, ai-gateway, proxy, rust, agentic]
date: 2026-06-13
sources: [plano-architecture-analysis.md]
related: [[ai-gateway]], [[mcp-gateway-tooling-map]], [[agentgateway]], [[mcp]], [[gateway-api]], [[agent-skills-plugin-system-map]]
---

# Plano

Plano 是 AI-native proxy / data plane，和 [[agentgateway]] 同处 agentic gateway / proxy 赛道，但更偏 Rust data plane + CLI/config/skills。详见 [[src-plano-architecture]]。

## 架构边界

Plano 不只是 provider adapter，也不是 Kubernetes Gateway API 控制面的完整替代。它的特点是把低延迟 proxy/data plane、配置 schema、CLI 运维入口和 skills/demos 组合起来，服务 model routing、guardrails 和 agent orchestration。

## 关键设计

- `crates/llm_gateway` 和 `prompt_gateway` 承载核心 Rust gateway/data plane。
- `cli/planoai` 是运维与使用入口。
- `config/**` 包含 Envoy template、schema 和测试配置。
- `skills/**` 把 agentic ops、部署、路由、观测固化成能力包。

## 选型判断

想看自有 Rust AI proxy + skills-first 路线时看 Plano。需要 Gateway API / xDS / mesh 结合看 [[agentgateway]] 或 [[kgateway]]；需要 Envoy Gateway GenAI 专用治理看 [[ai-gateway|Envoy AI Gateway]]。

