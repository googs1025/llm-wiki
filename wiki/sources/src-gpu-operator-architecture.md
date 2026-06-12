---
title: NVIDIA GPU Operator 架构与设计思路分析
tags: [architecture, kubernetes, gpu, operator]
date: 2026-06-12
sources: [gpu-operator-architecture-analysis.md]
related: ["[[kubernetes]]", "[[k8s-operator]]", "[[cdi]]", "[[gpu-sharing]]", "[[k8s-gpu-device-stack]]"]
---

# NVIDIA GPU Operator 架构与设计思路分析

> 原文：`raw/gpu-operator-architecture-analysis.md` · 仓库：https://github.com/NVIDIA/gpu-operator · 分析版本 HEAD `0219120`（2026-06-11）

## 一句话定位

NVIDIA GPU 软件栈的 Kubernetes Operator，用 ClusterPolicy/NVIDIADriver CRD 驱动 driver、container-toolkit、device-plugin、DCGM、MIG manager、sandbox/vGPU 等组件的声明式部署和升级。它管的是 GPU node 软件生命周期，而不是单次 Pod GPU 分配算法。 这页和 [[kubernetes]] [[k8s-operator]] [[cdi]] [[gpu-sharing]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────────────── ClusterPolicy CR ───────────────────┐
│ desired NVIDIA GPU software stack on Kubernetes nodes     │
└───────────────┬──────────────────────────────────────────┘
                │ reconcile
                v
┌──────────────────────────────┐
│ ClusterPolicyReconciler       │
│ singleton, metrics, conditions│
└───────────────┬──────────────┘
                │ step through states
                v
┌──────────────────────────────┐      ┌──────────────────────┐
│ State/resource managers       │<────>│ cluster info / labels │
│ render assets/state-*         │      │ OpenShift/NFD/GPU     │
└───────────────┬──────────────┘      └──────────────────────┘
                │ create/update operands
                v
┌───────────────────────────────────────────────────────────┐
│ driver, container-toolkit, device-plugin, dcgm, gfd, mig, │
│ node-status-exporter, sandbox/vgpu components             │
└───────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| Controller manager | 启动 controller-runtime manager、scheme、webhook、leader election、ClusterPolicy 和 upgrade controller。 |
| ClusterPolicy controller | 单例 ClusterPolicy reconcile，按状态机逐步部署 operands 并更新状态/metrics。 |
| State/resources renderer | 按 CR spec 和 cluster info 渲染 DaemonSet/Service/ConfigMap/CRD 等对象并 create/update。 |
| CRD/API | 定义 ClusterPolicy、NVIDIADriver 等声明式 spec/status。 |
| 升级与验证 | 管理 driver upgrade、operator validator、组件就绪检查。 |

## 关键数据流

```
Admin applies ClusterPolicy
  │
  ├─ controller-runtime manager enqueues ClusterPolicy reconcile
  │
  ├─ controller initializes singleton, cluster info, node labels
  │
  ├─ state machine renders each operand manifest from assets/state-*
  │
  ├─ create/update objects and check DaemonSet/Deployment readiness
  │
  └─ conditions/metrics expose Ready/NotReady and driver upgrade state
```

## 设计决策与哲学

- **Operator 管组件生命周期，不直接做 GPU allocation**：它部署 device plugin、driver、runtime、DCGM 等 operands，真正 Allocate 仍由 device plugin/kubelet 路径完成。
- **状态机比单次 reconcile 更贴合 GPU 软件栈**：`ClusterPolicyController.step()` 逐状态推进，便于表达 driver/toolkit/plugin/monitoring 的依赖顺序。
- **渲染资产与 cluster info 解耦**：`internal/state/driver.go` 根据 OpenShift、precompiled、kernel、proxy 等信息生成实际 DaemonSet。

## 与同类项目的架构差异

| 维度 | NVIDIA GPU Operator | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | GPU 软件栈 Operator | k8s-device-plugin: kubelet plugin | DRA driver: 新 API 分配 |
| 核心对象 | ClusterPolicy/NVIDIADriver | DaemonSet + config | ResourceClaim/ResourceSlice |
| 主要用户 | 集群管理员 | 平台/节点管理员 | DRA workload/platform |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[kubernetes]]
- [[k8s-operator]]
- [[cdi]]
- [[gpu-sharing]]
- [[k8s-gpu-device-stack]]
