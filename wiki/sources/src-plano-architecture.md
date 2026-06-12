---
title: Plano 架构与设计思路分析
tags: [architecture, ai-gateway, proxy, rust, agentic]
date: 2026-06-12
sources: [plano-architecture-analysis.md]
related: [[[mcp-gateway-tooling-map]], [[agentgateway]], [[mcp]], [[gateway-api]]]
---

# Plano 架构与设计思路分析

`katanemo/plano` 是 AI-native proxy/data plane，和 agentgateway 同层但更偏 Rust data plane + CLI/config/skills。仓库含 `crates/llm_gateway`、`prompt_gateway`、`hermesllm`、CLI、配置 schema、demos 和 skills，适合补 MCP/AI Gateway tooling map。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `katanemo/plano` 是 AI-native proxy/data plane，和 agentgateway 同层但更偏 Rust … │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `crates/llm_gateway`, `prompt_gateway` · `cli/planoai`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `config/**`                     │  │ `skills/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `crates/llm_gateway`, `prompt_gateway` | 核心 Rust gateway/data plane。 |
| `cli/planoai` | CLI 运维入口。 |
| `config/**` | Envoy template、schema 和测试配置。 |
| `skills/**` | 面向 agent/部署/路由/观测的技能包。 |

## 关键数据流

1. 用户通过 config/CLI 定义 gateway、routing、filter chains。
2. Rust data plane 处理 LLM 请求、路由、guardrails。
3. skills/demos 提供 agent orchestration 和运维入口。

## 设计决策

- 把 proxy/data plane 与 skills/docs 结合，服务 agentic ops。
- Rust 核心适合低延迟代理。
- 配置 schema 是使用体验关键。

## 对比定位

和 Envoy AI Gateway 相比，Plano 更自有 data plane/skills-first；和 agentgateway 相比，二者都可看作 agentic proxy，但生态和实现路线不同。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
