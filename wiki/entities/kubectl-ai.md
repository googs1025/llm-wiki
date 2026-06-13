---
title: kubectl-ai
tags: [entity, kubernetes, ai-ops, cli, mcp]
date: 2026-06-13
sources: [kubectl-ai-architecture-analysis.md]
related: [[ai-ops]], [[kubernetes]], [[mcp]], [[kagent]], [[k8m]], [[kubewall]]
---

# kubectl-ai

kubectl-ai 是 GoogleCloudPlatform 出品的 kubectl 入口 Kubernetes assistant。它以 Go CLI / agent loop 为核心，内置 bash、kubectl、journal、sessions、sandbox，并支持 MCP server mode。详见 [[src-kubectl-ai-architecture]]。

## 架构边界

kubectl-ai 是 CLI-first 的 [[ai-ops]] 工具，不是 dashboard，也不是完整 agent workflow 平台。它把自然语言问题转成 kubectl/bash 查询和解释，并能作为 MCP server 被其他 agent 调用。

## 关键设计

- `cmd/**` 提供 CLI 命令入口。
- `pkg/agent` 和 `pkg/tools` 管理 agent loop 与内置工具。
- `pkg/mcp` 让它从 standalone CLI 变成 K8s tool server。
- `pkg/sessions` / `pkg/journal` 保留会话与操作记录。

## 选型判断

想在终端里自然语言操作 Kubernetes，看 kubectl-ai；想把 K8s/DevOps 操作组织成 agentic workflow，看 [[kagent]]；想用 UI 管集群并接入 AI，看 [[k8m]] / [[kubewall]]。

