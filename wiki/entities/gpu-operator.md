---
title: NVIDIA GPU Operator
tags: [entity, kubernetes, gpu, operator, nvidia]
date: 2026-06-12
sources: [gpu-operator-architecture-analysis.md]
related: [[device-plugin]], [[k8s-device-plugin]], [[kubernetes-dra]], [[gpu-sharing]], [[kubernetes]]
---

# NVIDIA GPU Operator

NVIDIA GPU 软件栈的 Kubernetes Operator，用 ClusterPolicy/NVIDIADriver CRD 管理 driver、container-toolkit、device-plugin、DCGM、MIG manager、sandbox/vGPU 等组件生命周期。详见 [[src-gpu-operator-architecture]]。

## 架构边界

GPU Operator 管“节点软件栈怎么安装、升级、保持健康”，不是单次 Pod GPU allocation 算法。它通常部署或管理 [[k8s-device-plugin]]，并与 [[hami]]、[[dra-driver-nvidia-gpu]] 处在不同层。

## 选型判断

- 集群管理员管理 NVIDIA 软件栈：GPU Operator。
- kubelet 层暴露 GPU：[[k8s-device-plugin]]。
- 新 DRA API 分配：[[dra-driver-nvidia-gpu]]。
- 共享/虚拟化调度：[[hami]]。
