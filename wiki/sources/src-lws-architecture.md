---
title: LeaderWorkerSet 架构与设计思路分析
tags: [architecture, kubernetes, distributed-workload, llm-serving]
date: 2026-06-14
sources: [lws-architecture-analysis.md]
related: ["[[lws]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[kueue]]"]
---

# LeaderWorkerSet 架构与设计思路分析

> 原文：`raw/lws-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/lws · 优先级 P1

## 一句话定位

LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Distributed workload intent                                                │
│ A workload needs one leader plus a group of homogeneous worker Pods.       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ LeaderWorkerSet API                                                        │
│ Group size, replicas, pod templates, rollout policy, and status model the  │
│ group.                                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ LWS controller                                                             │
│ Reconciles leader/worker Pods and keeps grouped replicas in a coherent     │
│ lifecycle.                                                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Services, scheduler, Pods, and AI/HPC runtimes consume the generated       │
│ group.                                                                     │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API | LeaderWorkerSet CRD |
| Controller | replica group rollout/status |
| Pod template | leader/worker roles |
| Integrations | serving/HPC/AI workload |

## 关键数据流

```
用户声明 LeaderWorkerSet
        │
        ▼
controller 创建 leader/worker pod group
        │
        ▼
维护副本、状态和滚动更新
        │
        ▼
服务或上层 operator 连接每组 leader/worker
```

## 设计决策与哲学

- **补齐 `分布式 workload API` 维度**：LeaderWorkerSet 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：JobSet 面向作业集合；LWS 面向长期运行的 leader/worker 服务复制单元。
- **选型价值**：它应和 [[llm-inference]], [[batch-inference]], [[kueue]] 一起看，而不是孤立评估。

## 相关页面

- [[lws]]
- [[kubernetes]]
- [[llm-inference]]
- [[batch-inference]]
- [[kueue]]
