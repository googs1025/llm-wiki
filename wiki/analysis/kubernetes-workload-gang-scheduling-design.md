---
title: Kubernetes Workload and Gang Scheduling Design
tags: [analysis, kubernetes, kep, sig-scheduling, gang-scheduling, workload-api, design-deep-dive]
date: 2026-09-25
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4671-gang-scheduling/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5710-workload-aware-preemption/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6012-composite-podgroup-api/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/6089-was-controller-apis/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5732-topology-aware-workload-scheduling/README.md, src-kueue-architecture, src-jobset-architecture, src-lws-architecture, src-scheduler-plugins-architecture, src-karpenter-architecture]
related: ["[[kubernetes]]", "[[kubernetes-keps-design-tracking]]", "[[kubernetes-keps-implementation-matrix]]", "[[kubernetes-workload-automation]]", "[[kueue]]", "[[scheduler-plugins]]", "[[jobset]]", "[[lws]]", "[[karpenter]]", "[[kubernetes-scheduler-core-design]]"]
---

# Kubernetes Workload and Gang Scheduling Design

## 当前上游核验（2026-09-25）

本节记录执行时官方默认分支的当前快照，用于 M5-B 的跨项目职责比较；commit 不是 release 标识，API 在默认分支存在也不等于已在目标集群版本发布。[[src-kueue-architecture]]、[[src-jobset-architecture]]、[[src-lws-architecture]]、[[src-scheduler-plugins-architecture]] 与 [[src-karpenter-architecture]] 保留 2026-06-14 的 raw-backed Source 快照。下文既有 KEP 内容保留历史设计与演进语境；scheduler 底座的当前证据见 [[kubernetes-scheduler-core-design]]。

