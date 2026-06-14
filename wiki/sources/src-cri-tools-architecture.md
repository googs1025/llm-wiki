---
title: CRI Tools 架构与设计思路分析
tags: [architecture, kubernetes, cri, runtime]
date: 2026-06-14
sources: [cri-tools-architecture-analysis.md]
related: ["[[cri-tools]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# CRI Tools 架构与设计思路分析

> 原文：`raw/cri-tools-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/cri-tools · 优先级 P0

## 一句话定位

CRI Tools 提供 crictl 和 critest，用于操作与验证 kubelet Container Runtime Interface。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ CRI Tools                  │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ crictl: in │ │ critest: CRI c │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Runtime en │ │ Kubelet/runtim │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| crictl | inspect/run/exec/logs/images/pods |
| critest | CRI conformance/validation |
| Runtime endpoint config | Runtime endpoint config |
| Kubelet/runtime debugging workflow | Kubelet/runtime debugging workflow |

## 关键数据流

```
用户指定 CRI endpoint
        │
        ▼
crictl 调用 CRI gRPC
        │
        ▼
runtime 返回 pods/containers/images 状态
        │
        ▼
critest 执行 conformance cases
        │
        ▼
定位 kubelet/runtime 边界问题
```

## 设计决策与哲学

- **补齐 `计算 / Runtime` 维度**：CRI Tools 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：kubectl 面向 Kubernetes API；crictl 直接面向 CRI runtime，是节点级诊断工具。
- **选型价值**：它应和 [[kubernetes]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[cri-tools]]
- [[kubernetes]]
- [[cloud-native-security]]
