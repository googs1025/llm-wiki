---
title: CRI Tools
tags: [entity, kubernetes, cri, runtime]
date: 2026-06-14
sources: [cri-tools-architecture-analysis.md]
related: ["[[cri-tools]]", "[[kubernetes]]", "[[cloud-native-security]]"]
---

# CRI Tools

CRI Tools 提供 crictl 和 critest，用于操作与验证 kubelet Container Runtime Interface。 详见 [[src-cri-tools-architecture]]。

## 架构边界

kubectl 面向 Kubernetes API；crictl 直接面向 CRI runtime，是节点级诊断工具。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `计算 / Runtime` 能力 | 适合，CRI Tools 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[cloud-native-security]] 组合。 |

## 核心组件

- crictl: inspect/run/exec/logs/images/pods
- critest: CRI conformance/validation
- Runtime endpoint config
- Kubelet/runtime debugging workflow

## 选型提示

把 CRI Tools 放在 `计算 / Runtime` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
