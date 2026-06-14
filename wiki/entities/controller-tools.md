---
title: controller-tools
tags: [entity, kubernetes, crd, codegen]
date: 2026-06-14
sources: [controller-tools-architecture-analysis.md]
related: ["[[controller-tools]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]"]
---

# controller-tools

controller-tools 提供 controller-gen，用 Go marker 生成 CRD、RBAC、webhook、deepcopy 等 Kubernetes API 工程资产。 详见 [[src-controller-tools-architecture]]。

## 架构边界

kubebuilder 是脚手架；controller-tools 是实际生成 CRD/RBAC 等产物的工具链。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `API 生成工具` 能力 | 适合，controller-tools 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] 组合。 |

## 核心组件

- Markers parser: 读取 Go type/comment markers
- CRD generator: OpenAPI schema and validation
- RBAC/webhook generators
- object/deepcopy generation

## 选型提示

把 controller-tools 放在 `API 生成工具` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
