---
title: LeaderWorkerSet
tags: [entity, kubernetes, distributed-workload, llm-serving]
date: 2026-06-14
sources: [lws-architecture-analysis.md]
related: ["[[lws]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[kueue]]"]
---

# LeaderWorkerSet

LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。 详见 [[src-lws-architecture]]。

## 架构边界

JobSet 面向作业集合；LWS 面向长期运行的 leader/worker 服务复制单元。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `分布式 workload API` 能力 | 适合，LeaderWorkerSet 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[batch-inference]], [[kueue]] 组合。 |

## 核心组件

- API: LeaderWorkerSet CRD
- Controller: replica group rollout/status
- Pod template: leader/worker roles
- Integrations: serving/HPC/AI workload

## 选型提示

把 LeaderWorkerSet 放在 `分布式 workload API` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
