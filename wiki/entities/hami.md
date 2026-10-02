---
title: HAMi
tags: [entity, kubernetes, gpu-sharing, vgpu, scheduler]
date: 2026-09-27
sources: [hami-architecture-analysis.md]
related: ["[[gpu-sharing]]", "[[device-plugin]]", "[[kubernetes-dra]]", "[[cdi]]", "[[k8s-device-plugin]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[gpu-operator]]", "[[dra-driver-nvidia-gpu]]"]
---

# HAMi

Kubernetes 异构 GPU sharing / vGPU 项目，通过 mutating webhook、scheduler extender、device plugin 和多厂商设备后端实现 GPU memory/core/count 等细粒度共享。详见 [[src-hami-architecture]]。

证据说明：2026-09-27 官方默认分支快照为 [`a2dd191b2e7f`](https://github.com/Project-HAMi/HAMi/commit/a2dd191b2e7fb1f289833e9b4fcef16289ec89b3)，commit 不代表 release。[[src-hami-architecture]] 保留 2026-06-12 的 raw-backed Source；当前分层见 [[k8s-gpu-device-stack]]，Claim/Prepare 对照见 [[kubernetes-dra-design-deep-dive]]。

## 在 M5-C Device / GPU 地图中的位置

经典路径由 scheduler/extender 计算设备 reservation，经 Pod annotations 交接给 device-plugin Allocate，再由 HAMi-core 实施容器侧 memory/core 隔离。[[node-feature-discovery]] 的能力标签不能替代共享设备记账；[[gpu-operator]] 可管软件组件，但须避免其 [[k8s-device-plugin]] operand 与 HAMi 在同一节点争用 `nvidia.com/gpu`。

HAMi-DRA 改变 Claim/设备分配路径，不自动改变 HAMi-core 的隔离能力；与 [[dra-driver-nvidia-gpu]] 对照时应分别核验设备支持、分配语义与 runtime 隔离。依据见 [HAMi Protocol](https://project-hami.io/docs/developers/protocol)、[FAQ](https://project-hami.io/docs/faq) 与 [安装路线对比](https://project-hami.io/docs/get-started/choose-your-setup)。

## 架构边界

HAMi 不是官方基础 device plugin，也不是 GPU 软件栈 operator。它把调度、quota、annotation、device plugin 和隔离机制结合起来，解决“一个物理 GPU 如何被多个 workload 细粒度共享”。

## 选型判断

- 暴露 NVIDIA GPU 给 Kubernetes：看 [[k8s-device-plugin]]。
- 管理 driver/runtime/device-plugin/DCGM：看 [[gpu-operator]]。
- 细粒度 vGPU / GPU sharing：看 HAMi。
- 走 ResourceClaim/ResourceSlice：对照 HAMi-DRA 与 [[dra-driver-nvidia-gpu]] 的设备支持和隔离需求。
