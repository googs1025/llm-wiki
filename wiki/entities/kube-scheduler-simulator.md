---
title: kube-scheduler-simulator
tags: [entity, kubernetes, scheduler, simulator]
date: 2026-06-14
sources: [kube-scheduler-simulator-architecture-analysis.md]
related: ["[[kube-scheduler-simulator]]", "[[kubernetes]]"]
---

# kube-scheduler-simulator

kube-scheduler-simulator 提供 Kubernetes scheduler 行为模拟和可视化，用于理解 filter/score、调度失败原因和策略效果。 详见 [[src-kube-scheduler-simulator-architecture]]。

## 架构边界

KWOK 模拟大规模集群对象；scheduler simulator 解释单次或少量调度决策过程。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `scheduler 可视化模拟` 能力 | 适合，kube-scheduler-simulator 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]] 组合。 |

## 核心组件

- Simulator API/server
- Scheduler integration
- Frontend visualization
- Scenario objects: nodes/pods/policies

## 选型提示

把 kube-scheduler-simulator 放在 `scheduler 可视化模拟` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
