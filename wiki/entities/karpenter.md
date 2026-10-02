---
title: Karpenter
tags: [entity, kubernetes, autoscaling, node]
date: 2026-09-25
sources: [karpenter-architecture-analysis.md]
related: ["[[karpenter]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[kubernetes-workload-gang-scheduling-design]]", "[[kubernetes-scheduler-core-design]]", "[[kueue]]", "[[scheduler-plugins]]"]
---

# Karpenter

Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。 详见 [[src-karpenter-architecture]]。

证据说明：2026-09-25 核验的官方默认分支快照为 [`06bc3b4b94dd`](https://github.com/kubernetes-sigs/karpenter/commit/06bc3b4b94dd9af0228db4b611f2ebcb2ba17b9c)，该 commit 不代表 release。[[src-karpenter-architecture]] 保留 2026-06-14 的 raw-backed Source 快照；当前跨项目职责见 [[kubernetes-workload-gang-scheduling-design]]，调度器流程见 [[kubernetes-scheduler-core-design]]。

## 在 M5-B Workload / Scheduling 地图中的位置

在上述快照中，Karpenter 将不可调度 Pod 的需求与 `karpenter.sh/v1` NodePool、provider-specific NodeClass 约束组合为 NodeClaim，推进节点启动、注册、初始化及后续 disruption/termination。它提供容量，不决定 [[kueue]] 的 quota admission；最终 Pod placement/binding 仍由 kube-scheduler 及配置的 [[scheduler-plugins]] 完成。节点回收的 drift、consolidation、expiration 具有不同约束，不能统一理解为自动无损替换。

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
