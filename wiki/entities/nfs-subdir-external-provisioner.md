---
title: NFS Subdir External Provisioner
tags: [entity, kubernetes, storage, nfs]
date: 2026-06-14
sources: [nfs-subdir-external-provisioner-architecture-analysis.md]
related: ["[[nfs-subdir-external-provisioner]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# NFS Subdir External Provisioner

NFS Subdir External Provisioner 在远端 NFS server 上为 PVC 动态创建子目录，是轻量实验/中小集群常见 storage class。 详见 [[src-nfs-subdir-external-provisioner-architecture]]。

## 架构边界

它简单易用但隔离和性能弱于云盘/CSI，适合实验或非关键共享文件场景。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `NFS dynamic provisioning` 能力 | 适合，NFS Subdir External Provisioner 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[cloud-native-security]] 组合。 |

## 核心组件

- Provisioner controller: watch PVC/PV
- NFS backend: shared export path
- StorageClass parameters
- Cleanup/reclaim policy

## 选型提示

把 NFS Subdir External Provisioner 放在 `NFS dynamic provisioning` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
