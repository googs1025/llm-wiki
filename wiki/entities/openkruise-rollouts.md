---
title: OpenKruise Rollouts
tags: [entity, kubernetes, openkruise, release-governance, rollout]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[openkruise-kruise]], [[kubernetes-workload-automation]], [[gitops]], [[gateway-api]]
---

# OpenKruise Rollouts

OpenKruise Rollouts 是 OpenKruise 的 enhanced rollout 控制面，面向渐进式发布、分批发布、流量治理和应用自动化。根据 [[src-openkruise-projects-current-state]]，它是 OpenKruise P0 候选，适合和 Argo Rollouts、原生 Deployment rollout、Gateway/Ingress 流量切分一起对比；在概念层归入 [[kubernetes-workload-automation]] 的 release governance 子问题。

## 架构边界

它关注“新版本怎样逐步上线并受控回滚”，不是完整 GitOps 系统。GitOps 工具负责期望状态来源；Rollouts 控制实际发布节奏、批次、暂停、推进和流量策略。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 需要 Kubernetes 渐进式发布 | 适合，放入 [[kubernetes-workload-automation]] 的 release governance 路线评估。 |
| 想和 Gateway / Ingress 流量切分结合 | 适合，需要继续核验当前支持矩阵。 |
| 想管理 workload 类型本身 | 先看 [[openkruise-kruise]]。 |
| 想管理 Agent sandbox | 看 [[openkruise-agents]]。 |

## 选型提示

评估 Rollouts 时不要只看 rollout 策略名，还要看它如何和 workload controller、traffic provider、metrics analysis、GitOps reconcile 和回滚状态机组合。
