---
title: Kubespray
tags: [entity, kubernetes, cluster-lifecycle, ansible]
date: 2026-06-14
sources: [kubespray-architecture-analysis.md]
related: ["[[kubespray]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# Kubespray

Kubespray 用 Ansible inventory/roles 部署生产可用 Kubernetes 集群，覆盖 kubeadm、network plugin、etcd、HA 和云/裸金属差异。 详见 [[src-kubespray-architecture]]。

## 架构边界

Cluster API 是 K8s-native 声明式生命周期；Kubespray 是 Ansible-based 集群安装/升级自动化。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `计算 / 集群部署` 能力 | 适合，Kubespray 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[cloud-native-security]] 组合。 |

## 核心组件

- Inventory: hosts/group_vars/cluster config
- Ansible roles: kubeadm/etcd/network/storage/addons
- Playbooks: cluster.yml/upgrade/reset
- Provider support: bare metal/cloud/on-prem

## 选型提示

把 Kubespray 放在 `计算 / 集群部署` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
