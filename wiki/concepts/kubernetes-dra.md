---
title: Kubernetes Dynamic Resource Allocation
tags: [concept, kubernetes, dra, gpu, device-management]
date: 2026-07-15
sources: [dra-driver-nvidia-gpu-architecture-analysis.md, src-kubernetes-keps-design-tracking.md]
related: [[dra-driver-nvidia-gpu]], [[device-plugin]], [[cdi]], [[gpu-sharing]], [[kubernetes]], [[kubernetes-dra-design-deep-dive]], [[k8s-v1.37-scheduling-node-dra-progress]]
---

# Kubernetes Dynamic Resource Allocation

Kubernetes DRA 是新一代特殊设备资源分配模型，用 ResourceClaim、ResourceSlice 和 driver plugin 让 GPU、DPU、RDMA 等设备的配置与调度更声明式、更可扩展。

## 和传统 device plugin 的区别

传统 [[device-plugin]] 主要把节点设备暴露成 extended resources，Pod 请求后由 kubelet Allocate。DRA 把资源 claim、参数、slice 和第三方 driver 放到调度语义里，让设备厂商能表达更复杂的配置，例如 dynamic MIG、VFIO、ComputeDomain。

## 代表项目

[[dra-driver-nvidia-gpu]] 是 NVIDIA GPU 的 DRA driver 实现，覆盖 ResourceClaim validation、NodePrepare/Unprepare、ResourceSlice、dynamic MIG/VFIO 和 ComputeDomain。

## Upstream 进展

2026-07-15 复核 `kubernetes/enhancements` 后，DRA 的近期重点已经从 `ResourceSlice` / `ResourceClaim` 基础模型，扩展到 workload 级 claim、可消费容量、共享容量、设备兼容组、ResourceClaim device status、DRA attributes Downward API 和标准 `numaNode` 属性。详见 [[k8s-v1.37-scheduling-node-dra-progress]] 和 [[kubernetes-dra-design-deep-dive]]。

对 GPU/AI 平台来说，最值得跟踪的是 `5729-resourceclaim-support-for-workloads`、`5075-dra-consumable-capacity`、`4817-resource-claim-device-status`、`5304-dra-attributes-downward-api` 和 `6072-dra-standard-numanode`，因为它们把设备容量、状态和拓扑从 driver 私有逻辑推进到 Kubernetes 可推理 API。

## 选型提示

短期生产稳定性仍常依赖 [[k8s-device-plugin]] + [[gpu-operator]]；面向未来的复杂设备配置和调度，应跟踪 DRA。
