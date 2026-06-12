---
title: kubewall 架构与设计思路分析
tags: [architecture, kubernetes, dashboard, ai-ops]
date: 2026-06-12
sources: [kubewall-architecture-analysis.md]
related: [[[ai-ops]], [[kubernetes]], [[cloud-native-security]]]
---

# kubewall 架构与设计思路分析

`kubewall/kubewall` 是 single-binary K8s dashboard，仓库分为 Go backend、client、charts 和 media。它在 P1 中的价值是“AI integration 进入 K8s dashboard 管理体验”的对照样本，而不是完整 agent framework。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kubewall/kubewall` 是 single-binary K8s dashboard，仓库分为 Go backend、client… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `backend/cmd`, `backend/routes`, `backend/handlers` · `backend/event`, `backend/portfoward`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `client/src`                     │  │ `charts/kubewall`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `backend/cmd`, `backend/routes`, `backend/handlers` | Go dashboard server、路由和 handler。 |
| `backend/event`, `backend/portfoward` | 集群事件和端口转发。 |
| `client/src` | 前端 UI。 |
| `charts/kubewall` | Helm 安装。 |

## 关键数据流

1. 用户通过 dashboard 浏览资源。
2. backend 代理 K8s API、事件、port-forward 等能力。
3. AI 功能作为控制台辅助层接入。

## 设计决策

- single-binary/Helm 部署优先，降低运维门槛。
- 核心仍是 dashboard，AI 是增强层。
- 适合作为 k8m 的更轻对照。

## 对比定位

和 k8m 相比，kubewall 更 dashboard 基础设施；和 kubectl-ai 相比，它牺牲 CLI 灵活性换 UI 可视化。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
