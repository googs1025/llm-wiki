---
title: Kubernetes Dynamic Resource Allocation
tags: [concept, kubernetes, dra, gpu, device-management]
date: 2026-06-12
sources: [dra-driver-nvidia-gpu-architecture-analysis.md]
related: [[dra-driver-nvidia-gpu]], [[device-plugin]], [[cdi]], [[gpu-sharing]], [[kubernetes]]
---

# Kubernetes Dynamic Resource Allocation

Kubernetes DRA 是新一代特殊设备资源分配模型，用 ResourceClaim、ResourceSlice 和 driver plugin 让 GPU、DPU、RDMA 等设备的配置与调度更声明式、更可扩展。

## 和传统 device plugin 的区别

传统 [[device-plugin]] 主要把节点设备暴露成 extended resources，Pod 请求后由 kubelet Allocate。DRA 把资源 claim、参数、slice 和第三方 driver 放到调度语义里，让设备厂商能表达更复杂的配置，例如 dynamic MIG、VFIO、ComputeDomain。

## 代表项目

[[dra-driver-nvidia-gpu]] 是 NVIDIA GPU 的 DRA driver 实现，覆盖 ResourceClaim validation、NodePrepare/Unprepare、ResourceSlice、dynamic MIG/VFIO 和 ComputeDomain。

## 选型提示

短期生产稳定性仍常依赖 [[k8s-device-plugin]] + [[gpu-operator]]；面向未来的复杂设备配置和调度，应跟踪 DRA。
