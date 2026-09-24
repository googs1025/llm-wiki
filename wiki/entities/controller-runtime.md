---
title: controller-runtime
tags: [entity, kubernetes, controller, operator]
date: 2026-09-22
sources: [controller-runtime-architecture-analysis.md]
related: ["[[controller-runtime]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]", "[[k8s-core-controller-map]]", "[[kubebuilder]]", "[[controller-tools]]"]
---

# controller-runtime

controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。 详见 [[src-controller-runtime-architecture]]。

证据说明：本次官方默认分支快照为 [`6ab2188a1fb1`](https://github.com/kubernetes-sigs/controller-runtime/commit/6ab2188a1fb14a8c4837b418bc0a20049682cde4)，该 commit 不代表 release。[[src-controller-runtime-architecture]] 保留 2026-06-14 的 raw-backed Source 快照；当前跨项目证据与职责图见 [[k8s-core-controller-map]]。

## 在 M5-A Controller 地图中的位置

controller-runtime 在 client-go 基础上组合 Manager、Cache、Client、Controller/Reconciler 与 Webhook，并提供 envtest 测试支持，承担运行时框架职责。[[kubebuilder]] 负责作者工作流与项目脚手架，[[controller-tools]] 负责 CRD 等资产生成；controller-runtime 本身不承担这两类生成工作。三者的组合关系与控制循环见 [[k8s-core-controller-map]]。

## 架构边界

client-go 是底层机制；controller-runtime 是现代 operator 工程默认抽象；kubebuilder 在其上做项目脚手架。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Operator SDK` 能力 | 适合，controller-runtime 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] 组合。 |

## 核心组件

- Manager: lifecycle、leader election、scheme、metrics
- Cache/Client: informer cache + API writer
- Controller/Reconciler: workqueue and reconcile loop
- Webhook/envtest: admission and test harness

## 选型提示

把 controller-runtime 放在 `Operator SDK` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
