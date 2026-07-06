---
title: Kubernetes Resource Orchestration
tags: [concept, kubernetes, scheduling, autoscaling, node, platform-engineering]
date: 2026-07-06
sources: [src-kubernetes-resource-orchestration-keps.md]
related: [[kubernetes]], [[kubernetes-scheduling-design]], [[kubernetes-autoscaling-design]], [[kubernetes-node-design]], [[kubernetes-workload-automation]], [[kubernetes-dra]], [[kueue]], [[karpenter]], [[metrics-server]], [[prometheus-adapter]]
---

# Kubernetes Resource Orchestration

Kubernetes resource orchestration 是一个新的业务整理域，用来分析 Kubernetes 如何把 workload intent 转成资源放置、容量变化和节点执行结果。它覆盖三条主线：[[kubernetes-scheduling-design]]、[[kubernetes-autoscaling-design]]、[[kubernetes-node-design]]。

## 边界

这个概念不同于 [[kubernetes-workload-automation]]。后者关注更高层 workload API、operator 和业务生命周期；resource orchestration 关注 Kubernetes 核心控制面的资源决策链路：scheduler、HPA/metrics、kubelet/runtime/device。

```text
Workload automation
  expresses business intent
        |
        v
Resource orchestration
  decides placement, capacity, local execution
        |
        v
Node/runtime/device state
  feeds status, metrics, events back to control loops
```

## 三个子域

| 子域 | 关键问题 | 代表对象 / 组件 |
|---|---|---|
| [[kubernetes-scheduling-design]] | Pod 或 workload 何时进入队列、过滤哪些节点、如何打分、何时抢占、是否等待整组 Pod。 | kube-scheduler、framework plugin、profile、PodGroup、ResourceClaim。 |
| [[kubernetes-autoscaling-design]] | 什么信号触发扩缩、扩多少、是否容忍抖动、指标失败时如何处理。 | HPA、scale subresource、metrics APIs、metrics-server、custom/external metrics adapter。 |
| [[kubernetes-node-design]] | 节点如何落实资源分配、runtime 生命周期、设备注入、安全隔离和本地健康反馈。 | kubelet、CRI、CPU Manager、Memory Manager、Topology Manager、device plugin、DRA、cgroup。 |

## 为什么要单独成域

Kubernetes 新设计越来越多地跨越 SIG 边界。例如 [[kubernetes-dra]] 同时影响 scheduler 的可行性判断、node 的设备准备和 autoscaler 的容量推理；in-place Pod resize 同时影响 kubelet 执行、scheduler 抢占和 autoscaling 延迟；PodGroup/gang scheduling 把单 Pod 最优问题提升为 workload 整体容量问题。

如果只按项目整理，会把这些交叉点拆散。按 resource orchestration 业务域整理，可以把 KEP、实现项目和平台选型放到同一个坐标系里。

## 业务地图

| 层次 | 当前 wiki 入口 | 说明 |
|---|---|---|
| 核心设计源 | [[src-kubernetes-resource-orchestration-keps]] | 三个 SIG 的 KEP 聚合笔记。 |
| 调度实现/扩展 | [[scheduler-plugins]], [[kube-scheduler-simulator]], [[descheduler]], [[kueue]] | 从 scheduler plugin、模拟、调度后优化到 batch admission。 |
| 容量与指标 | [[karpenter]], [[metrics-server]], [[prometheus-adapter]] | 节点容量供给、资源指标、业务指标。 |
| 节点/设备 | [[node-feature-discovery]], [[device-plugin]], [[cdi]], [[kubernetes-dra]], [[gpu-sharing]] | 从硬件发现到设备注入和下一代资源声明。 |
| AI/Batch workload | [[jobset]], [[lws]], [[llm-d]], [[model-serving-operator]] | AI/HPC/serving 对调度、伸缩、拓扑、设备的综合需求。 |

## 阅读顺序

1. 先读 [[kubernetes-scheduling-design]]，理解 scheduler framework、队列、抢占和 workload 级调度。
2. 再读 [[kubernetes-autoscaling-design]]，理解 HPA API 如何从通用 CPU utilization 走向 workload-specific 行为。
3. 最后读 [[kubernetes-node-design]]，把资源决策落到 kubelet、CRI、cgroup、device 和 runtime 状态。
4. 对设备和 GPU 场景，补读 [[kubernetes-dra]]、[[device-plugin]]、[[cdi]]、[[gpu-sharing]]。
5. 对 AI/Batch 平台，和 [[kueue]]、[[karpenter]]、[[jobset]]、[[lws]]、[[model-serving-operator]] 对照。

## 后续扩展

下一轮适合纳入 `prod-readiness/sig-scheduling`、`prod-readiness/sig-autoscaling`、`prod-readiness/sig-node`，为每个主题增加 feature gate、graduation、metrics、failure mode、rollback 和 scalability 维度。
