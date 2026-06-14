---
title: kube-scheduler-simulator 架构与设计思路分析
tags: [architecture, kubernetes, scheduler, simulator]
date: 2026-06-14
sources: [kube-scheduler-simulator-architecture-analysis.md]
related: ["[[kube-scheduler-simulator]]", "[[kubernetes]]"]
---

# kube-scheduler-simulator 架构与设计思路分析

> 原文：`raw/kube-scheduler-simulator-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kube-scheduler-simulator · 优先级 P1

## 一句话定位

kube-scheduler-simulator 提供 Kubernetes scheduler 行为模拟和可视化，用于理解 filter/score、调度失败原因和策略效果。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Scheduler scenario                                                         │
│ Users define nodes, pods, scheduler config, and policy experiments.        │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Simulator backend                                                          │
│ Runs scheduler logic and captures filter, score, bind, and decision        │
│ traces.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Visualization frontend                                                     │
│ Shows scheduling timeline, plugin results, and object state changes.       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Scheduler policy debugging and education without requiring a real workload │
│ cluster.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Simulator API/server | Simulator API/server |
| Scheduler integration | Scheduler integration |
| Frontend visualization | Frontend visualization |
| Scenario objects | nodes/pods/policies |

## 关键数据流

```
用户创建模拟节点和 Pod
        │
        ▼
scheduler 执行调度周期
        │
        ▼
记录 filter/score/bind 过程
        │
        ▼
UI 展示每一步决策
        │
        ▼
用户调整策略复盘
```

## 设计决策与哲学

- **补齐 `scheduler 可视化模拟` 维度**：kube-scheduler-simulator 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：KWOK 模拟大规模集群对象；scheduler simulator 解释单次或少量调度决策过程。
- **选型价值**：它应和 [[kubernetes]] 一起看，而不是孤立评估。

## 相关页面

- [[kube-scheduler-simulator]]
- [[kubernetes]]
