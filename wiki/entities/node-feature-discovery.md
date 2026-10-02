---
title: Node Feature Discovery
tags: [entity, kubernetes, node, hardware]
date: 2026-09-27
sources: [node-feature-discovery-architecture-analysis.md]
related: ["[[kubernetes]]", "[[llm-inference]]", "[[gpu-sharing]]", "[[device-plugin]]", "[[kubernetes-dra]]", "[[cdi]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[gpu-operator]]", "[[k8s-device-plugin]]", "[[dra-driver-nvidia-gpu]]", "[[hami]]"]
---

# Node Feature Discovery

Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。 详见 [[src-node-feature-discovery-architecture]]。

证据说明：2026-09-27 官方默认分支快照为 [`386fda4332ba`](https://github.com/kubernetes-sigs/node-feature-discovery/commit/386fda4332ba5f049c6f0b107f9a58cd46f5af04)，commit 不代表 release。[[src-node-feature-discovery-architecture]] 保留 2026-06-14 的 raw-backed Source；当前分层见 [[k8s-gpu-device-stack]]，DRA 分配与节点准备见 [[kubernetes-dra-design-deep-dive]]。

## 在 M5-C Device / GPU 地图中的位置

NFD worker 检测节点特征，master 发布 labels/规则结果，topology-updater 维护 NodeResourceTopology，GC 清理过期对象。它为 [[gpu-operator]] 及 placement 提供能力信号，不分配每个 Pod 的设备；[[k8s-device-plugin]] / [[dra-driver-nvidia-gpu]] 管各自分配路径，[[hami]] 的共享记账也不能只依赖能力标签。

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
