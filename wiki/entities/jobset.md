---
title: JobSet
tags: [entity, kubernetes, batch, distributed-workload]
date: 2026-06-14
sources: [jobset-architecture-analysis.md]
related: ["[[jobset]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[kueue]]"]
---

# JobSet

JobSet 是 K8s native API for distributed ML training and HPC workloads，用多个 replicated jobs 表达一个整体作业。 详见 [[src-jobset-architecture]]。

## 架构边界

Kueue 负责 queue/admission；JobSet 负责表达分布式作业拓扑，二者常一起出现。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `分布式 workload API` 能力 | 适合，JobSet 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[batch-inference]], [[kueue]] 组合。 |

## 核心组件

- API: JobSet / replicatedJobs
- Controller: child Job lifecycle and status aggregation
- Failure policy: restart / recreate / fail fast
- Integrations: Kueue, batch, ML training

## 选型提示

把 JobSet 放在 `分布式 workload API` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
