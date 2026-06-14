---
title: Cluster API
tags: [entity, kubernetes, cluster-lifecycle, operator]
date: 2026-06-14
sources: [cluster-api-architecture-analysis.md]
related: ["[[cluster-api]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# Cluster API

Cluster API 用声明式 API 管理 Kubernetes 集群生命周期，把 Cluster/Machine/MachineDeployment 和 provider infra/bootstrap/control-plane 拆成可组合控制器。 详见 [[src-cluster-api-architecture]]。

## 架构边界

Kubespray 偏 Ansible 部署；Cluster API 偏 Kubernetes-native 声明式集群生命周期。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `集群生命周期` 能力 | 适合，Cluster API 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[cloud-native-security]] 组合。 |

## 核心组件

- Core API: Cluster, Machine, MachineDeployment, MachineSet
- Providers: infrastructure/bootstrap/control-plane
- Controllers: reconcile desired cluster state
- Clusterctl: provider init/move/upgrade workflow

## 选型提示

把 Cluster API 放在 `集群生命周期` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
