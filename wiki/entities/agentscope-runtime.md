---
title: AgentScope Runtime
tags: [entity, agent-runtime, agent-as-a-service, sandbox, ai-agent]
date: 2026-06-12
sources: [agentscope-runtime-architecture-analysis.md]
related: [[agent-runtime-substrate]], [[agent-runtime-sandbox-selection-map]], [[agent-sandbox]], [[agentcube]], [[agentgateway]]
---

# AgentScope Runtime

AgentScope 生态的生产化 Agent-as-a-Service runtime，把 AgentApp、Runner、protocol adapters、sandbox manager 和 K8s/serverless deployers 组合起来。详见 [[src-agentscope-runtime-architecture]]。

## 架构边界

它处在 framework app 与生产 runtime 之间：比 [[agent-sandbox]] 更上层，比完整 managed teammate 产品更底层。仓库 README 已提示能力并入 AgentScope 2.0，所以更适合作为架构迁移参考。

## 选型判断

- 要理解 AgentScope app 如何服务化：看 AgentScope Runtime。
- 要理解底层容器/沙箱隔离：看 [[agent-sandbox]] 和 [[agent-runtime-substrate]]。
- 要理解多 Agent 协作产品层：看 [[agentcube]]、HiClaw、Multica 类项目。
