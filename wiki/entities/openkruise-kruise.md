---
title: OpenKruise Kruise
tags: [entity, kubernetes, openkruise, workload, operator]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[kubernetes]], [[kubernetes-workload-automation]], [[openkruise-agents]], [[k8s-core-controller-map]], [[model-serving-operator]]
---

# OpenKruise Kruise

OpenKruise Kruise 是 OpenKruise 主仓，定位是 Kubernetes workload enhancement。根据 [[src-openkruise-projects-current-state]]，它是 OpenKruise 生态 P0 项目，用 CloneSet、Advanced StatefulSet、Advanced DaemonSet、SidecarSet、UnitedDeployment、WorkloadSpread、ImagePullJob 等控制器补足原生 Deployment/StatefulSet 在大规模应用管理上的细粒度自动化能力。

## 架构边界

它不是新的调度器，也不是 GitOps 工具。它位于 Kubernetes workload controller 层，用 CRD/controller 扩展 workload 生命周期、分批发布、sidecar 注入、镜像预热和跨域分布。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 想理解 OpenKruise 生态主线 | 先看 [[openkruise-kruise]]，再看 [[openkruise-rollouts]] / [[kruise-game]] / [[openkruise-agents]]。 |
| 原生 Deployment / StatefulSet 控制粒度不够 | 适合对比 CloneSet、Advanced StatefulSet、WorkloadSpread。 |
| 想研究 AI/LLM serving workload 预热和滚动 | 可作为 [[model-serving-operator]] 的 workload automation 对照。 |
| 只需要 Agent sandbox 生命周期 | 看 [[openkruise-agents]]。 |

## 选型提示

把 Kruise 放在 [[kubernetes-workload-automation]] 里理解：它扩展的是 workload 控制器语义，而不是替代 kube-scheduler、Kueue、Karpenter 或 Gateway API。
