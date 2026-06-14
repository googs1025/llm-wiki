---
title: kind
tags: [entity, kubernetes, testing, runtime]
date: 2026-06-14
sources: [kind-architecture-analysis.md]
related: ["[[kind]]", "[[kubernetes]]", "[[model-serving-operator]]"]
---

# kind

kind 是 Kubernetes IN Docker，用 Docker/Podman 容器模拟节点并用 kubeadm 拉起本地测试集群。 详见 [[src-kind-architecture]]。

## 架构边界

kind 适合 controller/operator CI 和本地测试；kubespray 适合真实机器的生产/准生产集群部署。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `计算 / 测试集群` 能力 | 适合，kind 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]] 组合。 |

## 核心组件

- CLI: kind create/delete/load/export
- Node image: systemd/kubelet/containerd/kubeadm
- Cluster config: control-plane/worker/networking
- Provider: docker/podman node lifecycle

## 选型提示

把 kind 放在 `计算 / 测试集群` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
