---
title: NVIDIA k8s-device-plugin 架构与设计思路分析
tags: [architecture, kubernetes, gpu, device-plugin]
date: 2026-06-12
sources: [k8s-device-plugin-architecture-analysis.md]
related: ["[[kubernetes]]", "[[cdi]]", "[[gpu-sharing]]", "[[k8s-gpu-device-stack]]", "[[dra]]"]
---

# NVIDIA k8s-device-plugin 架构与设计思路分析

> 原文：`raw/k8s-device-plugin-architecture-analysis.md` · 仓库：https://github.com/NVIDIA/k8s-device-plugin · 分析版本 HEAD `8688949`（2026-06-10）

## 一句话定位

NVIDIA 官方 Kubernetes device plugin，把节点上的 GPU/MIG/vGPU 发现为 kubelet extended resources，并在 Allocate 阶段通过 env、volume-mounts 或 CDI annotations 把设备传给容器。它是 GPU 暴露的基础层，上层 GPU Operator/HAMi/DRA 都会和它形成互补或替代关系。 这页和 [[kubernetes]] [[cdi]] [[gpu-sharing]] [[k8s-gpu-device-stack]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌────────────────── NVIDIA GPU Node ──────────────────┐
│ NVML / CUDA / Tegra / VFIO / MIG / IMEX / MPS         │
└──────────────┬───────────────────────────────────────┘
               │ discovery strategy
               v
┌────────────────────────────┐
│ resource manager            │
│ devices, health, allocation │
└──────────────┬─────────────┘
               │ per resource
               v
┌────────────────────────────┐      ┌───────────────────┐
│ device plugin gRPC server   │<────>│ kubelet            │
│ Register/List/Allocate      │      │ DevicePlugin API   │
└──────────────┬─────────────┘      └───────────────────┘
               │ device list strategy
               v
┌───────────────────────────────────────────────────────┐
│ container envvar / volume-mounts / CDI annotations     │
└───────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| CLI/config | 解析 MIG strategy、device-list strategy、CDI/MPS/IMEX/driver root 等配置。 |
| Plugin manager | 解析 discovery strategy，创建 CDI handler、resource manager 和 per-resource plugin。 |
| Resource manager | 基于 NVML/CUDA/Tegra/VFIO 发现设备，处理 MIG/resource mapping、preferred allocation、health。 |
| Device plugin server | 实现 kubelet device plugin gRPC：Serve/Register/ListAndWatch/Allocate/PreStart。 |
| Feature discovery/MPS | 提供 GPU label、MPS daemon 和 node feature discovery 集成。 |

## 关键数据流

```
Node starts nvidia-device-plugin DaemonSet
  │
  ├─ main parses config/env flags and selected discovery strategy
  │
  ├─ plugin-manager creates CDI spec and resource managers
  │
  ├─ per-resource plugin registers Unix socket with kubelet
  │
  ├─ ListAndWatch reports healthy GPU/MIG resources
  │
  └─ Allocate validates request and returns env/mount/CDI device edits
```

## 设计决策与哲学

- **保持 kubelet device plugin API 的基础语义**：项目核心是发现、健康检查和 Allocate，不承担全局调度或多租户策略。
- **多种 device list strategy 兼容不同 runtime**：envvar、volume-mounts、CDI annotations 并存，让老 runtime 和新 CDI 工作流都能接入。
- **resource manager 隔离硬件发现差异**：`internal/resource/factory.go` 按 NVML/Tegra/VFIO 选择 manager，plugin server 不直接关心硬件细节。

## 与同类项目的架构差异

| 维度 | NVIDIA k8s-device-plugin | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | 官方 GPU device plugin 基础层 | GPU Operator: 部署管理它 | HAMi: 共享调度/虚拟化扩展 |
| API | Kubelet DevicePlugin v1beta1 | Operator CRD | scheduler extender + annotations |
| 粒度 | GPU/MIG/MPS/time-slicing/CDI | 软件组件栈 | memory/core/count 共享 |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[kubernetes]]
- [[cdi]]
- [[gpu-sharing]]
- [[k8s-gpu-device-stack]]
- [[dra]]
