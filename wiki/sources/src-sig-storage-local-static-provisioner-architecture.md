---
title: Local Static Provisioner 架构与设计思路分析
tags: [architecture, kubernetes, storage, local-pv]
date: 2026-06-14
sources: [sig-storage-local-static-provisioner-architecture-analysis.md]
related: ["[[sig-storage-local-static-provisioner]]", "[[kubernetes]]", "[[llm-inference]]"]
---

# Local Static Provisioner 架构与设计思路分析

> 原文：`raw/sig-storage-local-static-provisioner-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner · 优先级 P1

## 一句话定位

Local Static Provisioner 发现节点本地磁盘/目录并创建 local PersistentVolume，配合调度绑定把数据固定到节点。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Local disk inventory                                                       │
│ Nodes expose disks or directories intended for local PersistentVolumes.    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Local static provisioner DaemonSet                                         │
│ Discovers local paths and creates PVs with node affinity.                  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Cleanup policy                                                             │
│ Handles released volumes, reuse behavior, and administrator-defined        │
│ discovery rules.                                                           │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Scheduler binds Pods to the node that owns the selected local PV.          │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Discovery daemon | scan mount directories |
| PV controller | create/delete local PV |
| Node affinity | bind PV to node |
| Cleanup scripts/classes | Cleanup scripts/classes |

## 关键数据流

```
节点挂载本地盘
        │
        ▼
daemon 发现可用路径
        │
        ▼
创建带 node affinity 的 PV
        │
        ▼
PVC 绑定后 Pod 调度到对应节点
        │
        ▼
释放后清理或保留
```

## 设计决策与哲学

- **补齐 `Local PV static provisioning` 维度**：Local Static Provisioner 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：local PV 性能高但节点绑定强；动态网络存储更灵活但可能牺牲本地性能。
- **选型价值**：它应和 [[kubernetes]], [[llm-inference]] 一起看，而不是孤立评估。

## 相关页面

- [[sig-storage-local-static-provisioner]]
- [[kubernetes]]
- [[llm-inference]]
