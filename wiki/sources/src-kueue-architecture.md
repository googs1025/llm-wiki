---
title: Kueue 架构与设计思路分析
tags: [architecture, kubernetes, scheduler, queueing]
date: 2026-06-14
sources: [kueue-architecture-analysis.md]
related: ["[[kueue]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[model-serving-operator]]"]
---

# Kueue 架构与设计思路分析

> 原文：`raw/kueue-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kueue · 优先级 P0

## 一句话定位

Kubernetes-native Job Queueing，用 ClusterQueue/LocalQueue/Workload/ResourceFlavor 把 batch、AI/HPC 和多租户资源配额做成 admission control。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Batch / AI / HPC workload intent                                           │
│ Users submit Jobs, JobSets, RayJobs, MPIJobs, or PyTorchJobs.              │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Kueue APIs                                                                 │
│ ClusterQueue, LocalQueue, Workload, and ResourceFlavor model quota and     │
│ admission.                                                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Admission and quota control                                                │
│ Workload admission, cohort borrowing, fair sharing, flavor assignment, and │
│ preemption.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Admitted workloads flow to Kubernetes scheduler and normal cluster         │
│ runtime.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API | ClusterQueue / LocalQueue / Workload / ResourceFlavor |
| Controller | workload admission, quota accounting, preemption |
| Integrations | Job, JobSet, RayJob, MPIJob, PyTorchJob 等 batch workload |
| Scheduler-like logic | cohort borrowing、fair sharing、flavor assignment |

## 关键数据流

```
用户提交 Job/JobSet/RayJob
        │
        ▼
Kueue 为 workload 建队列对象
        │
        ▼
ClusterQueue 检查资源配额与 flavor
        │
        ▼
admit 后 workload 才真正消耗集群资源
        │
        ▼
完成/失败后释放 quota
```

## 设计决策与哲学

- **补齐 `调度 / 队列` 维度**：Kueue 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：和 kube-scheduler 不同，Kueue 先决定 workload 是否能入场；真正的 Pod placement 仍由 scheduler 做。
- **选型价值**：它应和 [[llm-inference]], [[batch-inference]], [[model-serving-operator]] 一起看，而不是孤立评估。

## 相关页面

- [[kueue]]
- [[kubernetes]]
- [[llm-inference]]
- [[batch-inference]]
- [[model-serving-operator]]
