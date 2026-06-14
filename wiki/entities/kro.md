---
title: KRO
tags: [entity, kubernetes, orchestration, api]
date: 2026-06-14
sources: [kro-architecture-analysis.md]
related: ["[[kro]]", "[[kubernetes]]", "[[model-serving-operator]]"]
---

# KRO

KRO（Kube Resource Orchestrator）用 ResourceGraphDefinition 把多个 Kubernetes resources 组合成更高层 API。 详见 [[src-kro-architecture]]。

## 架构边界

Crossplane composition 偏跨云资源；KRO 偏 Kubernetes resource graph 和平台 API 组合。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `higher-level API orchestration` 能力 | 适合，KRO 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]] 组合。 |

## 核心组件

- ResourceGraphDefinition API
- Controller: graph reconciliation
- Generated instances/resources
- Status/value propagation

## 选型提示

把 KRO 放在 `higher-level API orchestration` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
