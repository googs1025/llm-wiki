---
title: Kueue
tags: [entity, kubernetes, scheduler, queueing]
date: 2026-06-14
sources: [kueue-architecture-analysis.md]
related: ["[[kueue]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[model-serving-operator]]"]
---

# Kueue

Kubernetes-native Job Queueing，用 ClusterQueue/LocalQueue/Workload/ResourceFlavor 把 batch、AI/HPC 和多租户资源配额做成 admission control。 详见 [[src-kueue-architecture]]。

## 架构边界

和 kube-scheduler 不同，Kueue 先决定 workload 是否能入场；真正的 Pod placement 仍由 scheduler 做。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `调度 / 队列` 能力 | 适合，Kueue 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[batch-inference]], [[model-serving-operator]] 组合。 |

## 核心组件

- API: ClusterQueue / LocalQueue / Workload / ResourceFlavor
- Controller: workload admission, quota accounting, preemption
- Integrations: Job, JobSet, RayJob, MPIJob, PyTorchJob 等 batch workload
- Scheduler-like logic: cohort borrowing、fair sharing、flavor assignment

## 选型提示

把 Kueue 放在 `调度 / 队列` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
