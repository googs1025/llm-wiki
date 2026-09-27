---
title: NVIDIA GPU Operator
tags: [entity, kubernetes, gpu, operator, nvidia]
date: 2026-09-27
sources: [gpu-operator-architecture-analysis.md]
related: ["[[device-plugin]]", "[[k8s-device-plugin]]", "[[kubernetes-dra]]", "[[gpu-sharing]]", "[[kubernetes]]", "[[cdi]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[dra-driver-nvidia-gpu]]", "[[hami]]"]
---

# NVIDIA GPU Operator

NVIDIA GPU 软件栈的 Kubernetes Operator，传统 ClusterPolicy/NVIDIADriver 路径管理 driver、container-toolkit、device-plugin、DCGM、MIG manager、sandbox/vGPU 等组件，当前 GPUCluster 提供独立的 DRA 管理路径。历史架构详见 [[src-gpu-operator-architecture]]。

证据说明：2026-09-27 官方默认分支快照为 [`60526e35efee`](https://github.com/NVIDIA/gpu-operator/commit/60526e35efeeedef584d8f40db0bac8864f98f26)，commit 不代表 release。[[src-gpu-operator-architecture]] 保留 2026-06-12 的 raw-backed Source；当前分层见 [[k8s-gpu-device-stack]]，DRA 分配与节点准备见 [[kubernetes-dra-design-deep-dive]]。

## 在 M5-C Device / GPU 地图中的位置

Operator reconcile NVIDIA 节点软件及选定 operands，不选择单次 Pod 获得哪块 GPU。按 [26.7 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)，ClusterPolicy 对应 [[k8s-device-plugin]] 路径，GPUCluster 对应 [[dra-driver-nvidia-gpu]] 管理路径，两者不能在同一集群并存，也不支持直接原地迁移。GPUCluster 需独立 NVIDIADriver/预装 driver 和兼容 [[cdi]] 的 runtime；这些条件不能由 [[node-feature-discovery]] 标签或 Operator Ready 替代。

## 架构边界

GPU Operator 管“节点软件栈怎么安装、升级、保持健康”，不是单次 Pod GPU allocation 算法。它通常部署或管理 [[k8s-device-plugin]]，并与 [[hami]]、[[dra-driver-nvidia-gpu]] 处在不同层。

## 选型判断

- 集群管理员管理 NVIDIA 软件栈：GPU Operator。
- kubelet 层暴露 GPU：[[k8s-device-plugin]]。
- 新 DRA API 分配：[[dra-driver-nvidia-gpu]]。
- 共享/虚拟化调度：[[hami]]。
