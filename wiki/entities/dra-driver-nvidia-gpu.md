---
title: DRA Driver for NVIDIA GPUs
tags: [entity, kubernetes, gpu, dra, nvidia]
date: 2026-09-27
sources: [dra-driver-nvidia-gpu-architecture-analysis.md]
related: ["[[kubernetes-dra]]", "[[device-plugin]]", "[[cdi]]", "[[gpu-sharing]]", "[[k8s-device-plugin]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[gpu-operator]]", "[[hami]]"]
---

# DRA Driver for NVIDIA GPUs

NVIDIA GPU 的 Kubernetes Dynamic Resource Allocation driver，围绕 ResourceClaim、ResourceSlice、NodePrepareResources、ComputeDomain/Multi-Node NVLink、动态 MIG/VFIO 配置展开。详见 [[src-dra-driver-nvidia-gpu-architecture]]。

证据说明：2026-09-27 通过 NVIDIA 仓库入口查询的官方默认分支快照为 [`495bf4c59b94`](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/commit/495bf4c59b9423080aa1fe2163955f44a495012c)，链接采用 GitHub 返回的规范仓库，commit 不代表 release。[[src-dra-driver-nvidia-gpu-architecture]] 保留 2026-06-12 的 raw-backed Source；当前分层见 [[k8s-gpu-device-stack]]，阶段与生命周期见 [[kubernetes-dra-design-deep-dive]]。

## 在 M5-C Device / GPU 地图中的位置

driver 提供 DeviceClass 等安装配置、发布 ResourceSlice 库存，并通过 NodePrepareResources/NodeUnprepareResources 执行设备配置与 [[cdi]] 交接；GPU 与 ComputeDomain 分别处理本机设备和 Multi-Node NVLink 相关生命周期。这不同于 [[k8s-device-plugin]] 的传统 extended-resource Allocate 路径，也不等于 [[node-feature-discovery]] 的节点能力发现。

厂商支持矩阵必须与 Kubernetes feature stage 分开：锚定仓库 README 对独立 GPU plugin 与 ComputeDomain 的支持说明，不能直接套用到 [[gpu-operator]] 26.7 所管理版本。基础 DRA stable 不保证所有动态 MIG/VFIO/sharing 功能同样稳定。

## 架构边界

它采用 Kubernetes DRA 设备资源 API，不是传统 device plugin API 的小补丁。与 [[k8s-device-plugin]] 相比，它把资源声明、配置和调度语义前移到 Claim 模型；[[hami]] 也有 DRA 接入，比较时应看厂商设备配置能力、分配路径与容器隔离，而非是否使用 DRA。

## 选型判断

适合需要 ResourceClaim/ResourceSlice、动态设备配置或 ComputeDomain 的平台团队；部署应按所选 Kubernetes/driver release 核对 API、feature gates 和硬件支持。

只需要 GPU extended resource 暴露时可评估 [[k8s-device-plugin]] 和 [[gpu-operator]]；选择 DRA 时须独立验证分配、节点准备与回收全链路。
