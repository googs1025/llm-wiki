---
title: NVIDIA k8s-device-plugin
tags: [entity, kubernetes, gpu, device-plugin, nvidia]
date: 2026-09-27
sources: [k8s-device-plugin-architecture-analysis.md]
related: ["[[device-plugin]]", "[[cdi]]", "[[gpu-sharing]]", "[[gpu-operator]]", "[[kubernetes-dra]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[dra-driver-nvidia-gpu]]", "[[hami]]"]
---

# NVIDIA k8s-device-plugin

NVIDIA 官方 Kubernetes device plugin，把 GPU/MIG/vGPU 发现为 kubelet extended resources，并在 Allocate 阶段通过 env、volume-mounts 或 CDI annotations 把设备传给容器。详见 [[src-k8s-device-plugin-architecture]]。

证据说明：2026-09-27 官方默认分支快照为 [`86142cf1a93f`](https://github.com/NVIDIA/k8s-device-plugin/commit/86142cf1a93fb68a99c5927b9599e13392e27e15)，commit 不代表 release。[[src-k8s-device-plugin-architecture]] 保留 2026-06-12 的 raw-backed Source；当前分层见 [[k8s-gpu-device-stack]]，DRA 对照路径见 [[kubernetes-dra-design-deep-dive]]。

## 在 M5-C Device / GPU 地图中的位置

插件向 kubelet 注册 extended resource，通过 ListAndWatch 报告设备与健康，在 Allocate 中返回设备交接配置；它没有 [[kubernetes-dra]] 的丰富 Claim/库存/条件模型。[[node-feature-discovery]] 的发现信号和 [[gpu-operator]] 的组件部署是相邻职责；其与 [[dra-driver-nvidia-gpu]] 的路径选择应按所需 API、driver 支持与资源所有权评估。

## 架构边界

它是 GPU 暴露基础层，不负责安装 driver，也不负责全局调度策略。GPU Operator 常用来部署和管理它；HAMi 经典路径使用自己的 device plugin，不能与官方插件在同一节点争用 `nvidia.com/gpu`；DRA driver 则采用 ResourceClaim/ResourceSlice 分配模型。

## 选型判断

适合需要理解 Kubernetes GPU allocation 基础机制、MIG/MPS/time-slicing/CDI 策略的人。做 AI serving 平台时，它是 [[gpu-operator]]、[[hami]]、[[kubernetes-dra]] 前必须理解的底层节点。
