---
title: ControllerMesh
tags: [entity, kubernetes, openkruise, controller, high-availability]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[kubernetes-workload-automation]], [[controller-runtime]], [[k8s-core-controller-map]], [[cloud-native-security]], [[openkruise-kruise]]
---

# ControllerMesh

ControllerMesh 是 OpenKruise 生态里的 controller/operator isolation and management 项目。根据 [[src-openkruise-projects-current-state]]，它属于 P1：活跃度不如 Kruise / Rollouts / Kruise Game，但适合作为 [[kubernetes-workload-automation]] 中控制器运行边界、故障半径和多 operator 管理的设计参考。

## 架构边界

它不解决单个业务 workload 的生命周期，而是关注控制器本身如何隔离、分片、管理和降低 blast radius。这个问题和 [[controller-runtime]] 常见的单 manager 多 controller 模式不同：后者解决工程骨架，ControllerMesh 更偏控制器运行形态和隔离策略。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 控制器太多、权限太大或故障影响面太广 | 值得研究 [[controllermesh]]，并结合 [[cloud-native-security]] 看权限和审计边界。 |
| 想写一个普通 CRD controller | 先看 [[controller-runtime]] / [[kubebuilder]]。 |
| 想理解 OpenKruise workload | 先看 [[openkruise-kruise]]。 |

## 选型提示

ControllerMesh 的架构价值大于当前项目热度。它提醒平台工程不要只关注 workload controller 的业务逻辑，也要关注控制器自身的权限、隔离、可观测和故障边界。
