---
title: HAMi
tags: [entity, kubernetes, gpu-sharing, vgpu, scheduler]
date: 2026-06-12
sources: [hami-architecture-analysis.md]
related: [[gpu-sharing]], [[device-plugin]], [[kubernetes-dra]], [[cdi]], [[k8s-device-plugin]]
---

# HAMi

Kubernetes 异构 GPU sharing / vGPU 项目，通过 mutating webhook、scheduler extender、device plugin 和多厂商设备后端实现 GPU memory/core/count 等细粒度共享。详见 [[src-hami-architecture]]。

## 架构边界

HAMi 不是官方基础 device plugin，也不是 GPU 软件栈 operator。它把调度、quota、annotation、device plugin 和隔离机制结合起来，解决“一个物理 GPU 如何被多个 workload 细粒度共享”。

## 选型判断

- 暴露 NVIDIA GPU 给 Kubernetes：看 [[k8s-device-plugin]]。
- 管理 driver/runtime/device-plugin/DCGM：看 [[gpu-operator]]。
- 细粒度 vGPU / GPU sharing：看 HAMi。
- 走下一代 ResourceClaim/ResourceSlice：看 [[dra-driver-nvidia-gpu]]。
