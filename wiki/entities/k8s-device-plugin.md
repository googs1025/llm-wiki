---
title: NVIDIA k8s-device-plugin
tags: [entity, kubernetes, gpu, device-plugin, nvidia]
date: 2026-06-12
sources: [k8s-device-plugin-architecture-analysis.md]
related: [[device-plugin]], [[cdi]], [[gpu-sharing]], [[gpu-operator]], [[kubernetes-dra]]
---

# NVIDIA k8s-device-plugin

NVIDIA 官方 Kubernetes device plugin，把 GPU/MIG/vGPU 发现为 kubelet extended resources，并在 Allocate 阶段通过 env、volume-mounts 或 CDI annotations 把设备传给容器。详见 [[src-k8s-device-plugin-architecture]]。

## 架构边界

它是 GPU 暴露基础层，不负责安装 driver，也不负责全局调度策略。GPU Operator 常用来部署和管理它；HAMi 在它之上或旁侧扩展细粒度共享；DRA driver 则代表新的 ResourceClaim/ResourceSlice API 路线。

## 选型判断

适合需要理解 Kubernetes GPU allocation 基础机制、MIG/MPS/time-slicing/CDI 策略的人。做 AI serving 平台时，它是 [[gpu-operator]]、[[hami]]、[[kubernetes-dra]] 前必须理解的底层节点。
