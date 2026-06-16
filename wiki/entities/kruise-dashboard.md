---
title: Kruise Dashboard
tags: [entity, kubernetes, openkruise, dashboard, observability]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[openkruise-kruise]], [[headlamp]], [[kubewall]], [[k8m]], [[kubernetes-workload-automation]]
---

# Kruise Dashboard

Kruise Dashboard 是 OpenKruise 的运维 UI 方向项目，面向 CloneSet、Advanced StatefulSet、Advanced DaemonSet 等 OpenKruise workload 的可视化管理。根据 [[src-openkruise-projects-current-state]]，它属于 OpenKruise P1/P2 边界项目，适合放到 Kubernetes dashboard / ops UI 维度做对比。

## 架构边界

它不是 OpenKruise workload 控制器本身。它的价值在于把 OpenKruise CRD 的状态、操作和排障入口暴露给用户，和 [[headlamp]]、[[kubewall]]、[[k8m]] 这类 Kubernetes UI 形成对照。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 团队已经使用 OpenKruise workload | 可作为运维入口候选。 |
| 想研究 Kubernetes dashboard 扩展 | 可和 [[headlamp]] / [[kubewall]] / [[k8m]] 对比。 |
| 想理解 OpenKruise 核心控制器 | 先看 [[openkruise-kruise]]。 |

## 选型提示

Dashboard 的优先级取决于 OpenKruise workload 是否已经成为生产日常操作对象；如果只是研究控制器架构，源码优先级低于主仓和 metrics。
