---
title: Agent 凭据隔离
tags: [security, multi-agent, ai-infra, design-pattern]
date: 2026-06-12
sources: [hiclaw-architecture-analysis.md, agentgateway-architecture-analysis.md]
related: [[HiClaw]], [[agentgateway]], [[ai-gateway]], [[mcp]], [[ai-agent-plugin-patterns]], [[declarative-agent-management]]
---

# Agent 凭据隔离

让 AI Agent **永远拿不到**真实凭据（LLM API key / GitHub PAT / OSS AK），它只持一个网关侧颁发的 **consumer key**，所有外部访问经网关鉴权和路由。

[[HiClaw]] 通过 [[higress|Higress AI Gateway]] 实现这个模式：

- 用户的真 API key 只存 Higress 的 secret 里
- 每个 Agent（[[HiClaw|Worker]] / Manager）被分配一个 Higress consumer + key
- Agent 调 LLM / OSS / [[mcp|MCP server]] 都经过 Higress，consumer key 决定能访问哪些路径
- **抗 prompt injection**：即便 Agent 被劫持，攻击者拿到的也只是可被即时 revoke 的 consumer key——而不是真凭据

## 为什么重要

社区 skill 市场（如 `skills.sh` 上 80,000+ 社区作品）能否被企业放心装载，取决于这一点——传统框架（[[autogen]] / [[langgraph]] / [[crewai]]）让 Agent 直接持真凭据，prompt injection = 凭据失窃。

## 模式拆解

```
Agent runtime
  │ only has consumer key / short-lived token
  ▼
AI Gateway / Tool Gateway
  │ owns real provider keys, GitHub PAT, OSS AK, MCP credentials
  │ applies authn/authz/rate limit/audit/policy
  ▼
LLM provider / MCP server / storage / code host
```

关键点不是“把 key 放到另一个地方”这么简单，而是把权限决策从 prompt 可影响的 Agent 进程移到网关控制面：

- Agent 只看到统一 endpoint 和可撤销身份；
- 真凭据只在 gateway/backend secret/credential provider 内部使用；
- route / policy / consumer 决定 Agent 能访问哪些模型、工具、bucket、repo；
- audit log 记录的是“哪个 Agent 身份调用了哪个能力”，而不是一堆共享 API key。

## 代表实现

| 项目 | 隔离方式 | 适合借鉴点 |
|------|----------|------------|
| [[HiClaw]] | Worker / Manager 只持 Higress consumer key，真实 LLM / OSS / MCP 凭据在网关侧 | 多 Agent 协作平台的默认安全边界 |
| [[agentgateway]] | `AgentgatewayBackend` 保存 provider/backend secret，LLM/MCP/A2A 统一走 gateway policy | AI Gateway 作为出口流量和工具访问控制面 |
| [[loongsuite-pilot]] | 不托管业务凭据，但在 telemetry 上统一执行 content policy / secret mask | 观测链路里的隐私边界 |

## 凭据轮转

凭据轮转应该发生在网关侧，而不是要求 Agent 重新学习/保存真实 key：

1. credential provider 或 secret manager 生成/刷新真实 provider 凭据；
2. gateway 更新 backend secret 或 consumer key 映射；
3. Agent 侧只需要继续用自己的 consumer key，或接收一个短期 token；
4. 旧 consumer key 可按 Agent、Team、workspace 维度 revoke；
5. audit log 用于确认旧 key 不再被使用。

HiClaw 的 `RefreshCredentials` 思路属于这个模式：Worker 身份稳定，真实凭据和 STS 权限可在外部滚动。

## 网关单点风险

凭据隔离把风险从“每个 Agent 都可能泄露真 key”收敛为“网关是强信任边界”。需要配套：

- 网关高可用，避免所有 Agent 出口依赖单 Pod；
- RBAC / namespace / consumer policy 分层，避免一个 consumer key 访问全部能力；
- secret manager 或 KMS 托管真凭据，避免明文落盘；
- access log + anomaly detection，发现异常工具调用或模型调用；
- break-glass 机制，网关不可用时明确哪些能力允许降级，哪些必须 fail-closed。

## 与插件设计原则的关系

这对应 [[ai-agent-plugin-patterns]] 中的“宿主权限边界”和“协议通道纪律”：插件、skill、MCP server 可以扩展 Agent 能力，但不应把真实凭据直接暴露给 Agent prompt 或第三方插件代码。
