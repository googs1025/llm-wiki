---
title: kagent
tags: [entity, ai-ops, kubernetes, ai-agent, mcp]
date: 2026-06-12
sources: [kagent-architecture-analysis.md]
related: [[ai-ops]], [[kubernetes]], [[mcp]], [[declarative-agent-management]], [[agent-framework-programming-model-map]]
---

# kagent

Cloud Native agentic AI 项目，把 Kubernetes / DevOps 操作、工具、Helm/UI 和 MCP 能力包装成 agentic workflow。详见 [[src-kagent-architecture]]。

## 架构边界

kagent 不应和通用 Agent framework 混放。它的主场是 [[ai-ops]]：围绕 K8s/DevOps 操作场景做 agentic automation，而不是提供通用个人 coding agent 执行 loop。

## 选型判断

- 想在 kubectl 里问答/执行：看 kubectl-ai。
- 想在 dashboard 管理 K8s：看 k8m / kubewall。
- 想把 K8s/DevOps 操作组织成 agentic workflow：看 kagent。
