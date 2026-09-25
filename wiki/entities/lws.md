---
title: LeaderWorkerSet
tags: [entity, kubernetes, distributed-workload, llm-serving]
date: 2026-09-25
sources: [lws-architecture-analysis.md]
related: ["[[lws]]", "[[kubernetes]]", "[[llm-inference]]", "[[batch-inference]]", "[[kueue]]", "[[kubernetes-workload-gang-scheduling-design]]", "[[kubernetes-scheduler-core-design]]", "[[jobset]]", "[[scheduler-plugins]]"]
---

# LeaderWorkerSet

LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。 详见 [[src-lws-architecture]]。

证据说明：2026-09-25 核验的官方默认分支快照为 [`d4f1525f15a4`](https://github.com/kubernetes-sigs/lws/commit/d4f1525f15a491170de19bc6abc1c89fe185b16c)，该 commit 不代表 release。[[src-lws-architecture]] 保留 2026-06-14 的 raw-backed Source 快照；当前跨项目职责见 [[kubernetes-workload-gang-scheduling-design]]，调度器流程见 [[kubernetes-scheduler-core-design]]。

## 在 M5-B Workload / Scheduling 地图中的位置

在上述快照中，`leaderworkerset.x-k8s.io/v1` 管理同类模型服务的 leader/worker 组及其恢复、扩缩与发布；`disaggregatedset.x-k8s.io/v1` 进一步以角色和 slices 组合子 LWS，协调分离推理的多角色生命周期。它们与 [[jobset]] 的批作业集合职责不同，也不管理 quota admission：准入通过 [[kueue]] 集成，最终 placement 由 kube-scheduler 及配置的 [[scheduler-plugins]] 完成。DS 的跨角色编排不等于整组原子准入。

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
