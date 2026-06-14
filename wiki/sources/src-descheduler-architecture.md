---
title: Descheduler 架构与设计思路分析
tags: [architecture, kubernetes, scheduler, optimization]
date: 2026-06-14
sources: [descheduler-architecture-analysis.md]
related: ["[[descheduler]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# Descheduler 架构与设计思路分析

> 原文：`raw/descheduler-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/descheduler · 优先级 P1

## 一句话定位

Descheduler 根据策略驱逐已经运行的 Pods，让 kube-scheduler 有机会重新放置，修复节点漂移、拓扑不均、约束变化等问题。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Cluster state drift                                                        │
│ Initial scheduling decisions become suboptimal after node or workload      │
│ changes.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ descheduler policy engine                                                  │
│ Strategies detect imbalance, policy violations, or removable Pods.         │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Eviction control                                                           │
│ Evicts eligible Pods while respecting PDBs, priorities, namespaces, and    │
│ safety limits.                                                             │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ kube-scheduler places replacement Pods using current cluster state.        │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Policy config | strategies/profiles |
| Strategies | remove duplicates, low utilization, topology spread, affinity violations |
| Evictor | safe pod eviction |
| CronJob/controller deployment modes | CronJob/controller deployment modes |

## 关键数据流

```
周期读取节点和 Pod 状态
        │
        ▼
策略识别需要移动的 Pods
        │
        ▼
检查 PDB/namespace/priority 等保护
        │
        ▼
evict Pod
        │
        ▼
scheduler 重新调度
```

## 设计决策与哲学

- **补齐 `调度后优化` 维度**：Descheduler 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：scheduler 决定新 Pod 放哪；descheduler 处理运行一段时间后的布局退化。
- **选型价值**：它应和 [[kubernetes]], [[llm-inference]] 一起看，而不是孤立评估。

## 相关页面

- [[descheduler]]
- [[kubernetes]]
- [[llm-inference]]
