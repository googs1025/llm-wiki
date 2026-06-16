---
title: Kruise Game
tags: [entity, kubernetes, openkruise, workload, game-server]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[openkruise-kruise]], [[kubernetes-workload-automation]], [[model-serving-operator]], [[k8s-core-controller-map]]
---

# Kruise Game

Kruise Game 是 OpenKruise 面向 game server management 的 specialized workload operator。根据 [[src-openkruise-projects-current-state]]，它是 OpenKruise P0 项目，适合研究长连接、有状态、生命周期敏感的游戏服务器如何用 Kubernetes workload API 表达和运维。

## 架构边界

它不是通用 Deployment 替代品，而是把游戏服务器的实例状态、运维操作、网络和生命周期管理做成专用控制器。它和 [[openkruise-kruise]] 的区别在于：Kruise 强调通用 workload enhancement；Kruise Game 强调游戏服务器这个垂直 workload。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 需要研究 specialized workload operator | 适合，GameServer 类 workload 是典型案例。 |
| 需要对比 Agones / StatefulSet | 适合，后续可单独摄入源码做横向对比。 |
| 只需要通用 workload 增强 | 先看 [[openkruise-kruise]]。 |
| 只需要 AI model serving | 看 [[model-serving-operator]] / [[llm-inference]]。 |

## 选型提示

Kruise Game 的价值在于把业务域状态放进 Kubernetes API，而不是把游戏服务器硬塞进通用 Deployment。这和 AI inference 里把 model、batch、worker group 做成 CRD 是同一类设计思想。
