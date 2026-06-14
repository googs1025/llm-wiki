---
title: Karpenter 架构与设计思路分析
tags: [architecture, kubernetes, autoscaling, node]
date: 2026-06-14
sources: [karpenter-architecture-analysis.md]
related: ["[[karpenter]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]"]
---

# Karpenter 架构与设计思路分析

> 原文：`raw/karpenter-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/karpenter · 优先级 P0

## 一句话定位

Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Pending Pods with resource and topology constraints                        │
│ CPU, memory, GPU, zone, architecture, taints, and affinity shape demand.   │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Karpenter controller                                                       │
│ Provisioning, disruption, consolidation, and termination control loops.    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Capacity model                                                             │
│ NodePool, NodeClaim, scheduler simulation, and CloudProvider               │
│ pricing/capacity APIs.                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Cloud instances join as Kubernetes nodes; idle or replaceable nodes are    │
│ consolidated.                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API | NodePool / NodeClaim / EC2NodeClass-like provider API |
| Controller | provisioning、disruption、consolidation、termination |
| Scheduler simulation | 从 pending pods 推导 instance requirements |
| CloudProvider boundary | 云厂商容量、价格、可用区和实例类型 |

## 关键数据流

```
Pod pending
        │
        ▼
Karpenter 汇总调度约束
        │
        ▼
选择 NodePool 和实例需求
        │
        ▼
创建 NodeClaim/云主机
        │
        ▼
节点加入集群并承载 Pod
        │
        ▼
空闲或可合并时 disruption/consolidation
```

## 设计决策与哲学

- **补齐 `节点弹性 / 成本` 维度**：Karpenter 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：和 HPA/KEDA 不同，Karpenter 扩的是节点容量；和 Cluster Autoscaler 相比，它更强调按 pending pods 即时求解容量。
- **选型价值**：它应和 [[llm-inference]], [[kubernetes]], [[model-serving-operator]] 一起看，而不是孤立评估。

## 相关页面

- [[karpenter]]
- [[kubernetes]]
- [[llm-inference]]
- [[model-serving-operator]]
