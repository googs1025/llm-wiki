---
title: controller-tools
tags: [entity, kubernetes, crd, codegen]
date: 2026-09-22
sources: [controller-tools-architecture-analysis.md]
related: ["[[controller-tools]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]", "[[k8s-core-controller-map]]", "[[controller-runtime]]", "[[kubebuilder]]"]
---

# controller-tools

controller-tools 提供 controller-gen，用 Go marker 生成 CRD、RBAC、webhook、deepcopy 等 Kubernetes API 工程资产。 详见 [[src-controller-tools-architecture]]。

证据说明：本次官方默认分支快照为 [`030a93937cbb`](https://github.com/kubernetes-sigs/controller-tools/commit/030a93937cbbd72cc02cc2fe943f1df6e4b1f115)，该 commit 不代表 release。[[src-controller-tools-architecture]] 保留 2026-06-14 的 raw-backed Source 快照；当前跨项目证据与职责图见 [[k8s-core-controller-map]]。

## 在 M5-A Controller 地图中的位置

controller-tools 的 controller-gen 解析 Go markers/types，生成 CRD、RBAC、webhook manifests、deepcopy（object generator）与 applyconfiguration 等资产。[[kubebuilder]] 把它接入作者工作流；[[controller-runtime]] 负责运行时控制器框架，controller-tools 不运行 controller。完整生成链与运行时边界见 [[k8s-core-controller-map]]。

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
