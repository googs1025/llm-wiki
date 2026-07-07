---
title: Kubernetes Scheduler Core Design
tags: [analysis, kubernetes, kep, sig-scheduling, scheduler, queue, placement, preemption, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/624-scheduling-framework/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/785-scheduler-component-config-api/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/1451-multi-scheduling-profiles/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4247-queueinghint/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6132-prequeueing-hints/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5598-opportunistic-batching/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/895-pod-topology-spread/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4832-async-preemption/README.md]
related: [[kubernetes]], [[kubernetes-keps-feature-coverage]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-keps-design-tracking]], [[kubernetes-workload-gang-scheduling-design]], [[kubernetes-dra-design-deep-dive]], [[scheduler-plugins]], [[descheduler]], [[kube-scheduler-simulator]]
---

# Kubernetes Scheduler Core Design

这页合并讲 `sig-scheduling` 的 scheduler core feature：framework、component config、profiles、queue/requeue、topology placement、async preemption 和调度性能。Workload/Gang 和 DRA 已经有单独详解页，这页负责解释它们依赖的 scheduler 底座。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]。

## 一句话定位

Scheduler core KEP 的共同目标是把 kube-scheduler 从一个内置策略集合，演进为可配置、可扩展、可解释、可高吞吐的调度框架。

## Scheduler Framework

`624-scheduling-framework` 是最关键的基础 KEP。它把一次 Pod 调度拆成多个 extension point：

```text
QueueSort
  -> PreFilter
  -> Filter
  -> PostFilter
  -> PreScore
  -> Score
  -> Reserve
  -> Permit
  -> PreBind
  -> Bind
  -> PostBind
```

设计价值：

- 新策略不再必须 fork scheduler 或靠 HTTP extender 绕路。
- plugin 可以在 filter、score、reserve、permit、bind 等不同阶段表达不同语义。
- DRA、gang scheduling、queueing hints、in-place resize preemption 都能复用这套扩展点。

`1819-scheduler-extender` 仍然是历史对照。HTTP extender 能扩展 Filter/Prioritize/Bind 等阶段，但有 cache 同步、性能、错误处理和扩展点表达不足的问题。framework 的方向是把关键扩展内聚到 scheduler 进程内，以 typed plugin API 表达。

## ComponentConfig 和 Profiles

`785-scheduler-component-config-api` 把 scheduler 配置版本化，`1451-multi-scheduling-profiles` 允许一个 scheduler 实例提供多个 profile。

这两个 KEP 解决的是运营问题：

- 不同 workload 可能需要不同 plugin 组合。
- 多 scheduler binary 会复制 cache、部署和 HA 成本。
- profile 让用户通过 `schedulerName` 选择策略，而不是部署多套控制面。

多 profile 的边界是：它共享 scheduler cache 和主进程，适合策略差异，不适合完全隔离不同调度器的故障域或权限域。

## Queue / Requeue 设计

调度性能不只取决于 Filter/Score 快不快，也取决于“什么时候值得重新尝试一个 pending Pod”。

| Feature | KEP | 设计作用 |
|---|---|---|
| Pod scheduling readiness | `3521` | 用 scheduling gates 阻止条件未满足的 Pod 进入正常调度。 |
| QueueingHint | `4247` | plugin 判断某个事件是否可能让某个 Pod 可调度。 |
| PreQueueing hints | `6132` | 在 Pod 进入 activeQ 前更早过滤无效唤醒。 |
| Pop backoffQ when activeQ empty | `5142` | activeQ 空时提前处理 backoffQ，提高吞吐。 |
| Reflect PreEnqueue rejection in Pod status | `5501` | 把被 PreEnqueue 拒绝的原因暴露给用户。 |
| Opportunistic batching | `5598` | 对高吞吐场景批量处理，减少重复计算。 |

QueueingHint 是 DRA、gang、resize 这类等待型场景的关键。没有 hint，任何 ResourceClaim、PodGroup、Node、Pod 事件都可能唤醒大量无关 pending Pod，造成调度风暴。

## Placement / Topology

普通 Pod placement 仍然是 scheduler core 的重要 feature：

- `895-pod-topology-spread` 将副本分散作为一等调度约束。
- `1258-default-pod-topology-spread` 给未显式配置 spread 的 workload 提供默认保护。
- `3022-min-domains-in-pod-topology-spread` 避免拓扑域数量不足时误判。
- `3094-pod-topology-spread-considering-taints` 让 skew 计算排除实际不可用节点。
- `3633-matchlabelkeys-to-podaffinity` 让 rollout hash 等动态标签参与 affinity/anti-affinity。

这组设计和 [[kubernetes-workload-gang-scheduling-design]] 的区别是：Pod topology spread 仍然以单 Pod 为基本调度循环；topology-aware workload scheduling 则要对一组 Pod 一起生成 placement。

## Preemption 基础线

Preemption 从最早的 priority/preemption 发展到更异步、更可解释：

