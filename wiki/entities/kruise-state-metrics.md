---
title: Kruise State Metrics
tags: [entity, kubernetes, openkruise, observability, metrics]
date: 2026-06-16
sources: [openkruise-projects-current-state.md]
related: [[openkruise-kruise]], [[metrics-server]], [[prometheus-adapter]], [[kubernetes-workload-automation]]
---

# Kruise State Metrics

Kruise State Metrics 是 OpenKruise CRD metrics addon。根据 [[src-openkruise-projects-current-state]]，它属于 OpenKruise P1，价值在于把 CloneSet、Advanced StatefulSet、SidecarSet 等 OpenKruise workload 状态转成可观测指标。

## 架构边界

它不是资源指标源，和 [[metrics-server]] 不同；它更接近 kube-state-metrics 的模式，把 Kubernetes API 对象状态转成 Prometheus 可采集指标。和 [[prometheus-adapter]] 的关系是：前者产出状态指标，后者可以把 Prometheus 指标暴露给 custom/external metrics API。

## 什么时候看它

| 场景 | 判断 |
|---|---|
| 已经使用 OpenKruise workload | 适合，用它补 CRD 状态可观测。 |
| 想把 OpenKruise 指标接入 autoscaling | 需要和 Prometheus / [[prometheus-adapter]] 组合验证。 |
| 只需要 Pod CPU/memory 指标 | 看 [[metrics-server]]。 |

## 选型提示

OpenKruise workload 一旦进入生产，就需要配套状态指标；否则 CloneSet、Advanced StatefulSet 这类增强 workload 会比原生 Deployment 更难解释和排障。
