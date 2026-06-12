---
title: HAMi 架构与设计思路分析
tags: [architecture, kubernetes, gpu, scheduler]
date: 2026-06-12
sources: [hami-architecture-analysis.md]
related: ["[[kubernetes]]", "[[dra]]", "[[cdi]]", "[[gpu-sharing]]", "[[k8s-gpu-device-stack]]"]
---

# HAMi 架构与设计思路分析

> 原文：`raw/hami-architecture-analysis.md` · 仓库：https://github.com/Project-HAMi/HAMi · 分析版本 HEAD `5dca58e`（2026-06-11）

## 一句话定位

Kubernetes 异构 GPU sharing / vGPU 项目，通过 mutating webhook、scheduler extender、device plugin 和设备厂商后端，把 GPU memory/core/count 等细粒度配额写入 Pod 注解并在 Allocate 阶段兑现。它更像“共享调度与隔离层”，不是 NVIDIA 官方基础 device plugin 的简单替代。 这页和 [[kubernetes]] [[dra]] [[cdi]] [[gpu-sharing]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────────────── Kubernetes API ───────────────────┐
│ Pod with nvidia.com/gpu/gpumem/gpucores requests        │
└──────────────┬─────────────────────────────────────────┘
               │ admission
               v
┌──────────────────────────┐
│ HAMi mutating webhook     │
│ defaults, schedulerName,  │
│ quota/resource validation │
└──────────────┬───────────┘
               │ scheduler extender callbacks
               v
┌──────────────────────────┐      ┌──────────────────────┐
│ HAMi Scheduler            │<────>│ node/pod/quota cache │
│ filter, score, bind       │      │ annotations + locks  │
└──────────────┬───────────┘      └──────────────────────┘
               │ assigned device annotations
               v
┌──────────────────────────┐
│ HAMi device plugin        │
│ Allocate, env/CDI/hooks   │
└──────────────┬───────────┘
               v
┌──────────────────────────┐
│ Container runtime + GPU    │
│ memory/core isolation      │
└──────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| Webhook | 拦截 Pod admission，注入 schedulerName、默认 GPU memory/core/count、quota 检查。 |
| Scheduler extender | 维护 node/pod/quota cache，提供 /filter /bind /score 路由和 binpack/spread 策略。 |
| 设备抽象 | 多厂商设备注册、资源名、quota、annotation 编解码和打分逻辑。 |
| Device plugin | 对接 kubelet device plugin API，读取 node config，注册虚拟化资源，生成 env/CDI/挂载。 |
| Monitor/metrics | 反馈容器内 GPU 使用、Prometheus 指标和调度可观测性。 |

## 关键数据流

```
Pod requests partial GPU resources
  │
  ├─ webhook validates non-privileged pod and mutates resource defaults
  │
  ├─ scheduler extender filters nodes by device/quota/annotation cache
  │
  ├─ score policy chooses node/GPU and writes allocation annotations
  │
  ├─ device plugin Allocate reads pending pod and node config
  │
  └─ runtime receives visible device/env/CDI/hook configuration
```

## 设计决策与哲学

- **使用 scheduler extender 而不是只靠 device plugin**：GPU memory/core 共享需要调度时全局决策，单纯 kubelet Allocate 已经太晚。
- **annotation 是调度到分配的契约**：Scheduler 选择设备后通过 Pod/Node annotation 传递给 device plugin，降低对 kube-scheduler 内部扩展的侵入。
- **多厂商后端共享同一 device abstraction**：`pkg/device` 提供 NVIDIA/AMD/Ascend/Cambricon 等扩展点，HAMi 定位异构设备共享而非单厂商工具。

## 与同类项目的架构差异

| 维度 | HAMi | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | vGPU/GPU sharing 调度与隔离 | k8s-device-plugin: 官方 GPU 暴露 | GPU Operator: 软件栈生命周期管理 |
| 调度参与 | 强，webhook + extender + bind | 弱，主要 kubelet plugin | 间接，部署组件 |
| 资源粒度 | memory/core/count/厂商自定义 | GPU/MIG/MPS/time-slicing | driver/runtime/plugin/DCGM 组件 |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[kubernetes]]
- [[dra]]
- [[cdi]]
- [[gpu-sharing]]
- [[k8s-gpu-device-stack]]
