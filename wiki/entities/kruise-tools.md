---
title: Kruise Tools
tags: [entity, kubernetes, openkruise, tooling]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[openkruise-kruise]], [[kubernetes-workload-automation]], [[k8s-core-controller-map]]
---

# Kruise Tools

Kruise Tools 是 OpenKruise 生态的 libraries/tools 项目。根据 [[src-openkruise-projects-current-state]]，它属于 OpenKruise P1，更适合作为 [[openkruise-kruise]] 摄入时的工具链支撑，而不是独立架构主线。

## 架构边界

它不是 OpenKruise 主控制面，也不是用户必须优先学习的入口。它的价值主要在开发、运维、库复用或辅助工具上。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 已经在研究 OpenKruise 主仓实现 | 可以看，作为工具链和复用库补充。 |
| 想快速理解 OpenKruise workload 模型 | 先看 [[openkruise-kruise]]。 |
| 想研究 OpenKruise Agent sandbox | 看 [[openkruise-agents]]。 |

## 选型提示

把 Kruise Tools 放在支撑层，不要和 Kruise、Rollouts、Kruise Game 这类主 workload/control-plane 项目同权重比较。
