---
title: Local Static Provisioner
tags: [entity, kubernetes, storage, local-pv]
date: 2026-06-14
sources: [sig-storage-local-static-provisioner-architecture-analysis.md]
related: ["[[sig-storage-local-static-provisioner]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# Local Static Provisioner

Local Static Provisioner 发现节点本地磁盘/目录并创建 local PersistentVolume，配合调度绑定把数据固定到节点。 详见 [[src-sig-storage-local-static-provisioner-architecture]]。

## 架构边界

local PV 性能高但节点绑定强；动态网络存储更灵活但可能牺牲本地性能。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Local PV static provisioning` 能力 | 适合，Local Static Provisioner 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[llm-inference]] 组合。 |

## 核心组件

- Discovery daemon: scan mount directories
- PV controller: create/delete local PV
- Node affinity: bind PV to node
- Cleanup scripts/classes

## 选型提示

把 Local Static Provisioner 放在 `Local PV static provisioning` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
