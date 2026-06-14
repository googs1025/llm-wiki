---
title: JobSet 架构与设计思路分析
tags: [architecture, kubernetes, batch, distributed-workload]
date: 2026-06-14
sources: [jobset-architecture-analysis.md]
related: ["[[jobset]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[kueue]]"]
---

# JobSet 架构与设计思路分析

> 原文：`raw/jobset-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/jobset · 优先级 P1

## 一句话定位

JobSet 是 K8s native API for distributed ML training and HPC workloads，用多个 replicated jobs 表达一个整体作业。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ JobSet                     │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ API: JobSe │ │ Controller: ch │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Failure po │ │ Integrations:  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API | JobSet / replicatedJobs |
| Controller | child Job lifecycle and status aggregation |
| Failure policy | restart / recreate / fail fast |
| Integrations | Kueue, batch, ML training |

## 关键数据流

```
用户提交 JobSet
        │
        ▼
controller 展开多个 child Jobs
        │
        ▼
各 job 创建 Pods
        │
        ▼
聚合成功/失败状态
        │
        ▼
按 failure policy 处理重试或终止
```

## 设计决策与哲学

- **补齐 `分布式 workload API` 维度**：JobSet 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Kueue 负责 queue/admission；JobSet 负责表达分布式作业拓扑，二者常一起出现。
- **选型价值**：它应和 [[llm-inference]], [[batch-inference]], [[kueue]] 一起看，而不是孤立评估。

## 相关页面

- [[jobset]]
- [[kubernetes]]
- [[llm-inference]]
- [[batch-inference]]
- [[kueue]]
