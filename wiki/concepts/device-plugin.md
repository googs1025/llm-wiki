---
title: Kubernetes Device Plugin
tags: [concept, kubernetes, device-plugin, gpu, runtime]
date: 2026-06-12
sources: [k8s-device-plugin-architecture-analysis.md, k8s-gpu-device-plugins-stars.md]
related: [[k8s-device-plugin]], [[gpu-operator]], [[gpu-sharing]], [[cdi]], [[kubernetes-dra]]
---

# Kubernetes Device Plugin

Kubernetes Device Plugin 是 kubelet 扩展机制，让厂商把 GPU、FPGA、RDMA 等特殊硬件注册为节点资源，并在 Pod Allocate 阶段把设备交给容器。

## 核心流程

```
Device discovery -> plugin Unix socket -> kubelet Register/ListAndWatch -> Pod requests resource -> Allocate returns env/mount/CDI edits
```

## 代表项目

[[k8s-device-plugin]] 是 NVIDIA 官方实现，覆盖 NVML/CUDA/Tegra/VFIO discovery、MIG/MPS/time-slicing、health check、env/volume/CDI device list strategy。

## 与 DRA 的关系

DRA 不是简单替代所有 device plugin，而是为更复杂的声明式资源配置提供新 API。理解 device plugin 仍是理解 GPU on Kubernetes 的基础。
