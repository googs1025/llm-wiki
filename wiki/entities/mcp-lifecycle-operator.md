---
title: MCP Lifecycle Operator
tags: [entity, kubernetes, mcp, agent]
date: 2026-06-14
sources: [mcp-lifecycle-operator-architecture-analysis.md]
related: ["[[mcp-lifecycle-operator]]", "[[kubernetes]]", "[[mcp]]", "[[declarative-agent-management]]", "[[agentgateway]]"]
---

# MCP Lifecycle Operator

MCP Lifecycle Operator 用声明式 API 部署、管理和安全滚动 MCP Servers，把 Agent tool server 生命周期放进 Kubernetes control plane。 详见 [[src-mcp-lifecycle-operator-architecture]]。

## 架构边界

MCP server framework 解决怎么写工具；MCP lifecycle operator 解决工具服务器如何在集群里安全运行和升级。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `MCP lifecycle` 能力 | 适合，MCP Lifecycle Operator 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[mcp]], [[declarative-agent-management]], [[agentgateway]] 组合。 |

## 核心组件

- MCPServer-like APIs
- Controller: deploy/rollout/status
- Integration: gateway/auth/config/secrets
- Production automation: health, rollout, lifecycle

## 选型提示

把 MCP Lifecycle Operator 放在 `MCP lifecycle` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
