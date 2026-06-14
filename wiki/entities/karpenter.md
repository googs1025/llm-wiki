---
title: Karpenter
tags: [entity, kubernetes, autoscaling, node]
date: 2026-06-14
sources: [karpenter-architecture-analysis.md]
related: ["[[karpenter]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]"]
---

# Karpenter

Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。 详见 [[src-karpenter-architecture]]。

## 架构边界

和 HPA/KEDA 不同，Karpenter 扩的是节点容量；和 Cluster Autoscaler 相比，它更强调按 pending pods 即时求解容量。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `节点弹性 / 成本` 能力 | 适合，Karpenter 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[kubernetes]], [[model-serving-operator]] 组合。 |

## 核心组件

- API: NodePool / NodeClaim / EC2NodeClass-like provider API
- Controller: provisioning、disruption、consolidation、termination
- Scheduler simulation: 从 pending pods 推导 instance requirements
- CloudProvider boundary: 云厂商容量、价格、可用区和实例类型

## 选型提示

把 Karpenter 放在 `节点弹性 / 成本` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
