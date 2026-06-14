---
title: KWOK 架构与设计思路分析
tags: [architecture, kubernetes, simulator, testing]
date: 2026-06-14
sources: [kwok-architecture-analysis.md]
related: ["[[kwok]]", "[[kubernetes]]", "[[model-serving-operator]]"]
---

# KWOK 架构与设计思路分析

> 原文：`raw/kwok-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kwok · 优先级 P1

## 一句话定位

KWOK 是 Kubernetes WithOut Kubelet，用 fake nodes/pods 模拟大规模集群，适合调度、控制器和 scalability 测试。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ KWOK                       │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ kwok contr │ │ kwokctl: clust │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Stage/Conf │ │ Integrations:  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| kwok controller | fake kubelet behavior |
| kwokctl | cluster lifecycle |
| Stage/Configuration | pod/node condition transitions |
| Integrations | kind/kube-apiserver tests |

## 关键数据流

```
创建 KWOK cluster 或接入现有 apiserver
        │
        ▼
声明大量 fake nodes/pods
        │
        ▼
kwok controller 模拟状态变化
        │
        ▼
被测 scheduler/controller 观察大规模对象
        │
        ▼
收集性能和行为结果
```

## 设计决策与哲学

- **补齐 `大规模集群模拟` 维度**：KWOK 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：kind 提供真实小集群；KWOK 提供便宜的大规模对象模拟。
- **选型价值**：它应和 [[kubernetes]], [[model-serving-operator]] 一起看，而不是孤立评估。

## 相关页面

- [[kwok]]
- [[kubernetes]]
- [[model-serving-operator]]
