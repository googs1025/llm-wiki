---
title: Descheduler
tags: [entity, kubernetes, scheduler, optimization]
date: 2026-06-14
sources: [descheduler-architecture-analysis.md]
related: ["[[descheduler]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# Descheduler

Descheduler 根据策略驱逐已经运行的 Pods，让 kube-scheduler 有机会重新放置，修复节点漂移、拓扑不均、约束变化等问题。 详见 [[src-descheduler-architecture]]。

## 架构边界

scheduler 决定新 Pod 放哪；descheduler 处理运行一段时间后的布局退化。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `调度后优化` 能力 | 适合，Descheduler 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[llm-inference]] 组合。 |

## 核心组件

- Policy config: strategies/profiles
- Strategies: remove duplicates, low utilization, topology spread, affinity violations
- Evictor: safe pod eviction
- CronJob/controller deployment modes

## 选型提示

把 Descheduler 放在 `调度后优化` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
