---
title: KWOK
tags: [entity, kubernetes, simulator, testing]
date: 2026-06-14
sources: [kwok-architecture-analysis.md]
related: ["[[kwok]]", "[[kubernetes]]", "[[model-serving-operator]]"]
---

# KWOK

KWOK 是 Kubernetes WithOut Kubelet，用 fake nodes/pods 模拟大规模集群，适合调度、控制器和 scalability 测试。 详见 [[src-kwok-architecture]]。

## 架构边界

kind 提供真实小集群；KWOK 提供便宜的大规模对象模拟。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `大规模集群模拟` 能力 | 适合，KWOK 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[kubernetes]], [[model-serving-operator]] 组合。 |

## 核心组件

- kwok controller: fake kubelet behavior
- kwokctl: cluster lifecycle
- Stage/Configuration: pod/node condition transitions
- Integrations: kind/kube-apiserver tests

## 选型提示

把 KWOK 放在 `大规模集群模拟` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
