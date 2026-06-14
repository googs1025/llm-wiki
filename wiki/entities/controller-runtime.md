---
title: controller-runtime
tags: [entity, kubernetes, controller, operator]
date: 2026-06-14
sources: [controller-runtime-architecture-analysis.md]
related: ["[[controller-runtime]]", "[[kubernetes]]", "[[model-serving-operator]]", "[[declarative-agent-management]]"]
---

# controller-runtime

controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。 详见 [[src-controller-runtime-architecture]]。

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
