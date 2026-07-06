---
title: Kubernetes Scheduling Design
tags: [concept, kubernetes, scheduling, scheduler, kep]
date: 2026-07-06
sources: [src-kubernetes-resource-orchestration-keps.md]
related: [[kubernetes-resource-orchestration]], [[kubernetes]], [[scheduler-plugins]], [[kube-scheduler-simulator]], [[descheduler]], [[kueue]], [[kubernetes-dra]]
---

# Kubernetes Scheduling Design

Kubernetes scheduling design 关注 kube-scheduler 如何从 Pod/workload intent 走到节点绑定：排队、过滤、打分、reserve、permit、bind、抢占、重新入队和设备资源协商。

## 设计分层

| 层次 | 代表 KEP | 设计关注点 |
|---|---|---|
| Framework | `624-scheduling-framework` | 把 scheduler 拆成 QueueSort、PreFilter、Filter、PostFilter、PreScore、Score、Reserve、Permit、PreBind、Bind、PostBind 等扩展点。 |
| Profile / config | `785-scheduler-component-config-api`, `1451-multi-scheduling-profiles`, `2891-simplified-config` | 多策略共用一个 scheduler binary，减少 fork scheduler 的成本。 |
| Queue semantics | `3521-pod-scheduling-readiness`, `4247-queueinghint`, `6132-prequeueing-hints` | 让插件和 Pod 状态决定是否入队、何时重试、哪些事件能让 Pod 重新可调度。 |
| Placement policy | `895-pod-topology-spread`, `1258-default-pod-topology-spread`, `2458-node-resource-score-strategy`, `3633-matchlabelkeys-to-podaffinity` | 拓扑、亲和、资源打分和默认 spread 策略。 |
| Preemption | `268-priority-preemption`, `902-non-preempting-priorityclass`, `4832-async-preemption`, `5710-workload-aware-preemption` | 从单 Pod 优先级抢占扩展到异步和 workload-aware 抢占。 |
| Workload scheduling | `4671-gang-scheduling`, `5832-decouple-podgroup-api`, `6012-composite-podgroup-api`, `6089-was-controller-apis` | PodGroup/gang/workload API 让一组 Pod 作为整体进入调度状态机。 |
| Device-aware scheduling | `5007-device-attach-before-pod-scheduled`, `5075-dra-consumable-capacity`, `5517-dra-node-allocatable-resources`, `6080-dra-derived-attributes` | [[kubernetes-dra]] 让设备容量、属性、拓扑和绑定条件进入调度决策。 |

## 核心判断

Scheduler 设计的主线不是“增加更多内置策略”，而是把策略插槽和状态边界标准化。这样 [[scheduler-plugins]] 可以承载 out-of-tree 策略，[[kube-scheduler-simulator]] 可以解释调度路径，[[descheduler]] 可以修正运行后漂移，[[kueue]] 可以在 scheduler 前面做队列/admission。

## 关键趋势

- **调度从单 Pod 走向 workload**：gang scheduling、PodGroup、workload-aware preemption 都说明 AI/HPC/batch 不能只用单 Pod 视角。
- **队列变成一等设计对象**：PodSchedulingReadiness、QueueingHint 和 PreQueueingHint 把“什么时候值得重试”显式化。
- **抢占要减少副作用**：non-preempting priority、async preemption 和 workload-aware preemption 都是在降低无效驱逐和容量浪费。
- **设备调度进入主路径**：DRA 相关 KEP 让 ResourceClaim、ResourceSlice、device attributes 和 topology 影响 filter/score/reserve。

## 和现有项目的关系

| 项目 | 关系 |
|---|---|
| [[scheduler-plugins]] | scheduling framework 的实验和生产扩展集合。 |
| [[kube-scheduler-simulator]] | 帮助观察 filter/score/queue/preemption 决策。 |
| [[descheduler]] | 运行后重新平衡，与初次调度形成互补。 |
| [[kueue]] | 在 scheduler 前做 workload admission、quota、cohort 和抢占。 |
| [[karpenter]] | 读取 pending Pod 约束后补节点容量，不替代 scheduler。 |
