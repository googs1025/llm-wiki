---
title: Node Feature Discovery
tags: [entity, kubernetes, node, hardware]
date: 2026-06-14
sources: [node-feature-discovery-architecture-analysis.md]
related: ["[[node-feature-discovery]]", "[[kubernetes]]", "[[llm-inference]]", "[[gpu-sharing]]"]
---

# Node Feature Discovery

Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。 详见 [[src-node-feature-discovery-architecture]]。

## 架构边界

device plugin 暴露可分配资源；NFD 暴露节点能力标签，常作为 GPU/NUMA/硬件调度前置信号。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `节点能力发现` 能力 | 适合，Node Feature Discovery 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[llm-inference]], [[gpu-sharing]] 组合。 |

## 核心组件

- nfd-worker: node local feature sources
- nfd-master/gc: label publication and cleanup
- Feature sources: cpu, kernel, pci, usb, custom hooks
- Rules: custom feature labels

## 选型提示

把 Node Feature Discovery 放在 `节点能力发现` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
