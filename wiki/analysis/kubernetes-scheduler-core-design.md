---
title: Kubernetes Scheduler Core Design
tags: [analysis, kubernetes, kep, sig-scheduling, scheduler, queue, placement, preemption, design-deep-dive]
date: 2026-09-25
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/624-scheduling-framework/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/785-scheduler-component-config-api/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/1451-multi-scheduling-profiles/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4247-queueinghint/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6132-prequeueing-hints/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5598-opportunistic-batching/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/895-pod-topology-spread/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4832-async-preemption/README.md]
related: ["[[kubernetes]]", "[[kubernetes-keps-feature-coverage]]", "[[kubernetes-keps-implementation-matrix]]", "[[kubernetes-keps-design-tracking]]", "[[kubernetes-workload-gang-scheduling-design]]", "[[kubernetes-dra-design-deep-dive]]", "[[scheduler-plugins]]", "[[descheduler]]", "[[kube-scheduler-simulator]]", "[[k8s-core-controller-map]]", "[[kueue]]", "[[karpenter]]"]
---

# Kubernetes Scheduler Core Design

## 当前上游核验（2026-09-25）

本节以执行时官方默认分支为当前证据，commit 不代表 release。Kubernetes KEP 页面与下文既有内容保留历史设计/演进证据；具体实现、feature stage 和默认行为须按目标 Kubernetes 版本核对，不能从提案状态或默认分支推定已经发布。[[src-scheduler-plugins-architecture]] 仍是 2026-06-14 的 raw-backed Source 快照。

