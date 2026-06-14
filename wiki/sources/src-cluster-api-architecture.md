---
title: Cluster API 架构与设计思路分析
tags: [architecture, kubernetes, cluster-lifecycle, operator]
date: 2026-06-14
sources: [cluster-api-architecture-analysis.md]
related: ["[[cluster-api]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# Cluster API 架构与设计思路分析

> 原文：`raw/cluster-api-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/cluster-api · 优先级 P0

## 一句话定位

Cluster API 用声明式 API 管理 Kubernetes 集群生命周期，把 Cluster/Machine/MachineDeployment 和 provider infra/bootstrap/control-plane 拆成可组合控制器。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Cluster API                │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Core API:  │ │ Providers: inf │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Controller │ │ Clusterctl: pr │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Core API | Cluster, Machine, MachineDeployment, MachineSet |
| Providers | infrastructure/bootstrap/control-plane |
| Controllers | reconcile desired cluster state |
| Clusterctl | provider init/move/upgrade workflow |

## 关键数据流

```
用户声明 Cluster/Machine topology
        │
        ▼
CAPI core controller 协调对象
        │
        ▼
provider controller 创建云/裸金属资源
        │
        ▼
bootstrap/control-plane provider 初始化节点
        │
        ▼
状态回写并支持升级/迁移
```

## 设计决策与哲学

- **补齐 `集群生命周期` 维度**：Cluster API 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Kubespray 偏 Ansible 部署；Cluster API 偏 Kubernetes-native 声明式集群生命周期。
- **选型价值**：它应和 [[kubernetes]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[cluster-api]]
- [[kubernetes]]
- [[cloud-native-security]]
