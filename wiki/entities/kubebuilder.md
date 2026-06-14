---
title: Kubebuilder
tags: [entity, kubernetes, operator, crd]
date: 2026-06-14
sources: [kubebuilder-architecture-analysis.md]
related: ["[[kubebuilder]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]"]
---

# Kubebuilder

Kubebuilder 是构建 Kubernetes APIs using CRDs 的 SDK，把 API type、marker、controller-runtime manager、webhook、RBAC 和 manifests 生成流程标准化。 详见 [[src-kubebuilder-architecture]]。

## 架构边界

kubebuilder 解决项目结构和生成路径；controller-runtime 解决运行时 controller 抽象。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `CRD / controller 脚手架` 能力 | 适合，Kubebuilder 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] 组合。 |

## 核心组件

- CLI scaffolding: init/create api/webhook
- API markers: kubebuilder validation/printcolumn/rbac
- Project layout: api/ controllers/ config/
- Generation: CRD/RBAC/webhook/deepcopy manifests

## 选型提示

把 Kubebuilder 放在 `CRD / controller 脚手架` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
