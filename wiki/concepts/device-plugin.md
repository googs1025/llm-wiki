---
title: Kubernetes Device Plugin
tags: [concept, kubernetes, device-plugin, gpu, runtime]
date: 2026-09-27
sources: [k8s-device-plugin-architecture-analysis.md, k8s-gpu-device-plugins-stars.md]
related: ["[[k8s-device-plugin]]", "[[gpu-operator]]", "[[gpu-sharing]]", "[[cdi]]", "[[kubernetes-dra]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[dra-driver-nvidia-gpu]]", "[[hami]]"]
---

# Kubernetes Device Plugin

Kubernetes Device Plugin 是 kubelet 扩展机制，让厂商把 GPU、FPGA、RDMA 等特殊硬件注册为节点资源，并在 kubelet 调用 Allocate 时返回设备与容器配置。

## 在 M5-C Device / GPU 地图中的位置

Device Plugin 向 kubelet 注册资源名与 endpoint，通过 ListAndWatch 发布设备/health，再由 kubelet 更新节点 extended-resource capacity/allocatable。scheduler 按节点资源选择位置，节点侧 Allocate 返回 env、mount 或 [[cdi]] 交接信息；完整流程见 [[k8s-gpu-device-stack]] 的 D2。[[node-feature-discovery]] 提供能力标签，[[gpu-operator]] 管受管组件，均不替代本次设备分配。

[[dra-driver-nvidia-gpu]] 的 Claim/库存/Prepare 路径见 [[kubernetes-dra-design-deep-dive]]。两种 API 不应让同一设备被重复分配；例如 [[hami]] 与 NVIDIA 官方 plugin 不能在同一节点争用 `nvidia.com/gpu`，共存须明确资源所有权与安装模式。

## 核心流程

设备发现后建立 plugin Unix socket，向 kubelet 注册并通过 ListAndWatch 报告库存/健康；Pod 请求资源并绑定节点后，kubelet 选择设备 ID、调用 Allocate，再经容器配置将设备交给 runtime。

## 代表项目

[[k8s-device-plugin]] 是 NVIDIA 官方实现，覆盖 NVML/CUDA/Tegra/VFIO discovery、MIG/MPS/time-slicing、health check、env/volume/CDI device list strategy。

## 与 DRA 的关系

DRA 不是简单替代所有 device plugin，而是为更复杂的声明式资源配置提供新 API。理解 device plugin 仍是理解 GPU on Kubernetes 的基础。
