---
title: k8m
tags: [entity, kubernetes, ai-ops, dashboard, mcp]
date: 2026-06-13
sources: [k8m-architecture-analysis.md]
related: [[ai-ops]], [[kubernetes]], [[mcp]], [[kubectl-ai]], [[kubewall]], [[kagent]]
---

# k8m

k8m 是轻量 Kubernetes AI dashboard，把集群浏览、操作权限、异常检测和 AI/MCP 能力放进一个小型控制台。详见 [[src-k8m-architecture]]。

## 架构边界

k8m 是 dashboard-first，不是 CLI assistant，也不是通用 Agent framework。它更适合把 AI 辅助嵌到集群管理 UI 里，而不是让 agent 直接接管复杂 workflow。

## 关键设计

- Go backend 的 `internal/dao`、`pkg/service`、`pkg/controller` 和 `pkg/plugins` 负责资源访问与插件能力。
- `ui/**` 提供管理控制台。
- AI/MCP 能力通过插件进入资源解释、排障和操作辅助。
- 项目价值主要在产品形态参考：小型控制台如何接入 AI，而不是 agent loop 本身。

## 选型判断

需要 UI-first K8s AI 管理入口时看 k8m。需要单二进制 dashboard 对照看 [[kubewall]]；需要 kubectl 工作流看 [[kubectl-ai]]；需要 agentic K8s 操作层看 [[kagent]]。

