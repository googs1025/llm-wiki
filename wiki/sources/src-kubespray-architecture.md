---
title: Kubespray 架构与设计思路分析
tags: [architecture, kubernetes, cluster-lifecycle, ansible]
date: 2026-06-14
sources: [kubespray-architecture-analysis.md]
related: ["[[kubespray]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# Kubespray 架构与设计思路分析

> 原文：`raw/kubespray-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kubespray · 优先级 P0

## 一句话定位

Kubespray 用 Ansible inventory/roles 部署生产可用 Kubernetes 集群，覆盖 kubeadm、network plugin、etcd、HA 和云/裸金属差异。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Cluster deployment inventory                                               │
│ Hosts, variables, networking, runtime, and add-ons define desired cluster  │
│ shape.                                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Kubespray Ansible playbooks                                                │
│ Roles prepare OS, container runtime, kubeadm, control plane, workers, and  │
│ CNI.                                                                       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Lifecycle operations                                                       │
│ Install, upgrade, scale, reset, and configure production Kubernetes        │
│ clusters.                                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Bare-metal, VM, or cloud Kubernetes clusters managed through repeatable    │
│ automation.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Inventory | hosts/group_vars/cluster config |
| Ansible roles | kubeadm/etcd/network/storage/addons |
| Playbooks | cluster.yml/upgrade/reset |
| Provider support | bare metal/cloud/on-prem |

## 关键数据流

```
用户准备 inventory
        │
        ▼
Ansible 配置 OS/runtime/etcd
        │
        ▼
kubeadm 初始化 control plane
        │
        ▼
加入 worker nodes
        │
        ▼
安装 CNI/addons 并验证
```

## 设计决策与哲学

- **补齐 `计算 / 集群部署` 维度**：Kubespray 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Cluster API 是 K8s-native 声明式生命周期；Kubespray 是 Ansible-based 集群安装/升级自动化。
- **选型价值**：它应和 [[kubernetes]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[kubespray]]
- [[kubernetes]]
- [[cloud-native-security]]
