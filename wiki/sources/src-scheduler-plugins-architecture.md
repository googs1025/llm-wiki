---
title: scheduler-plugins 架构与设计思路分析
tags: [architecture, kubernetes, scheduler, plugins]
date: 2026-06-14
sources: [scheduler-plugins-architecture-analysis.md]
related: ["[[scheduler-plugins]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# scheduler-plugins 架构与设计思路分析

> 原文：`raw/scheduler-plugins-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/scheduler-plugins · 优先级 P0

## 一句话定位

scheduler-plugins 是基于 kube-scheduler framework 的 out-of-tree 插件集合，用于研究和生产化调度扩展。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ scheduler-plugins          │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Framework  │ │ Scheduler bina │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Controller │ │ Integration te │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Framework plugins | queueSort/preFilter/filter/score/reserve 等扩展点 |
| Scheduler binary/config | Scheduler binary/config |
| Controllers/examples for capacity/placement policies | Controllers/examples for capacity/placement policies |
| Integration tests and manifests | Integration tests and manifests |

## 关键数据流

```
Pod 进入 scheduler queue
        │
        ▼
插件在各 extension point 参与决策
        │
        ▼
score/filter/reserve 改变节点选择
        │
        ▼
scheduler bind Pod
        │
        ▼
控制器/指标反馈策略效果
```

## 设计决策与哲学

- **补齐 `调度 / 资源` 维度**：scheduler-plugins 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Kueue 做 workload admission；scheduler-plugins 影响 Pod 到 Node 的 placement。
- **选型价值**：它应和 [[kubernetes]], [[llm-inference]] 一起看，而不是孤立评估。

## 相关页面

- [[scheduler-plugins]]
- [[kubernetes]]
- [[llm-inference]]
