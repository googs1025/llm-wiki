---
title: Headlamp 架构与设计思路分析
tags: [architecture, kubernetes, dashboard, observability]
date: 2026-06-14
sources: [headlamp-architecture-analysis.md]
related: ["[[headlamp]]", "[[kubernetes]]", "[[kubewall]]"]
---

# Headlamp 架构与设计思路分析

> 原文：`raw/headlamp-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/headlamp · 优先级 P1

## 一句话定位

Headlamp 是可扩展 Kubernetes web UI，面向 dashboard、debugging、monitoring 和插件扩展。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Headlamp                   │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Frontend:  │ │ Backend/proxy: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Plugin sys │ │ Auth/context:  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Frontend | React/TypeScript UI |
| Backend/proxy | Kubernetes API access |
| Plugin system | UI and cluster extensions |
| Auth/context | kubeconfig, in-cluster, OIDC-like deployments |

## 关键数据流

```
用户打开 Headlamp
        │
        ▼
选择 cluster/context
        │
        ▼
后端代理 Kubernetes API
        │
        ▼
前端展示 workloads/events/logs/resources
        │
        ▼
插件扩展额外视图或动作
```

## 设计决策与哲学

- **补齐 `Kubernetes UI` 维度**：Headlamp 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：kubewall 是 single-binary dashboard；Headlamp 更强调插件化和通用 Kubernetes UI。
- **选型价值**：它应和 [[kubernetes]], [[kubewall]] 一起看，而不是孤立评估。

## 相关页面

- [[headlamp]]
- [[kubernetes]]
- [[kubewall]]
