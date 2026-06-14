---
title: Headlamp
tags: [entity, kubernetes, dashboard, observability]
date: 2026-06-14
sources: [headlamp-architecture-analysis.md]
related: ["[[headlamp]]", "[[kubernetes]]", "[[kubewall]]"]
---

# Headlamp

Headlamp 是可扩展 Kubernetes web UI，面向 dashboard、debugging、monitoring 和插件扩展。 详见 [[src-headlamp-architecture]]。

## 架构边界

kubewall 是 single-binary dashboard；Headlamp 更强调插件化和通用 Kubernetes UI。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Kubernetes UI` 能力 | 适合，Headlamp 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[kubewall]] 组合。 |

## 核心组件

- Frontend: React/TypeScript UI
- Backend/proxy: Kubernetes API access
- Plugin system: UI and cluster extensions
- Auth/context: kubeconfig, in-cluster, OIDC-like deployments

## 选型提示

把 Headlamp 放在 `Kubernetes UI` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
