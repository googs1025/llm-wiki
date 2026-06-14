---
title: sig-storage-lib-external-provisioner 架构与设计思路分析
tags: [architecture, kubernetes, storage, provisioner]
date: 2026-06-14
sources: [sig-storage-lib-external-provisioner-architecture-analysis.md]
related: ["[[sig-storage-lib-external-provisioner]]", "[[kubernetes]]"]
---

# sig-storage-lib-external-provisioner 架构与设计思路分析

> 原文：`raw/sig-storage-lib-external-provisioner-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/sig-storage-lib-external-provisioner · 优先级 P1

## 一句话定位

sig-storage-lib-external-provisioner 是 Kubernetes dynamic volume provisioner 的库，抽象 PVC watch、PV 创建、reclaim 和 controller lifecycle。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ External storage provisioner code                                          │
│ Driver authors need common PVC/PV controller mechanics.                    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Provisioner library                                                        │
│ Watches claims, manages finalizers, events, leader election, and           │
│ controller flow.                                                           │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Driver hooks                                                               │
│ Provision and delete callbacks implement storage-system-specific behavior. │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ External storage appears to Kubernetes as PersistentVolumes and bound      │
│ claims.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| ProvisionController | PVC/PV watch and sync |
| Provisioner interface | Provisioner interface |
| Leader election/events | Leader election/events |
| Reclaim/delete handling | Reclaim/delete handling |

## 关键数据流

```
controller watch PVC
        │
        ▼
调用实现方 Provision()
        │
        ▼
创建 PV 并绑定
        │
        ▼
PVC/PV 删除时调用 Delete()
        │
        ▼
事件和错误重试
```

## 设计决策与哲学

- **补齐 `external provisioner library` 维度**：sig-storage-lib-external-provisioner 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：具体 provisioner 如 NFS provisioner 处理后端细节；这个库处理 Kubernetes 控制器通用模式。
- **选型价值**：它应和 [[kubernetes]] 一起看，而不是孤立评估。

## 相关页面

- [[sig-storage-lib-external-provisioner]]
- [[kubernetes]]