- `902-non-preempting-priorityclass` 支持“高优先级排序但不抢占”。
- `4832-async-preemption` 避免 scheduler 在调度周期里同步等待 victim 删除。
- `5278-nominated-node-name-for-expectation` 改善 nominated node 期望表达。
- `3280-guarantee-pdb-when-preemption-happens` 关注抢占和 PDB 的冲突。

这组 feature 是 Workload-aware preemption 和 resize-induced preemption 的基础。后两者不是重新发明抢占，而是把现有抢占模型扩展到 PodGroup 或已绑定 Pod resize 场景。

## Data Flow

```text
cluster event
  |
  +-- queueing hint decides affected pods
  |
activeQ / backoffQ / unschedulable
  |
  +-- scheduling profile selects plugin set
  |
framework cycle
  |
  +-- filter / score / reserve / permit / prebind
  |
bind or fail
  |
  +-- events / status / requeue hints
```

理解 scheduler feature 时，应该先问它改的是哪一层：

- 改 API 表达：ComponentConfig、profile、Pod topology spread。
- 改队列行为：QueueingHint、PreQueueing、backoffQ。
- 改调度计算：Filter/Score plugin、DRA Filter、TopologySpread。
- 改失败处理：PostFilter、preemption、status/event。
- 改性能：batching、async API calls、async preemption。

## 重要边界

| 边界 | 说明 |
|---|---|
| Scheduler 不是 admission queue | 多租户队列、公平性、quota 仍更适合 [[kueue]] 这类 controller。 |
| Scheduler profile 不是强隔离 | 多 profile 共享进程和 cache。 |
| Queueing hints 不改变调度结果 | 它只减少无意义重试，不应改变最终可调度性。 |
| TopologySpread 不是 gang placement | 它仍然按 Pod 调度，只是计算 skew。 |
| Preemption 不保证 PDB 绝不被破坏 | Kubernetes 尽量减少 disruption，但不能把 PDB 当硬约束。 |

## 关键 KEP 实现状态

| KEP | 当前状态 | Alpha / Beta / GA | Feature gate | 关键实现路径 |
|---|---|---|---|---|
| `624-scheduling-framework` | `implemented / stable`，已实现/GA | v1.16 / - / v1.19 | - | kube-scheduler 内部 extension points，替代大量 extender/fork 场景。 |
| `785-scheduler-component-config-api` | `implemented / stable`，已实现/GA | - / v1.19 / v1.25 | - | versioned `KubeSchedulerConfiguration`，让调度器配置可升级。 |
| `1451-multi-scheduling-profiles` | `implementable / beta`，设计可实现，metadata 未标 implemented | v1.18 / v1.19 / v1.22 | - | 一个 scheduler 进程多个 profile，Pod 通过 `schedulerName` 选择策略。 |
| `3521-pod-scheduling-readiness` | `implemented / stable`，已实现/GA | v1.26 / v1.27 / v1.30 | `PodSchedulingReadiness` | `schedulingGates` 让 Pod 在外部条件满足前不进入普通调度。 |
| `4247-queueinghint` | `implemented / stable`，已实现/GA | v1.26 / v1.32 / v1.34 | `SchedulerQueueingHints` | plugin 按事件判断是否 requeue pending Pod，降低调度风暴。 |
| `6132-prequeueing-hints` | `implementable / beta`，仍在 beta | - / v1.37 / v1.39 | `SchedulerPreQueueingHints` | 在 activeQ 之前过滤无效唤醒，是 DRA/gang/resize 的性能补强。 |
| `5598-opportunistic-batching` | `implementable / beta`，仍在 beta | - / v1.35 / v1.38 | `OpportunisticBatching` | 对可调度机会做批量化，减少重复 snapshot/filter/score 成本。 |
| `895-pod-topology-spread` | `implemented / stable`，已实现/GA | v1.16 / v1.18 / v1.19 | `EvenPodsSpread` | scheduler filter/score 计算 topology domain skew。 |
| `4832-async-preemption` | `implementable / beta`，仍在 beta | v1.32 / v1.33 / - | `SchedulerAsyncPreemption` | 抢占 victim 删除异步化，减少主调度循环阻塞。 |

## 和其他详解页的关系

- [[kubernetes-workload-gang-scheduling-design]] 依赖 framework、queue、preemption。
- [[kubernetes-dra-design-deep-dive]] 依赖 queueing hints、Filter timeout、Reserve/PreBind。
- [[kubernetes-in-place-pod-resize-design]] 依赖 queueing hints 和 preemption failure handler。
- [[scheduler-plugins]] 是 out-of-tree 实验和生产化扩展的参考实现集合。
- [[kube-scheduler-simulator]] 适合用来观察 filter/score/preemption 的具体行为。

## 追踪重点

- QueueingHint / PreQueueing hints 是否覆盖 DRA、PodGroup、resize 等高等待场景。
- Async preemption 与 workload-aware preemption 是否收敛到统一的失败处理模型。
- Scheduling profile 的 plugin 参数是否继续保持可升级和可观测。
- TopologySpread 与 workload-level topology 的边界是否清晰。
- scheduler perf 中 extension point latency 是否被 DRA / CEL / batch scheduling 拉高。
