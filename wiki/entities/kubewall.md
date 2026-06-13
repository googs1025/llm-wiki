---
title: kubewall
tags: [entity, kubernetes, dashboard, ai-ops]
date: 2026-06-13
sources: [kubewall-architecture-analysis.md]
related: [[ai-ops]], [[kubernetes]], [[k8m]], [[kubectl-ai]], [[cloud-native-security]]
---

# kubewall

kubewall 是 single-binary Kubernetes dashboard，仓库分为 Go backend、client、charts 和 media。它在当前 wiki 中的价值是“AI integration 进入 K8s dashboard 管理体验”的对照样本。详见 [[src-kubewall-architecture]]。

## 架构边界

kubewall 的主体仍是 dashboard 基础设施：资源浏览、事件、port-forward、Helm 安装和前端 UI。AI 是增强层，不是完整 agent framework。

## 关键设计

- `backend/cmd`、`backend/routes`、`backend/handlers` 组成 Go dashboard server。
- `backend/event` 与 `backend/portfoward` 承接集群事件和端口转发。
- `client/src` 是前端控制台。
- `charts/kubewall` 降低部署门槛。

## 选型判断

需要轻量 dashboard 对照时看 kubewall；需要更强 AI/MCP 控制台形态看 [[k8m]]；需要命令行自然语言入口看 [[kubectl-ai]]。

