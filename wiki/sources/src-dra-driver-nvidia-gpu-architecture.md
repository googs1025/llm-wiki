---
title: DRA Driver for NVIDIA GPUs 架构与设计思路分析
tags: [architecture, kubernetes, gpu, dra]
date: 2026-06-12
sources: [dra-driver-nvidia-gpu-architecture-analysis.md]
related: ["[[kubernetes]]", "[[dra]]", "[[cdi]]", "[[gpu-sharing]]", "[[k8s-gpu-device-stack]]"]
---

# DRA Driver for NVIDIA GPUs 架构与设计思路分析

> 原文：`raw/dra-driver-nvidia-gpu-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu · 分析版本 HEAD `749a743`（2026-06-11）

## 一句话定位

NVIDIA GPU 的 Kubernetes Dynamic Resource Allocation driver，围绕 ResourceClaim/ResourceSlice、NodePrepareResources、ComputeDomain/Multi-Node NVLink 和动态 MIG/VFIO 配置展开。它代表 K8s 新一代设备分配模型，而不是传统 device plugin API 的增量补丁。 这页和 [[kubernetes]] [[dra]] [[cdi]] [[gpu-sharing]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────────── Kubernetes DRA API ────────────────┐
│ ResourceClaim / ResourceSlice / ClaimParameters     │
└───────────────┬───────────────────────┬─────────────┘
                │ validate              │ scheduler assigns claim
                v                       v
┌────────────────────────┐   ┌────────────────────────┐
│ validating webhook      │   │ gpu-kubelet-plugin      │
│ strict config decoder   │   │ NodePrepare/Unprepare   │
└────────────────────────┘   └──────────────┬─────────┘
                                             │ checkpoint + resource slices
                                             v
┌────────────────────────┐   ┌────────────────────────┐
│ DeviceState             │<─>│ NVML/MIG/VFIO/CDI      │
│ prepared full/mig/vfio  │   │ concrete device config │
└────────────────────────┘   └────────────────────────┘
                │
                │ ComputeDomain path
                v
┌────────────────────────┐   ┌────────────────────────┐
│ compute-domain-controller│→ │ daemon / IMEX / clique │
└────────────────────────┘   └────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| DRA kubelet plugins | 实现 kubelet DRA plugin，发布 ResourceSlice，执行 Prepare/Unprepare 和 checkpoint 清理。 |
| GPU state/config | 抽象 full GPU、MIG、VFIO、sharing、checkpoint 与资源 slice。 |
| ComputeDomain 控制面 | 管理 ComputeDomain/Clique 生命周期，动态渲染 daemonset 与 IMEX primitives。 |
| API 与 webhook | 定义 GpuConfig/MigDeviceConfig/ComputeDomain 等配置，并验证 ResourceClaim 参数。 |
| 部署与站点 | Helm/demo/docs 展示 K8s 1.32+ DRA 使用方式。 |

## 关键数据流

```
Workload consumes ResourceClaim
  │
  ├─ webhook validates strict nvidia.com resource config payload
  │
  ├─ DRA scheduler selects ResourceSlice/device allocation
  │
  ├─ kubelet calls NodePrepareResources on gpu-kubelet-plugin
  │
  ├─ driver locks prepare/unprepare, creates MIG/VFIO/CDI/checkpoint state
  │
  └─ NodeUnprepare cleans checkpoint and dynamic device incarnation
```

## 设计决策与哲学

- **接受 DRA 的声明式 claim 模型**：资源配置进入 ResourceClaim，而不是 Pod annotation；这把厂商调度逻辑接到 Kubernetes 1.32+ DRA 语义上。
- **checkpoint 是动态设备生命周期的事实来源**：`NewDriver` 在 DynamicMIG 下会清理未知 MIG devices，避免重启后静态/动态状态混乱。
- **GPU 和 ComputeDomain 分成两个插件/控制面**：ComputeDomain 面向 Multi-Node NVLink/IMEX，GPU 面向本机 device allocation，生命周期和风险边界不同。

## 与同类项目的架构差异

| 维度 | DRA Driver for NVIDIA GPUs | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | K8s DRA NVIDIA driver | k8s-device-plugin: beta device plugin API | HAMi: scheduler extender vGPU sharing |
| 资源 API | ResourceClaim/ResourceSlice | extended resource + kubelet plugin | Pod annotation + extender |
| 高级能力 | dynamic MIG/VFIO/ComputeDomain | MIG/MPS/time-slicing/CDI | memory/core sharing + heterogeneous vendors |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[kubernetes]]
- [[dra]]
- [[cdi]]
- [[gpu-sharing]]
- [[k8s-gpu-device-stack]]
