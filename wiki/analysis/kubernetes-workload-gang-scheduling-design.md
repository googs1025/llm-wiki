---
title: Kubernetes Workload and Gang Scheduling Design
tags: [analysis, kubernetes, kep, sig-scheduling, gang-scheduling, workload-api, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4671-gang-scheduling/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5710-workload-aware-preemption/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6012-composite-podgroup-api/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6089-was-controller-apis/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5732-topology-aware-workload-scheduling/README.md]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-workload-automation]], [[kueue]], [[scheduler-plugins]], [[jobset]], [[lws]], [[karpenter]]
---

# Kubernetes Workload and Gang Scheduling Design

这页专门讲 `sig-scheduling` 里最重要的一条设计线：从单 Pod 调度，走向 Workload / PodGroup 作为调度单位。核心 KEP 是 `4671-gang-scheduling`，后续由 `5710-workload-aware-preemption`、`6012-composite-podgroup-api`、`6089-was-controller-apis` 和 `5732-topology-aware-workload-scheduling` 继续展开。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]。

## 一句话定位

这组 KEP 的目标是让 Kubernetes 原生理解“一个 workload 由一组 Pod 构成，必须以组为单位做准入、放置、抢占和状态反馈”，而不是继续让每个 AI/HPC/batch controller 各自实现一套 gang scheduling 语义。

## 为什么重要

传统 kube-scheduler 的基本单位是 Pod。对 Web 服务这通常够用，但对分布式训练、MPI、Ray、JobSet、LeaderWorkerSet、multi-host inference 这类 workload 不够：

- 一组 Pod 需要同时启动，缺一个成员就无法训练或推理。
- 部分 Pod 被调度成功会占住昂贵 GPU/NIC/CPU 资源，但 workload 仍然不能运行。
- 抢占不能只看单个 Pod，否则可能驱逐了一批低优先级 Pod，却仍然无法让高优先级 gang 整体可运行。
- controller、scheduler、autoscaler 都需要同一个标准对象来理解“这一组 Pod 是一个调度单元”。

因此这条设计线的关键不是“增加一个插件”，而是建立新的调度 API 层。

## 核心对象

```text
True workload controller
  |
  +-- Workload
  |     static scheduling policy / template
  |
  +-- PodGroup
  |     runtime scheduling unit
  |     minCount / priority / status / conditions
  |
  +-- Pods
        spec.schedulingGroup -> PodGroup
```

`Workload` 是策略模板，表达这个 workload 的调度层级和规则。它应该相对稳定，适合由 Job、JobSet、LWS、TrainJob、MPIJob 等 controller 创建或映射。

`PodGroup` 是运行时调度实例，表达某一次实际要一起调度的 Pod 集合。它有自己的生命周期、状态和垃圾回收关系。KEP 明确把 `PodGroup` 从 `Workload` 中解耦，是为了避免把大量运行时状态塞进一个长期对象，导致 etcd 对象过大、状态更新冲突和生命周期混乱。

Pod 只引用自己所属的 `PodGroup`。scheduler 看到 Pod 后，通过这个引用找到 group 语义。

## Alpha 到 Beta 的设计演进

第一版 gang scheduling 更像“正确性屏障”：

1. `PreEnqueue` 检查 `PodGroup` 是否存在、scheduler 是否已经观察到至少 `minCount` 个 Pod。
2. `Permit` 阶段等待同组 Pod 都到达同一阶段。
3. 如果超时或无法满足 `minCount`，已占用的预约状态释放，整组回退。

这能保证“不要绑定半个 gang”，但它仍然是以 Pod 为单位推进，性能和全局决策能力有限。

Beta 方向引入 `Workload Scheduling Cycle`：

```text
activeQ pops PodGroup
  |
  +-- take one cluster snapshot
  +-- collect pending pods in the group
  +-- run group-level placement algorithm
  +-- if minCount fits: enter binding path
  +-- if preemption needed: trigger group-aware preemption and retry
  +-- if still not fit: mark PodGroup unschedulable/backoff
```

这个变化很关键：scheduler 不再把 group 成员当作独立 Pod 分散处理，而是在一次调度循环里看完整组的可行性。

## Workload-aware Preemption

`5710-workload-aware-preemption` 解决的是 gang scheduling 的下一个问题：如果一组 Pod 需要抢占，victim 也可能是一组 Pod。

它把 preemption 从这四种情况统一起来：

| Preemptor | Victim | 说明 |
|---|---|---|
| 单 Pod | 单 Pod | 传统模式。 |
| 单 Pod | PodGroup | 单 Pod 可能要驱逐一个低优先级 workload 的整体或部分。 |
| PodGroup | 单 Pod | 高优先级 gang 抢占普通 Pod。 |
| PodGroup | PodGroup | 高优先级 workload 替换低优先级 workload。 |

设计重点是“先判断整个 preemptor 是否可运行，再决定是否真的驱逐”。这避免单个 Pod 的 `PostFilter` 过早触发 preemption，最后发现整组仍然放不下，造成无意义 disruption。

因此它引入或推动 `PodGroupPostFilter` 这类 group-level extension point：只有当完整 PodGroup scheduling cycle 失败后，才给插件一次完整上下文来决定是否抢占。

## Priority 和 Preemption Unit

PodGroup 引入 priority 语义后，scheduler 会以 `PodGroup` 的 priority 作为权威值。Pod 自己的 priority 不能和 PodGroup 冲突，否则会造成用户误解：到底是 Pod 级别还是 group 级别在决定抢占？