| 项目 | 当前 commit | 当前 API / 职责 | M5-B 层 |
|---|---|---|---|
| [[kueue]] | [`2a766717037a`](https://github.com/kubernetes-sigs/kueue/commit/2a766717037ac8c8ca8ee03539e7504db2a56008) | 当前 `kueue.x-k8s.io/v1beta2` 包含 Workload、LocalQueue、ClusterQueue、ResourceFlavor、Cohort、AdmissionCheck、Topology；管理配额、flavor 与准入，不负责 Pod 最终绑定到 Node | Admission / quota |
| [[jobset]] | [`03f9dccef945`](https://github.com/kubernetes-sigs/jobset/commit/03f9dccef945c12e6ea9a35c524b928b9599cd87) | `jobset.x-k8s.io/v1alpha2` JobSet 用 ReplicatedJobs 组合子 Job，提供依赖、coordinator、成功/失败与重启策略 | Workload / Job lifecycle |
| [[lws]] | [`d4f1525f15a4`](https://github.com/kubernetes-sigs/lws/commit/d4f1525f15a491170de19bc6abc1c89fe185b16c) | `leaderworkerset.x-k8s.io/v1` 管理 leader/worker Pod 组；`disaggregatedset.x-k8s.io/v1` 组合多个子 LWS，管理分离推理角色、slice 与协调发布 | Workload / group and role lifecycle |
| [[scheduler-plugins]] | [`6df8d8e4ae5f`](https://github.com/kubernetes-sigs/scheduler-plugins/commit/6df8d8e4ae5f53d8c20e57e703d7f0a6340baddd) | kube-scheduler 的 out-of-tree framework plugins；配套 `scheduling.x-k8s.io/v1alpha1` PodGroup / ElasticQuota 支撑相应插件，与 Kubernetes 原生 Workload/PodGroup KEP API 分开看 | Pod placement / scheduler extensions |
| [[karpenter]] | [`06bc3b4b94dd`](https://github.com/kubernetes-sigs/karpenter/commit/06bc3b4b94dd9af0228db4b611f2ebcb2ba17b9c) | `karpenter.sh/v1` NodePool / NodeClaim 联合 provider-specific NodeClass 表达容量约束与节点生命周期；响应不可调度 Pod 的容量需求，不执行 Pod binding | Node capacity / lifecycle |

官方依据：[Kueue Concepts](https://kueue.sigs.k8s.io/docs/concepts/) 与 [当前 v1beta2 API 源码](https://github.com/kubernetes-sigs/kueue/tree/2a766717037ac8c8ca8ee03539e7504db2a56008/apis/kueue/v1beta2)、[JobSet Concepts](https://jobset.sigs.k8s.io/docs/concepts/) 与 [v1alpha2 API](https://jobset.sigs.k8s.io/docs/reference/jobset.v1alpha2/)、[LWS Concepts](https://lws.sigs.k8s.io/docs/concepts/)、[Scheduler Plugins 文档](https://scheduler-plugins.sigs.k8s.io/docs/)、[Karpenter NodePools](https://karpenter.sh/docs/concepts/nodepools/) 与 [NodeClaims](https://karpenter.sh/docs/concepts/nodeclaims/)。安装时仍需核对所选 release 的 CRD、feature gates 和 Kubernetes 兼容矩阵。

## D1 · Workload / Admission / Placement / Capacity

```text
WORKLOAD EXPRESSION
  JobSet / LeaderWorkerSet (LWS) / DisaggregatedSet (DS)
    - - supported integration / PodSets - -> ADMISSION AND QUOTA

ADMISSION AND QUOTA
  Kueue: Workload / LocalQueue / ClusterQueue
         ResourceFlavor / Cohort / AdmissionCheck / Topology
    - - admitted: unsuspend / remove scheduling gates - -> POD PLACEMENT

POD PLACEMENT
  kube-scheduler framework + configured scheduler-plugins
    ── select feasible Node / bind Pod ──> existing Node
    - - unschedulable Pod feedback - -> NODE CAPACITY

NODE CAPACITY
  Karpenter: Pod requirements + NodePool + provider-specific NodeClass
    ── create capacity request ──> NodeClaim
    ── launch / register / initialize ──> Node
  Node - - capacity / readiness events: requeue - -> POD PLACEMENT
```

图例：实线 `── label ──>` 表示顺序控制动作或同步 API 操作，不承诺跨控制器原子完成；虚线 `- - label - ->` 表示带条件的集成、事件、准入反馈或重试。分区表示职责，既有 Node 能放下 Pod 时无需进入扩容路径。

[[jobset]]、[[lws]] 及 LWS 仓库中的 DisaggregatedSet 表达组、角色、子资源与生命周期。[[kueue]] 决定 Workload 何时取得配额和准入，选择 flavor、必要时约束拓扑域；它不负责最终 Node 选择或 Pod binding。kube-scheduler 完成 placement/binding，[[scheduler-plugins]] 扩展其 framework 插件能力。[[karpenter]] 负责节点容量及生命周期，不绑定 Pod。图中的 integration 是条件关系：只有已启用且受当前版本支持的工作负载集成才走 Kueue 路径。

## D2 · Admission 与 Scheduling 路径

```text
Create JobSet / LWS / DS (roles -> child LWS)
  - - supported integration / Pod templates - -> Kueue Workload / PodSets
Workload ── resolve queueName ──> LocalQueue ── resolve reference ──> ClusterQueue
ClusterQueue + optional Cohort ── evaluate ──> quota / ResourceFlavor
  + configured AdmissionChecks + optional Topology constraints
  ── record reservation / check state ──> Workload admission status
  - - admitted feedback - -> integration controller
integration controller ── unsuspend workload OR remove Pod scheduling gates ──> Pods
Pods - - watch / enqueue - -> kube-scheduler
  QueueSort ──> PreFilter ──> Filter ──> PreScore / Score ──> Reserve ──> Permit
  Permit approved ──> PreBind ──> Bind ──> PostBind
```

这是成功路径，省略 PreEnqueue、PostFilter 等分支；完整 cycle 与失败回退见 [[kubernetes-scheduler-core-design]]。LocalQueue 引用 ClusterQueue；Cohort 是配额共享关系，不是所有任务必经的另一条队列。QuotaReserved 与 Admitted 也不是同一个完成条件：已配置的 AdmissionCheck 必须满足要求，启用 topology-aware scheduling 时还要满足对应容量/拓扑条件。准入成功不保证所有 Pod 已绑定或业务已就绪，依据见 [Kueue Concepts](https://kueue.sigs.k8s.io/docs/concepts/)。

集成差异决定“允许开始”的具体操作：JobSet 集成通过工作负载 suspend 状态控制启动；[LWS 集成](https://kueue.sigs.k8s.io/docs/tasks/run/leaderworkerset/) 基于 Plain Pod Group，以每个 LWS group 为准入单元，Pod 可以先存在并由 scheduling gate 暂停调度。DS 先编排子 LWS；本图不据此推定存在 DS 整体原子准入，仍需验证角色标签传递、子 LWS 集成和所用版本。不能把三种 API 都画成同一个 owner controller 创建全部 Workload 后统一 unsuspend。

## D3 · Capacity Feedback

```text
Pod: PodScheduled=False / Unschedulable
  - - observed condition / Pod event - -> Karpenter provisioning controller
Karpenter ── combine constraints ──> pending Pod requirements
                                    + NodePool
                                    + provider-specific NodeClass
  ── create immutable capacity request ──> NodeClaim
NodeClaim lifecycle (controller + provider + kubelet)
  ── launch instance ──> register Node ──> initialize resources ──> Node ready
Node - - watched capacity / readiness changes - -> scheduler queue / retry
kube-scheduler ── re-evaluate feasible Nodes / bind ──> Pod placement
```

NodeClaim 是容量请求；不可变的是容量规格，不是随阶段推进的 status。检查 `Launched`、`Registered`、`Initialized` 等条件，可以区分云侧启动、Node 注册和资源初始化问题。Node Ready 也不替代 scheduler 的约束检查；即使扩容成功，Pod 仍可能因 affinity、taint 或拓扑约束无法放置。Karpenter 观察 Pod/NodePool/NodeClass 并重新计算需求，事件是触发重新评估的反馈，不是 scheduler 向它发送的同步“创建指定节点”请求。参见 [NodeClaims](https://karpenter.sh/docs/concepts/nodeclaims/)。

Disruption 是独立于扩容的控制路径：drift/consolidation 受相应 NodePool disruption budgets 和驱逐约束影响，必要时先 pre-spin replacement，再 drain/terminate。Expiration 属于 forceful 路径，不受 NodePool disruption budgets 限速，也不保证先等待替代节点就绪；PDB、`do-not-disrupt` 与 `terminationGracePeriod` 对排空和强制终止有不同作用，不能统一理解成“有预算就可安全回收”。参见 [Karpenter Disruption](https://karpenter.sh/docs/concepts/disruption/)。

## D4 · Workload 生命周期

| API / 所有权单位 | 子资源 / 关键状态 | 成功、失败与重启语义 | 扩缩 / 发布边界 | API / 快照注意事项 |
|---|---|---|---|---|
| [[jobset]]：一组 ReplicatedJobs | 子 Job、Pod；DependsOn、coordinator；可配置共享 PVC 与 retention | success/failure policy 汇总子 Job 结果；按规则与 maxRestarts 执行 restart strategy，不等于无限重试 | ReplicatedJob 的副本、依赖与 JobSet 重启由 JobSet controller 管理；不是 serving group 的滚动发布模型 | `jobset.x-k8s.io/v1alpha2`；字段可用性以表首 commit 和部署 release 为准 |
| [[lws]] / LeaderWorkerSet：一个 replica 是 leader/worker Pod 组 | controller 管理 StatefulSet/Pod 组与服务发现，观察副本 readiness | 按配置的 group restart policy 恢复受影响组；持续 serving 的 Ready 不等于 batch Completed | replicas 按组扩缩，LWS controller 负责组发布、placement/subgroup 约束 | `leaderworkerset.x-k8s.io/v1`；Kueue group admission 不提供跨所有 replicas 的原子启动 |
| DisaggregatedSet：多角色 serving topology / slices | 角色映射到子 LWS；跨角色 revision、readiness、drain 状态 | 组内失败由子 LWS 策略处理，DS 协调角色发布与 drain；不套用 JobSet 完成策略 | 支持角色维度与 slice 维度扩缩，由 DS 协调跨角色 rollout | `disaggregatedset.x-k8s.io/v1`；当前能力不能回写成 2026-06-14 Source 已覆盖的结论 |
| [[kueue]] Workload：一次准入所需 PodSets | queue 引用、QuotaReserved/Admitted、AdmissionCheck 状态、eviction/requeue；业务子资源仍由原 controller 管理 | 准入、驱逐与重新排队按策略推进，业务成功/失败由集成反映；释放配额不等于重启业务 | PodSet 变化、扩缩和重新准入取决于具体 integration；Kueue 不接管 rollout | 当前 `kueue.x-k8s.io/v1beta2`；不要与 Kubernetes KEP 中的 Workload/PodGroup 混为一种 API |

生命周期依据：[JobSet v1alpha2 API](https://jobset.sigs.k8s.io/docs/reference/jobset.v1alpha2/)、[JobSet 当前 API 定义](https://github.com/kubernetes-sigs/jobset/blob/03f9dccef945c12e6ea9a35c524b928b9599cd87/api/jobset/v1alpha2/jobset_types.go)、[LWS / DisaggregatedSet Concepts](https://lws.sigs.k8s.io/docs/concepts/)。

## D5 · 失败边界

| 失败点 / 直接影响 | 自动重试 / 控制器恢复边界 | 需要人工处理的情况 |
|---|---|---|
| LocalQueue / ClusterQueue 缺失或 inactive：Workload 无法正常准入 | 队列恢复、相关依赖就绪后，Kueue 可重新评估；重试不会自动创建租户所需配置 | 修正 queue-name、引用、stop policy、权限或缺失依赖，检查 queue conditions |
| quota / flavor 不足：排队或不能完成 reservation | 配额释放、共享配额可用后重试；borrowing/preemption 只按已配置策略执行 | 调整配额、flavor 约束、共享/抢占策略或业务规模；加 Node 不会自动增加配额 |
| AdmissionCheck / 外部 provisioning 卡住：有配额仍未 Admitted | 对应 check controller 恢复后更新状态；Retry/Rejected 的处理依集成和策略 | 修复 check controller、外部凭据/服务、provisioning 配置；Kueue 不能保证外部供应成功 |
| topology 无解：Kueue TAS 无可用域或后续 placement 仍不满足 | 域内容量或标签变化后重算；不自动放宽 required topology | 校验 Topology/ResourceFlavor、PodSet 分组、节点标签与硬约束，避免假设任意新增 Node 都有效 |
| scheduler Filter 无 feasible Node：Pod 未绑定 | 相关事件触发 requeue；PostFilter/preemption 仅在策略允许且能产生可行结果时有帮助 | 修复互斥 affinity/taint/资源条件，或增加满足约束的容量；抢占不能解决所有不可行条件 |
| NodeClaim launch / register / initialize 失败：容量请求未变成可用 Node | Karpenter/provider 按错误和超时路径重试或清理，仍需观察阶段 conditions；不承诺每种错误无限自愈 | 分别检查云配额/可用性/权限、启动与注册配置、网络与初始化资源；修复 NodeClass / NodePool |
| JobSet child Job failure：JobSet 可能重启或终止失败 | 按 failure rules、restart strategy、maxRestarts 恢复；达到终止条件后不会靠排队重试继续运行 | 修复镜像/应用/数据或依赖问题，评估共享 PVC retention 后重新提交/恢复任务 |
| LWS group / DS role-slice 失败：副本不可用或 rollout/drain 停滞 | LWS 按组策略恢复，DS 按角色 readiness 和发布策略继续协调；不保证跨角色业务状态一致 | 检查 restart policy、readiness、角色依赖和 drain 协议，修复持续故障或不兼容版本 |
| PDB / do-not-disrupt / termination 约束冲突：节点排空停滞或被强制终止 | 自愿 disruption 等待条件允许；配置的 NodeClaim terminationGracePeriod 到期可强制删除剩余 Pod | 核对预算、保护注解、checkpoint/drain 所需时间；排空完成与保住业务进度是不同结果 |

排障时先定位停在“准入、放置、节点容量、业务生命周期”的哪一层，再看该层的 status/conditions 和 events。上述自动路径依赖有效配置及可恢复的外部条件；细化证据见 [Kueue 队列排障](https://kueue.sigs.k8s.io/docs/tasks/troubleshooting/troubleshooting_queues/)、[[kubernetes-scheduler-core-design]] 与 D3/D4 的官方文档。

## KEP 背景与演进（历史设计）

下面保留 `sig-scheduling` 的设计线：从单 Pod 调度，走向 Workload / PodGroup 作为调度单位。核心 KEP 是 `4671-gang-scheduling`，后续由 `5710-workload-aware-preemption`、`6012-composite-podgroup-api`、`6089-was-controller-apis` 和 `5732-topology-aware-workload-scheduling` 继续展开。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]；这里的设计与状态表沿用历史笔记，不作为当前发布状态的重新核验。

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

在这组 KEP 的对象模型中，业务 workload controller 创建或映射三类对象：`Workload` 保存静态调度策略/模板；`PodGroup` 承载运行时调度单元及 `minCount`、priority、status/conditions；Pod 通过 `spec.schedulingGroup` 引用所属 PodGroup。这里的对象层级不同于 D1 中 Kueue 的准入 API。

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

1. 从 activeQ 取出 PodGroup，获取一次 cluster snapshot。
2. 收集该组 pending Pods，执行 group-level placement。
3. 满足 minCount 时进入 binding 路径。
4. 需要抢占时执行 group-aware preemption 并重试；仍无法放置时标记 PodGroup unschedulable/backoff。

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
- [[jobset]] 管理一组 Job；[[lws]] 管理 leader/worker 组，其当前 DisaggregatedSet 进一步组合多角色子 LWS。业务 API 的生命周期编排与 KEP 的 scheduler-facing 对象需要通过具体集成衔接。
- [[karpenter]] / Cluster Autoscaler 的现有容量反馈不能直接等同于理解原生 PodGroup 全部约束；历史 KEP 所指的 group-aware 扩容协同仍须按当前版本和集成另行核验。

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
