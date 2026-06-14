---
title: Node Feature Discovery 架构与设计思路分析
tags: [architecture, kubernetes, node, hardware]
date: 2026-06-14
sources: [node-feature-discovery-architecture-analysis.md]
related: ["[[node-feature-discovery]]", "[[kubernetes]]", "[[llm-inference]]", "[[gpu-sharing]]"]
---

# Node Feature Discovery 架构与设计思路分析

> 原文：`raw/node-feature-discovery-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/node-feature-discovery · 优先级 P1

## 一句话定位

Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Node Feature Discovery     │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ nfd-worker │ │ nfd-master/gc: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Feature so │ │ Rules: custom  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| nfd-worker | node local feature sources |
| nfd-master/gc | label publication and cleanup |
| Feature sources | cpu, kernel, pci, usb, custom hooks |
| Rules | custom feature labels |

## 关键数据流

```
worker 扫描节点硬件和系统信息
        │
        ▼
生成 feature set
        │
        ▼
master 写 node labels/extended info
        │
        ▼
scheduler/operator 根据 labels 选择节点
        │
        ▼
变化时更新或清理
```

## 设计决策与哲学

- **补齐 `节点能力发现` 维度**：Node Feature Discovery 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：device plugin 暴露可分配资源；NFD 暴露节点能力标签，常作为 GPU/NUMA/硬件调度前置信号。
- **选型价值**：它应和 [[kubernetes]], [[llm-inference]], [[gpu-sharing]] 一起看，而不是孤立评估。

## 相关页面

- [[node-feature-discovery]]
- [[kubernetes]]
- [[llm-inference]]
- [[gpu-sharing]]