| 项目 | 当前 commit | 当前职责 / 证据边界 |
|---|---|---|
| [[kubernetes]] / kube-scheduler | [`ab9b0dcfd320`](https://github.com/kubernetes/kubernetes/commit/ab9b0dcfd32039601ad368ae891efa3ff67600e0) | Scheduling Framework 组织插件扩展点；scheduling cycle 选择 Node，binding cycle 将选择应用到集群。Pod placement/binding 属于 scheduler 职责 |
| [[scheduler-plugins]] | [`6df8d8e4ae5f`](https://github.com/kubernetes-sigs/scheduler-plugins/commit/6df8d8e4ae5f53d8c20e57e703d7f0a6340baddd) | 通过 out-of-tree plugins 扩展 kube-scheduler；其 `scheduling.x-k8s.io/v1alpha1` PodGroup / ElasticQuota 与 Kubernetes 原生 API 演进分开核验，部署须匹配 Kubernetes 依赖版本 |

官方入口：[Scheduling Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/)、[Scheduler Configuration](https://kubernetes.io/docs/reference/scheduling/config/)、[当前 kube-scheduler 源码](https://github.com/kubernetes/kubernetes/tree/ab9b0dcfd32039601ad368ae891efa3ff67600e0/pkg/scheduler)、[Scheduler Plugins 文档](https://scheduler-plugins.sigs.k8s.io/docs/) 与 [当前兼容矩阵](https://github.com/kubernetes-sigs/scheduler-plugins/blob/6df8d8e4ae5f53d8c20e57e703d7f0a6340baddd/README.md#compatibility-matrix)。跨项目主线见 [[kubernetes-workload-gang-scheduling-design]]：[[kueue]] 负责 admission，[[karpenter]] 负责节点容量反馈；通用 controller 工具链见 [[k8s-core-controller-map]]。

## M5-B 中的职责边界

[[kubernetes-workload-gang-scheduling-design]] 是跨项目入口，本页下钻 Pod 的 placement/binding 与失败重试。[[kueue]] 在所管理工作负载进入实际 Pod 调度前完成配额准入，再由 integration unsuspend 工作负载或移除 Pod scheduling gates；Pod 对象可能在准入前已存在。kube-scheduler 对可调度 Pod 选择 Node 并完成 binding，[[scheduler-plugins]] 以 out-of-tree 插件扩展同一 framework，不能据此推定它接管 JobSet/LWS 等业务对象生命周期。

[[karpenter]] 从未调度 Pod 的状态和约束计算容量需求，经 NodePool/NodeClass、NodeClaim 与节点生命周期补充容量；它不执行 Pod binding。新 Node 的状态变化再成为 scheduler 重试的输入，扩容成功也不保证 Pod 的所有放置约束可满足。

## Scheduling / Binding Cycle

```text
QUEUE ENTRY
  Pod event - - enqueue eligibility - -> PreEnqueue
  PreEnqueue ── success ──> activeQ (ordered by QueueSort) ── pop ──> profile
  PreEnqueue - - gated / reject - -> unschedulableQ

SCHEDULING CYCLE (serial, single-Pod path)
  profile ──> snapshot / PreFilter ──> Filter
  Filter ── no feasible Node ──> PostFilter / optional preemption
  PostFilter - - nomination / failure feedback: retry later - -> queue
  Filter ── feasible Nodes ──> PreScore / Score / NormalizeScore
    ── select Node ──> assume in scheduler cache ──> Reserve ──> Permit
  Permit ── approve OR wait ──> dispatch binding cycle
  Reserve / Permit failure ──> Unreserve / forget assumed Pod
    - - failure / retry - -> queue

BINDING CYCLE (may run concurrently for different Pods)
  WaitOnPermit (if waiting) ── approved ──> PreBind ──> Bind ──> PostBind
  WaitOnPermit reject/timeout OR PreBind/Bind failure
    ──> Unreserve / forget assumed Pod - - failure / retry - -> queue
```

实线 `── label ──>` 表示调用或有序步骤，虚线 `- - label - ->` 表示事件、排队和后续重试；图中失败回队列后仍需经过下一节的唤醒与退避判断。PreEnqueue 在 activeQ 之前执行，QueueSort 决定队列顺序，并非 Pod 被 pop 后才依次执行这两步。当前图聚焦单 Pod 路径；原生 PodGroup 调度另见 L1 页的 KEP 边界。

这里按锚定 commit 的 [`schedule_one.go`](https://github.com/kubernetes/kubernetes/blob/ab9b0dcfd32039601ad368ae891efa3ff67600e0/pkg/scheduler/schedule_one.go) 区分周期：`schedulingCycle` 调用 `prepareForBindingCycle`，其中完成 assume/reserve 和首次 Permit 调用；之后异步启动 `bindingCycle`，在 `WaitOnPermit` 等待需要放行的 Pod，再执行 PreBind/Bind/PostBind。这与 [Scheduling Framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/) 对 Permit 位于 scheduling cycle 末尾的说明一致。图省略了版本/feature gate 相关的辅助检查，不把 Reserve/Permit 整体移到 binding cycle。

`nominatedNodeName` 表达候选或预期，不等于已绑定；抢占选出的候选通常要在后续调度周期重验。当前轮选择 Node 后的 assume 也是 scheduler 的内存记账，不是 API binding 已成功。Reserve/Permit 与后续阶段失败时必须释放相应保留状态；Bind 成功后才运行 PostBind。

## Queue / Requeue Feedback

```text
Kueue admission - - admitted feedback - -> workload / Pod integration
integration ── unsuspend OR remove scheduling gates ──> eligible Pod
Pod - - watch / enqueue - -> PreEnqueue ── success ──> activeQ (QueueSort)
PreEnqueue - - gated / reject - -> unschedulableQ
activeQ ── pop ──> scheduling / binding attempt
attempt - - unschedulable / error feedback - -> failure handler
failure handler - - wait for relevant change - -> unschedulableQ
failure handler - - retry after backoff - -> backoffQ

Node / Pod / plugin-relevant cluster events
  - - QueueingHints: eligible to retry - -> unschedulableQ re-evaluation
unschedulableQ - - retry eligible + backoff pending - -> backoffQ
unschedulableQ - - retry eligible + backoff satisfied / bypass allowed - -> activeQ
backoffQ - - backoff complete / queue activation - -> activeQ
unschedulableQ - - periodic fallback re-evaluation - -> activeQ or backoffQ

Pod Unschedulable - - observed state / event - -> Karpenter capacity controller
Karpenter ── NodePool + NodeClass / NodeClaim lifecycle ──> Node
Node - - capacity / readiness event - -> cluster events / QueueingHints above
```

`unschedulableQ` 在这里是概念名；该 commit 的实现使用 `unschedulableEntities`，可保存 Pod 或 PodGroup。activeQ 保存可尝试项，backoffQ 保存等待退避的项；失败回队列的位置还取决于失败插件、在途事件和当前退避状态，不是所有错误都固定先进入同一个队列。QueueingHint 根据插件关心的变化决定是否值得再试，未命中时继续等待；相关事件不是“无条件唤醒全部 pending Pods”。回到 activeQ 仍须满足入队门槛，周期性兜底也不会自动解除 scheduling gates。实现依据见 [当前 scheduling queue](https://github.com/kubernetes/kubernetes/blob/ab9b0dcfd32039601ad368ae891efa3ff67600e0/pkg/scheduler/backend/queue/scheduling_queue.go)。

Kueue 的等待准入和 scheduler 的不可放置是不同状态。被 gate 挡住的 Pod 不能直接当作已经执行 Filter 后的 Unschedulable；Karpenter 也必须结合 Pod 和节点约束评估可供应容量。对允许调度后仍缺少节点的 Pod，新 Node 通过 watch/队列机制触发重算，不会绕过 Filter、Permit 或 Bind。

## Scheduling 失败路径

| 失败点 / 直接影响 | 自动恢复与控制器协同 | 人工排查 / 修复边界 |
|---|---|---|
| Filter 无 feasible Node：当前轮无法选 Node | 按配置尝试 PostFilter；后续相关事件与退避允许重新评估 | 检查失败插件、资源请求、taint、affinity、拓扑等硬条件；增加不匹配的节点不会解决问题 |
| PostFilter / preemption 无可行结果：可能无候选或 victim 释放后仍不足 | 抢占策略允许时选择候选，等待资源变化后重试；nomination 不保证后续绑定 | 检查优先级、抢占策略、不可由抢占消除的约束；不要将 PDB 理解为 scheduler preemption 的绝对保护 |
| Reserve 失败或后续阶段失败：保留状态需清理 | 运行 Unreserve、撤销 assumed Pod；Unreserve 应幂等且不能失败 | 自定义插件泄漏资源、不可逆副作用或不完整回滚需修正代码/清理外部状态，不能仅靠 requeue |
| Permit wait / reject / timeout：绑定暂停或被拒绝 | 等待相关插件批准；拒绝/超时触发清理和重新排队 | 检查组成员、超时、外部条件与插件配置；增加超时不会修复永久缺失的成员 |
| PreBind 失败：绑定前准备未完成 | 中止 binding cycle、清理保留状态并重试；依赖控制器恢复后再尝试 | 检查外部依赖、权限和插件错误；确认重复执行及补偿能处理部分完成的准备操作 |
| Bind 失败：API 层绑定未确认 | scheduler 走失败处理，依据后续 API/watch 状态判断 Pod 是否仍需调度 | 区分权限/冲突/网络超时；超时不证明服务端未写入，避免插件盲目重复不可逆操作 |
| 插件数据陈旧：快照或外部缓存与实际状态不一致 | 正常 watch 更新与下一轮 snapshot 可修正暂时陈旧；插件需注册正确的重试事件 | 长期不同步、错误失效策略或漏注册事件需修复；调度队列不能替代外部缓存一致性设计 |
| 插件目标冲突：Filter 交集为空或 Score 权重违背预期 | 只在输入变化后重算；没有自动“放松策略”的通用机制 | 校验 profile、插件开关/顺序/权重与业务目标，用 [[kube-scheduler-simulator]] 对照具体决策 |

out-of-tree 插件与 in-tree 插件都通过 framework 参与相应阶段；部署 scheduler-plugins 并不建立另一套 JobSet/LWS 所有权模型。故障定位应同时看 Pod events/status、失败 extension point 和相关控制器状态，避免把所有 Pending 都归为容量不足。

## KEP 设计背景

下面保留 scheduler core 的 framework、component config、profiles、queue/requeue、topology placement、async preemption 和性能演进笔记。历史状态表不作为本次对 release/feature stage 的重新核验；逐个 KEP 的追踪入口见 [[kubernetes-keps-implementation-matrix]]。

## 一句话定位

Scheduler core KEP 的共同目标是把 kube-scheduler 从一个内置策略集合，演进为可配置、可扩展、可解释、可高吞吐的调度框架。

## Scheduler Framework

`624-scheduling-framework` 是最关键的基础 KEP。它把一次 Pod 调度拆成多个 extension point，当前调用顺序与分支见上方 Scheduling / Binding Cycle。PostFilter 属于无可行节点时的恢复分支，不能画成每次 Filter 后必经的一步。

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

完整事件、队列、profile、framework 与失败反馈路径已合并到上方两张图。

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