设计上的取舍：

- Alpha 允许一定程度的文档化差异。
- Beta/GA 倾向于要求同组 Pod 和 PodGroup priority 一致。
- `preemptionPolicy` 也跟随同样原则，避免一个 PodGroup 内部出现“有的成员可以抢占、有的不能抢占”的不可解释状态。

## Topology-aware Workload Scheduling

Gang scheduling 只解决“是否整组一起调度”，还没有解决“这一组 Pod 应该怎样靠近放置”。`5732-topology-aware-workload-scheduling` 把 PodGroup 扩展到 group-level placement：

- AI training 可能希望所有 workers 在同一 rack、zone、NUMA 或高带宽网络域。
- 多 Pod 不能只逐个用 pod affinity，因为逐个放置会错过组级最优解。
- scheduler 需要先生成候选 placement，再逐个 Pod 做可行性验证和评分。

这条线会和 DRA、NUMA、Node Feature Discovery、GPU topology 强交叉。未来真正有价值的是“workload 级 topology + workload 级 preemption + DRA 设备拓扑”同时成立。

## Controller API 设计

`6089-was-controller-apis` 的核心判断是：不要强迫所有 workload controller 暴露完全相同的用户 API。Job、JobSet、LWS、TrainJob 的用户心智不同，如果硬塞一个统一 schema，反而会阻塞集成。

它选择的方向是：

- 在 `scheduling.k8s.io` 提供可复用 building blocks。
- 各 controller 把这些 building blocks 嵌入自己的 API。
- 用共享 `workloadbuilder` library 把 controller-native API 转换成 scheduler-facing `Workload` / `PodGroup` / `CompositePodGroup`。

这是一种“局部 API 一致性优先于全局强统一”的设计。代价是不同 workload API 的用户体验可能不完全一致；收益是 JobSet、LWS、Kueue 这类生态组件可以更快接入，而不必等待一个完美统一的顶层 workload API。

## 关键失败模式

| 失败模式 | 设计处理 |
|---|---|
| PodGroup 不存在 | Pod 在 `PreEnqueue` 或 filter 路径中等待，不进入普通调度。 |
| 只调度出部分成员 | 不绑定，释放资源，整组回退。 |
| 抢占后 group 仍不可运行 | 通过 group-level post-filter 避免过早驱逐。 |
| PodGroup 状态膨胀 | 独立 `PodGroup` 对象承载 runtime status，避免压垮 `Workload` 对象。 |
| controller API 集成慢 | 使用 reusable building blocks + workloadbuilder，而不是强制统一 API。 |
| autoscaler 不知道加节点是否有效 | 当前仍是后续工作，需要和 [[karpenter]] / Cluster Autoscaler 继续对齐。 |

## 和现有项目的关系

- [[kueue]] 更偏 admission control / quota / queueing。Workload API 让底层 scheduler 有机会原生理解 gang 语义。
- [[scheduler-plugins]] 里的 coscheduling 是历史上 out-of-tree 的对照实现；KEP 线是在把相关能力标准化。
- [[jobset]]、[[lws]] 是最直接的用户侧 workload API 候选。
- [[karpenter]] / Cluster Autoscaler 后续需要理解 PodGroup，否则可能错误判断加节点是否有用。

## 阅读顺序

1. `4671-gang-scheduling`：先理解 Workload / PodGroup 的对象边界。
2. `5710-workload-aware-preemption`：再看抢占如何从 Pod 级扩展到 workload 级。
3. `5732-topology-aware-workload-scheduling`：看 group-level placement。
4. `6089-was-controller-apis`：看 Job/JobSet/LWS 等 controller 如何对接。
5. `6012-composite-podgroup-api`：最后看多层 workload 如何表达。

## 关键 KEP 实现状态

| KEP | 当前状态 | Alpha / Beta / GA | Feature gate | 关键实现路径 |
|---|---|---|---|---|
| `4671-gang-scheduling` | `implementable / beta`，仍在 beta | v1.35 / v1.37 / v1.38 | `GenericWorkload` | `Workload` / `PodGroup` 成为调度单位，scheduler 做 group-level scheduling cycle。 |
| `5710-workload-aware-preemption` | `implementable / beta`，仍在 beta | v1.36 / v1.37 / v1.39 | `GenericWorkload` | 抢占逻辑从单 Pod 扩展到 PodGroup，避免先驱逐后发现整组仍不可运行。 |
| `6012-composite-podgroup-api` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.40 | `CompositePodGroup` | 表达多组件 workload 的组合 PodGroup，适合 JobSet/LWS/训练任务。 |
| `6089-was-controller-apis` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.39 | `WorkloadWithJob` | 给 workload controller 提供可嵌入 building blocks 和转换库。 |
| `5732-topology-aware-workload-scheduling` | `implementable / beta`，仍在 beta | v1.36 / v1.37 / v1.39 | `TopologyAwareWorkloadScheduling` | group-level placement，把一组 Pod 放到满足拓扑目标的节点集合。 |

## 追踪重点

后续要继续跟：

- `Workload` / `PodGroup` API 版本是否进入 beta/stable。
- Job、JobSet、LWS、Kueue 等 controller 的真实集成方式。
- `PodGroupPostFilter` 是否稳定，out-of-tree PostFilter 如何迁移。
- PodGroup 与 DRA ResourceClaim、topology-aware scheduling、Cluster Autoscaler/Karpenter 的联动。
- 生产指标：PodGroup scheduling latency、失败原因、binding 成功率、preemption 造成的 disruption。
