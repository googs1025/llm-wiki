---
title: DRA Driver for NVIDIA GPUs
tags: [entity, kubernetes, gpu, dra, nvidia]
date: 2026-06-12
sources: [dra-driver-nvidia-gpu-architecture-analysis.md]
related: [[kubernetes-dra]], [[device-plugin]], [[cdi]], [[gpu-sharing]], [[k8s-device-plugin]]
---

# DRA Driver for NVIDIA GPUs

NVIDIA GPU 的 Kubernetes Dynamic Resource Allocation driver，围绕 ResourceClaim、ResourceSlice、NodePrepareResources、ComputeDomain/Multi-Node NVLink、动态 MIG/VFIO 配置展开。详见 [[src-dra-driver-nvidia-gpu-architecture]]。

## 架构边界

它代表 K8s 新一代设备资源 API 路线，不是传统 device plugin API 的小补丁。与 [[k8s-device-plugin]] 相比，它把资源声明、配置和调度语义前移到 DRA；与 [[hami]] 相比，它更贴近 Kubernetes upstream DRA 模型。

## 选型判断

适合关注 Kubernetes 1.32+ DRA、ResourceClaim/ResourceSlice、dynamic MIG、ComputeDomain 的平台团队。

短期只需要稳定 GPU extended resource 暴露时，仍应理解 [[k8s-device-plugin]] 和 [[gpu-operator]]。
