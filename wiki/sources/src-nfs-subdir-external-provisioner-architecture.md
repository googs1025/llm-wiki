---
title: NFS Subdir External Provisioner 架构与设计思路分析
tags: [architecture, kubernetes, storage, nfs]
date: 2026-06-14
sources: [nfs-subdir-external-provisioner-architecture-analysis.md]
related: ["[[nfs-subdir-external-provisioner]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# NFS Subdir External Provisioner 架构与设计思路分析

> 原文：`raw/nfs-subdir-external-provisioner-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner · 优先级 P1

## 一句话定位

NFS Subdir External Provisioner 在远端 NFS server 上为 PVC 动态创建子目录，是轻量实验/中小集群常见 storage class。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ NFS Subdir External Provis │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Provisione │ │ NFS backend: s │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ StorageCla │ │ Cleanup/reclai │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Provisioner controller | watch PVC/PV |
| NFS backend | shared export path |
| StorageClass parameters | StorageClass parameters |
| Cleanup/reclaim policy | Cleanup/reclaim policy |

## 关键数据流

```
用户创建 PVC
        │
        ▼
external provisioner 创建 NFS 子目录
        │
        ▼
生成 PV 指向该路径
        │
        ▼
Pod 挂载 PVC
        │
        ▼
删除时按 reclaim policy 清理
```

## 设计决策与哲学

- **补齐 `NFS dynamic provisioning` 维度**：NFS Subdir External Provisioner 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它简单易用但隔离和性能弱于云盘/CSI，适合实验或非关键共享文件场景。
- **选型价值**：它应和 [[kubernetes]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[nfs-subdir-external-provisioner]]
- [[kubernetes]]
- [[cloud-native-security]]
