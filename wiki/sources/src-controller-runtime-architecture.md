---
title: controller-runtime 架构与设计思路分析
tags: [architecture, kubernetes, controller, operator]
date: 2026-06-14
sources: [controller-runtime-architecture-analysis.md]
related: ["[[controller-runtime]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]"]
---

# controller-runtime 架构与设计思路分析

> 原文：`raw/controller-runtime-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/controller-runtime · 优先级 P0

## 一句话定位

controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ controller-runtime         │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Manager: l │ │ Cache/Client:  │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Controller │ │ Webhook/envtes │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Manager | lifecycle、leader election、scheme、metrics |
| Cache/Client | informer cache + API writer |
| Controller/Reconciler | workqueue and reconcile loop |
| Webhook/envtest | admission and test harness |

## 关键数据流

```
manager 启动 cache/webhook/controllers
        │
        ▼
watch 事件进入 workqueue
        │
        ▼
reconciler 读取 cache/API
        │
        ▼
patch status/finalizer/owned resources
        │
        ▼
错误重试或完成
```

## 设计决策与哲学

- **补齐 `Operator SDK` 维度**：controller-runtime 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：client-go 是底层机制；controller-runtime 是现代 operator 工程默认抽象；kubebuilder 在其上做项目脚手架。
- **选型价值**：它应和 [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] 一起看，而不是孤立评估。

## 相关页面

- [[controller-runtime]]
- [[kubernetes]]
- [[model-serving-operator]]
- [[declarative-agent-management]]
