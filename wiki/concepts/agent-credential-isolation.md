---
title: Agent 凭据隔离
tags: [security, multi-agent, ai-infra, design-pattern]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md]
related: [[HiClaw]], [[higress]], [[ai-agent-plugin-patterns]], [[declarative-agent-management]]
---

# Agent 凭据隔离

> Stub — 待充实

让 AI Agent **永远拿不到**真实凭据（LLM API key / GitHub PAT / OSS AK），它只持一个网关侧颁发的 **consumer key**，所有外部访问经网关鉴权和路由。

[[HiClaw]] 通过 [[higress|Higress AI Gateway]] 实现这个模式：

- 用户的真 API key 只存 Higress 的 secret 里
- 每个 Agent（[[HiClaw|Worker]] / Manager）被分配一个 Higress consumer + key
- Agent 调 LLM / OSS / [[mcp|MCP server]] 都经过 Higress，consumer key 决定能访问哪些路径
- **抗 prompt injection**：即便 Agent 被劫持，攻击者拿到的也只是可被即时 revoke 的 consumer key——而不是真凭据

## 为什么重要

社区 skill 市场（如 `skills.sh` 上 80,000+ 社区作品）能否被企业放心装载，取决于这一点——传统框架（[[autogen]] / [[langgraph]] / [[crewai]]）让 Agent 直接持真凭据，prompt injection = 凭据失窃。

## TODO

- [ ] 补充：除 HiClaw 外其它"网关托管凭据"的实现（如 Anthropic 的 OAuth 模式）
- [ ] 写"凭据轮转"的具体机制（HiClaw 的 RefreshCredentials）
- [ ] 写"网关单点"的反向风险与缓解（高可用 / RBAC）
- [ ] 加 [[ai-agent-plugin-patterns]] 中对应原则的链接
