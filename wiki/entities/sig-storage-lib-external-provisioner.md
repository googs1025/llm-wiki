---
title: sig-storage-lib-external-provisioner
tags: [entity, kubernetes, storage, provisioner]
date: 2026-06-14
sources: [sig-storage-lib-external-provisioner-architecture-analysis.md]
related: ["[[sig-storage-lib-external-provisioner]]", "[[kubernetes]]"]
---

# sig-storage-lib-external-provisioner

sig-storage-lib-external-provisioner 是 Kubernetes dynamic volume provisioner 的库，抽象 PVC watch、PV 创建、reclaim 和 controller lifecycle。 详见 [[src-sig-storage-lib-external-provisioner-architecture]]。

## 架构边界

具体 provisioner 如 NFS provisioner 处理后端细节；这个库处理 Kubernetes 控制器通用模式。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `external provisioner library` 能力 | 适合，sig-storage-lib-external-provisioner 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]] 组合。 |

## 核心组件

- ProvisionController: PVC/PV watch and sync
- Provisioner interface
- Leader election/events
- Reclaim/delete handling

## 选型提示

把 sig-storage-lib-external-provisioner 放在 `external provisioner library` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
