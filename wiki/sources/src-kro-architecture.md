---
title: KRO 架构与设计思路分析
tags: [architecture, kubernetes, orchestration, api]
date: 2026-06-14
sources: [kro-architecture-analysis.md]
related: ["[[kro]]", "[[kubernetes]]", "[[model-serving-operator]]"]
---

# KRO 架构与设计思路分析

> 原文：`raw/kro-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kro · 优先级 P1

## 一句话定位

KRO（Kube Resource Orchestrator）用 ResourceGraphDefinition 把多个 Kubernetes resources 组合成更高层 API。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Higher-level platform API intent                                           │
│ A team defines a ResourceGraphDefinition for application or platform       │
│ abstractions.                                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ KRO controller                                                             │
│ Expands graph definitions, reconciles dependencies, and tracks composed    │
│ resource status.                                                           │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Generated API surface                                                      │
│ Application teams create simpler custom resources backed by multiple       │
│ Kubernetes objects.                                                        │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ The composed Kubernetes resources implement the higher-level API contract. │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| ResourceGraphDefinition API | ResourceGraphDefinition API |
| Controller | graph reconciliation |
| Generated instances/resources | Generated instances/resources |
| Status/value propagation | Status/value propagation |

## 关键数据流

```
平台定义 ResourceGraphDefinition
        │
        ▼
用户创建上层 instance
        │
        ▼
controller 渲染/协调底层 resources
        │
        ▼
从子资源聚合状态
        │
        ▼
提供简化的平台 API
```

## 设计决策与哲学

- **补齐 `higher-level API orchestration` 维度**：KRO 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Crossplane composition 偏跨云资源；KRO 偏 Kubernetes resource graph 和平台 API 组合。
- **选型价值**：它应和 [[kubernetes]], [[model-serving-operator]] 一起看，而不是孤立评估。

## 相关页面

- [[kro]]
- [[kubernetes]]
- [[model-serving-operator]]
