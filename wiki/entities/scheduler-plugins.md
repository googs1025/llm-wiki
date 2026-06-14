---
title: scheduler-plugins
tags: [entity, kubernetes, scheduler, plugins]
date: 2026-06-14
sources: [scheduler-plugins-architecture-analysis.md]
related: ["[[scheduler-plugins]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# scheduler-plugins

scheduler-plugins 是基于 kube-scheduler framework 的 out-of-tree 插件集合，用于研究和生产化调度扩展。 详见 [[src-scheduler-plugins-architecture]]。

## 架构边界

Kueue 做 workload admission；scheduler-plugins 影响 Pod 到 Node 的 placement。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `调度 / 资源` 能力 | 适合，scheduler-plugins 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[llm-inference]] 组合。 |

## 核心组件

- Framework plugins: queueSort/preFilter/filter/score/reserve 等扩展点
- Scheduler binary/config
- Controllers/examples for capacity/placement policies
- Integration tests and manifests

## 选型提示

把 scheduler-plugins 放在 `调度 / 资源` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
