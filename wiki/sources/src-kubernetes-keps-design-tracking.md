---
title: Kubernetes KEP Design Tracking
tags: [source, kubernetes, kep, sig-scheduling, sig-autoscaling, sig-node, design-tracking]
date: 2026-07-06
sources: [/Users/zhenyu.jiang/enhancements/keps/sig-scheduling, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling, /Users/zhenyu.jiang/enhancements/keps/sig-node]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-keps-feature-coverage]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-scheduler-core-design]], [[kubernetes-workload-gang-scheduling-design]], [[kubernetes-dra-design-deep-dive]], [[kubernetes-hpa-autoscaling-design]], [[kubernetes-in-place-pod-resize-design]], [[kubernetes-node-runtime-observability-security-design]], [[kubernetes-dra]], [[kubernetes-workload-automation]], [[kueue]], [[karpenter]], [[metrics-server]], [[prometheus-adapter]], [[scheduler-plugins]], [[node-feature-discovery]]
---

# Kubernetes KEP Design Tracking

这页是 `/Users/zhenyu.jiang/enhancements/keps` 中 `sig-scheduling`、`sig-autoscaling`、`sig-node` 三个 SIG 的 KEP 设计方案源摘要。它的目标不是抽象一个新概念，而是建立一个可持续更新的 **KEP 设计追踪入口**：按 SIG、设计方向、状态、成熟度、交叉依赖和阅读优先级组织 KEP。

更偏清单和后续追踪的表格见 [[kubernetes-keps-design-tracking]]；逐个 KEP 的实现状态、Alpha/Beta/GA、feature gates 和关键实现路径见 [[kubernetes-keps-implementation-matrix]]。

本轮已把最重要的合并设计组单独拉出详解：

- [[kubernetes-keps-feature-coverage]]
- [[kubernetes-keps-implementation-matrix]]
- [[kubernetes-scheduler-core-design]]
- [[kubernetes-workload-gang-scheduling-design]]
- [[kubernetes-dra-design-deep-dive]]
- [[kubernetes-hpa-autoscaling-design]]
- [[kubernetes-in-place-pod-resize-design]]
- [[kubernetes-node-runtime-observability-security-design]]

## 范围和方法

本轮只读取三个 SIG 的 KEP 目录，不纳入 `prod-readiness/*` YAML：

| SIG | README 数量 | 追踪重点 |
|---|---:|---|
| `sig-scheduling` | 58 | scheduler framework、队列、抢占、workload/gang、PodGroup、DRA 调度语义。 |
| `sig-autoscaling` | 9 | HPA API、metrics、behavior、tolerance、scale from zero、fallback、Cluster Autoscaler 集成。 |
| `sig-node` | 125 | kubelet、CRI、resource managers、device plugin、DRA/CDI、Pod lifecycle、安全、节点健康。 |

追踪维度：

| 维度 | 说明 |
|---|---|
| `SIG` | KEP 所属目录和 owning-sig。 |
| `分类` | 设计方向，不按 KEP 文件夹机械排序。 |
| `状态` | 从 `kep.yaml` 读取 `status/stage/latest-milestone`，但保留人工判断。 |
| `方案要点` | 该 KEP 解决的设计问题、API/控制面边界和与其他 KEP 的关系。 |
| `追踪优先级` | P0 表示正在形成设计主线或近期 v1.35-v1.37 活跃；P1 表示稳定但仍是背景知识；P2 表示历史/补充。 |

## 总体设计线索

```text
KEP design tracking
  |
  +-- sig-scheduling
  |     +-- scheduler framework / config
  |     +-- queue / requeue / batching
  |     +-- placement / topology / affinity
  |     +-- preemption / disruption
  |     +-- workload / PodGroup / gang
  |     +-- DRA / device-aware scheduling
  |
  +-- sig-autoscaling
  |     +-- HPA API and behavior
  |     +-- metrics specificity and pod selection
  |     +-- scale from zero and external metrics fallback
  |     +-- Cluster Autoscaler integration
  |
  +-- sig-node
        +-- kubelet / CRI / runtime boundary
        +-- CPU / memory / topology managers
        +-- DRA / device plugin / CDI
        +-- Pod lifecycle and resize
        +-- security / isolation
        +-- observability / node health
```

## SIG Scheduling 设计方案

### 1. Scheduler framework / config

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `624-scheduling-framework` | implemented / stable | 把调度过程拆成 QueueSort、PreFilter、Filter、PostFilter、PreScore、Score、Reserve、Permit、PreBind、Bind、PostBind 等扩展点。核心设计是让复杂策略变成 plugin，而不是继续膨胀 scheduler core。 |
| `785-scheduler-component-config-api` | implemented / stable | 给 scheduler 配置提供 versioned ComponentConfig，支撑 profile、plugin enable/disable/order/args。 |
| `1451-multi-scheduling-profiles` | implementable / beta | 多个 scheduling profile 共享同一个 scheduler 实例，减少多 scheduler binary 的部署和 cache 成本。 |
| `1819-scheduler-extender` | implemented / stable | 历史扩展路径：HTTP extender 在 Filter/Prioritize/Preempt/Bind 等阶段介入，但性能、cache、错误回滚和扩展点数量都有局限。 |

设计判断：后续 KEP 基本都建立在 scheduler framework 之上。追踪 scheduling KEP 时，先判断它是在新增 framework extension point、改变 queue 行为，还是只是在某个 plugin 里新增策略。

### 2. Queue / requeue / batching

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `3521-pod-scheduling-readiness` | implemented / stable | 通过 scheduling gates 让 Pod 在外部条件满足前不进入正常调度，避免 scheduler 反复尝试明显不可调度的 Pod。 |
| `4247-queueinghint` | implemented / stable | 每个 plugin 给事件注册 QueueingHint，告诉调度队列某类事件是否可能让某个 Pod 可调度。重点是减少无效 requeue，并允许 DRA 等等待型场景跳过不必要 backoff。 |
| `6132-prequeueing-hints` | implementable / beta | 在 PreQueueing 阶段过滤事件，让调度队列在 Pod 进入 activeQ 之前更早判断是否值得唤醒。 |
| `5142-pop-backoffq-when-activeq-empty` | implementable / beta | activeQ 空时从 backoffQ 提前取 Pod，提高队列吞吐和资源利用。 |
| `5501-reflect-preenqueue-rejections-in-pod-status` | implementable / beta | 把 PreEnqueue 拒绝原因反映到 Pod status，降低“为什么 pending”的排障成本。 |
| `5598-opportunistic-batching` | implementable / beta | 利用批处理机会减少重复计算，面向高吞吐调度场景。 |

设计判断：queue 线是近期调度性能和可解释性的核心。它把 scheduler 从“失败后等待 backoff”推进到“插件能解释哪些事件真正有用”。

### 3. Placement / topology / affinity

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `895-pod-topology-spread` | implemented / stable | 将 spread 约束作为一等调度策略，解决跨 zone/node/domain 的副本分布问题。 |
| `1258-default-pod-topology-spread` | implementable / stable | 默认拓扑分布策略，减少用户未配置 spread 时的集中风险。 |
| `3022-min-domains-in-pod-topology-spread` | implemented / stable | 为 PodTopologySpread 增加最小 domain 语义，避免 domain 数不足时产生误判。 |
| `3094-pod-topology-spread-considering-taints` | implemented / stable | skew 计算纳入 taints/tolerations，避免把实际不可用节点当成可用拓扑域。 |
| `3243-respect-pod-topology-spread-after-rolling-upgrades` | implementable / beta | 滚动升级后继续尊重 PodTopologySpread，关注长期分布漂移。 |
| `2249-pod-affinity-namespace-selector` | implementable / stable | Pod affinity 引入 namespace selector，提高跨 namespace 选择能力。 |
| `3633-matchlabelkeys-to-podaffinity` | implemented / stable | affinity/anti-affinity 支持 matchLabelKeys/mismatchLabelKeys，让同一 rollout/hash 这类动态标签参与匹配。 |
| `2458-node-resource-score-strategy` | implementable / beta | 节点资源打分策略可配置，支撑 MostAllocated / RequestedToCapacityRatio 等资源拟合策略。 |
| `5471-enable-sla-based-scheduling` | implementable / alpha | 扩展 toleration operator 支撑 threshold-based placement，适合 SLA/容量阈值表达。 |

设计判断：placement 线要区分“节点可行性 filter”和“偏好 score”。拓扑 KEP 还会和 DRA、NUMA、PodGroup 交叉，后续应重点看 topology-aware workload scheduling。

### 4. Preemption / disruption

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `268-priority-preemption` | implementable / alpha | Priority 和 preemption 的基础线，定义高优先级 Pod 通过驱逐低优先级 Pod 获得容量。 |
| `902-non-preempting-priorityclass` | implemented / stable | PriorityClass 支持 non-preempting，用高优先级排序但不驱逐已有 Pod。 |
| `3280-guarantee-pdb-when-preemption-happens` | implementable / alpha | 抢占时更严格地保护 PDB，降低控制面为了调度破坏可用性的风险。 |
| `4832-async-preemption` | implementable / beta | 将抢占执行异步化，避免调度周期被删除 victim Pod 等动作阻塞。 |
| `5278-nominated-node-name-for-expectation` | implementable / beta | 改善 nominated node 的期望表达，减少抢占和绑定过程中的不一致。 |
| `5710-workload-aware-preemption` | implementable / beta | 针对 PodGroup/workload 做整体抢占决策，避免单 Pod 抢占导致 gang 仍无法整体运行。 |
| `5836-scheduler-preemption-for-ippr` | implementable / alpha | 面向 In-Place Pod Resize 的 scheduler preemption，把 resize 引发的资源竞争纳入调度处理。 |

设计判断：preemption 正在从单 Pod 局部优化转向 workload/disruption-aware 决策。跟踪时要同时看 victim 选择、PDB/可用性、异步执行和 PodGroup 语义。

### 5. Workload / PodGroup / gang

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `4671-gang-scheduling` | implementable / beta / v1.37 | 用 Workload/PodGroup 表达一组 Pod 的整体调度。核心问题是 minCount、组装等待、整体可行性、抢占、binding 顺序和失败回退。 |
| `5710-workload-aware-preemption` | implementable / beta / v1.37 | 与 gang scheduling 强耦合，避免先抢占再发现整个 workload 仍不可运行。 |
| `5832-decouple-podgroup-api` | implementable / alpha | 将 PodGroup API 从特定 workload API 中解耦，为通用 workload scheduling 做 API 基础。 |
| `6012-composite-podgroup-api` | implementable / alpha | 支撑组合 PodGroup，处理多组件 workload 的整体调度表达。 |
| `6089-was-controller-apis` | implementable / alpha | Workload Aware Scheduling controller API，把 workload-aware 状态从 scheduler 内部扩展到控制器接口。 |
| `583-coscheduling` | provisional | 历史 coscheduling 方案，适合作为 gang scheduling 的前身对照。 |

设计判断：AI/HPC/batch 平台要重点跟踪这条线。它决定 Kubernetes 是否能原生表达“要么一组 Pod 一起运行，要么先不要占资源”的语义。

### 6. DRA / device-aware scheduling

代表 KEP：

| KEP | 状态 | 方案要点 |
|---|---|---|
| `5007-device-attach-before-pod-scheduled` | implementable / beta | 设备绑定条件进入调度路径，避免 Pod 绑定后才发现设备准备失败。 |
| `5075-dra-consumable-capacity` | implementable / beta / v1.37 | DRA 设备不仅是离散实例，也可能有可消费容量；调度需要理解容量消耗和剩余量。 |
| `5941-dra-shared-consumable-capacity` | implementable / alpha | 多个相关设备共享同一 consumable capacity，适合复杂加速器或拓扑共享资源。 |
| `5517-dra-node-allocatable-resources` | implementable / alpha | 把 DRA 相关 node allocatable 资源暴露给调度和容量推理。 |
| `5729-resourceclaim-support-for-workloads` | implementable / beta | ResourceClaim 从单 Pod 扩展到 workload 级别，和 PodGroup/gang 产生交叉。 |
| `6080-dra-derived-attributes` | provisional / alpha | 用表达式从设备属性派生拓扑/匹配属性，解决不同 driver 发布属性不完全一致的问题。 |
| `5963-device-compatibility-groups` | implementable / alpha | 表达设备兼容组，让多设备组合调度不只依赖简单属性相等。 |
| `5055-dra-device-taints-and-tolerations` | implementable / stable | 将 taints/tolerations 语义扩展到设备层。 |
| `4815-dra-partitionable-devices` | implementable / beta | 支撑可分区设备，例如可切分的 GPU/MIG-like 资源。 |
| `4816-dra-prioritized-list` | implementable / stable | 设备请求支持优先级备选列表，改善多种设备配置可接受的场景。 |

设计判断：DRA 是 scheduling/node/autoscaling 三方交叉最密集的线。调度侧要关注 filter/score/reserve；node 侧要关注 NodePrepare/ResourceClaim status；autoscaling 侧要关注是否能推理新增节点后的设备可用性。

## SIG Autoscaling 设计方案

### 1. HPA API / behavior

| KEP | 状态 | 方案要点 |
|---|---|---|
| `2702-graduate-hpa-api-to-GA` | implemented / stable | HPA v2 API 稳定化，是多指标和 behavior 的承载面。 |
| `853-configurable-hpa-scale-velocity` | implemented / stable | 用 `behavior.scaleUp/scaleDown`、policies、selectPolicy、stabilizationWindowSeconds 表达扩缩速度。核心是从硬编码全局行为转向 workload 级策略。 |
| `4951-configurable-hpa-tolerance` | implementable / stable / v1.37 | per-HPA 或 per-direction tolerance，解决统一 10% 容忍度对大规模和敏感 workload 都太粗的问题。 |

设计判断：HPA 设计不只是算法，更是 API 表达能力。后续追踪应看新字段是否真正能被用户以 workload 粒度配置，并且是否有清晰 rollback 语义。

### 2. Metrics / target selection

| KEP | 状态 | 方案要点 |
|---|---|---|
| `117-hpa-metrics-specificity` | implemented / stable | custom/external metrics 增加 label selector，避免为了 HPA 改造整个指标管道。 |
| `1610-container-resource-autoscaling` | implemented / stable | HPA 可针对单个 container 的 CPU/memory，而不是 Pod 总和。解决主容器和 sidecar 资源变化不一致时的错误扩缩。 |
| `5325-hpa-pod-selection-accuracy` | implementable / v1.35 | 通过更准确的 Pod selection strategy 减少 label selector 匹配到非目标 Pod 的风险。 |

设计判断：metrics 线要看“指标是否代表真正 target”。对 sidecar-heavy workload、operator 生成 Pod、跨 owner selector 的场景，Pod 选择和 container-level metrics 比算法本身更关键。

### 3. Scale from zero / metrics failure

| KEP | 状态 | 方案要点 |
|---|---|---|
| `2021-scale-from-zero` | implementable / beta / v1.37 | 让 object/external metrics 支持从 0 副本启动。关键前提是无 Pod 时仍可读到外部业务信号。 |
| `5679-external-metric-fallback` | implementable / alpha / v1.36 | 外部指标获取失败时允许 fallback，避免 metrics adapter 或外部系统短暂失败导致错误扩缩。 |

设计判断：这条线直接影响事件驱动和队列驱动 workload。追踪时要记录 fallback 是保守维持、默认值、还是业务指定值，以及失败信号如何暴露给用户。

### 4. Cluster Autoscaler integration

| KEP | 状态 | 方案要点 |
|---|---|---|
| `5030-attach-limit-autoscaler` | implementable / beta / v1.37 | 将 CSI Volume attach limit 纳入 Cluster Autoscaler 推理，避免新增节点后仍因挂载上限无法调度。 |

设计判断：autoscaling 不只有 HPA。Cluster Autoscaler/Karpenter 需要模拟 scheduling 结果；DRA、volume attach、topology 和 PodGroup 都会让“加节点是否有用”变复杂。

## SIG Node 设计方案

### 1. kubelet / CRI / runtime boundary

| KEP | 状态 | 方案要点 |
|---|---|---|
| `2040-kubelet-cri` | implementable / beta | kubelet 运行时接口收敛到 CRI，是 dockershim 移除和多 runtime 支撑的前提。 |
| `2221-remove-dockershim` | implemented / stable | 移除 dockershim，把 runtime 支撑交给 CRI 实现，明确 kubelet/runtime 责任边界。 |
| `585-runtime-class` | implemented / stable | 用 RuntimeClass 把 runtime handler 选择暴露成 Pod 级 API。 |
| `4216-image-pull-per-runtime-class` | implementable / alpha | 镜像拉取按 runtime class 区分，适合 sandboxed runtime 或特殊 runtime 镜像链路。 |
| `2371-cri-pod-container-stats` | implementable / beta / v1.37 | 从 cAdvisor 依赖转向 CRI 完整 Pod/Container stats，是 metrics 和 autoscaling 的基础。 |
| `5825-cri-pagination` | implementable / alpha | CRI list streaming/pagination，面向大规模节点 runtime API 性能。 |
| `4033-group-driver-detection-over-cri` | implemented / stable | 通过 CRI 发现 cgroup driver，减少 kubelet/runtime 配置不一致。 |

设计判断：node 侧 runtime 线的核心是 kubelet 不再绑定 Docker 或 cAdvisor 具体实现，而是通过 CRI/RuntimeClass/stats API 形成可替换边界。

### 2. CPU / memory / topology managers

| KEP | 状态 | 方案要点 |
|---|---|---|
| `3570-cpumanager` | implemented / stable | kubelet CPU Manager 管理 cpuset 分配，面向 Guaranteed QoS 和性能敏感 workload。 |
| `1769-memory-manager` | implemented / stable | Memory Manager 通过 hint protocol 与 Topology Manager 协作，管理 NUMA/hugepages/Guaranteed memory。 |
| `693-topology-manager` | implemented / stable | 汇总 CPU/Memory/Device 等 hint provider 的 NUMA affinity，为本地资源对齐提供统一决策。 |
| `3545-improved-multi-numa-alignment` | implemented / stable | 改善多 NUMA 对齐，支撑更复杂机器拓扑。 |
| `2902-cpumanager-distribute-cpus-policy-option` | implementable / beta | CPUManager 支持跨 NUMA 分散 CPU，而不是总是 pack。 |
| `4540-strict-cpu-reservation` | implemented / stable | 严格限制 reservedSystemCPUs 给系统 daemon/interrupt，保护 workload CPU 隔离。 |
| `4800-cpumanager-split-uncorecache` | implementable / stable | CPU Manager 感知 uncore cache 拓扑，进一步细化性能隔离。 |
| `5526-pod-level-resource-managers` | implementable / beta / v1.37 | 资源管理从 container 级向 Pod 级演进，适配 Pod-level resources。 |

设计判断：这条线是性能型 Kubernetes 的底座。追踪时要记录它与 scheduler 拓扑、DRA numaNode、Node Feature Discovery 和 GPU/NIC locality 的关系。

### 3. Pod resources / resize

| KEP | 状态 | 方案要点 |
|---|---|---|
| `1287-in-place-update-pod-resources` | implemented / stable | Pod resource requests/limits 可原地更新，用 desired/actual resource status 和 CRI UpdateContainerResources 替代“改资源必须重建 Pod”。 |
| `5419-pod-level-resources-in-place-resize` | implementable / beta | 将 in-place resize 扩展到 Pod-level resources。 |
| `2837-pod-level-resource-spec` | implementable / stable | Pod 级资源规格，改变资源请求从 container sum 到 Pod envelope 的表达方式。 |
| `5554-in-place-update-pod-resources-alongside-static-cpu-manager-policy` | implementable / alpha | in-place resize 和 static CPU Manager policy 的交叉问题。 |
| `6122-configurable-scaling-delay-with-pod-resource-exposure` | implementable / alpha | Pod resource exposure 后的 scaling delay 可配置，连接 node 资源变化和 autoscaling 反馈延迟。 |

设计判断：resize 线是 scheduler/autoscaling/node 的交叉点。它不仅是 kubelet 能不能改 cgroup，还涉及 quota、QoS class、scheduler 可行性、preemption 和 HPA/VPA 反馈。

### 4. DRA / device plugin / CDI

| KEP | 状态 | 方案要点 |
|---|---|---|
| `3573-device-plugin` | implemented / stable | 传统设备插件模型：device plugin 通过 gRPC 注册设备，kubelet Allocate 后注入 container。 |
| `4009-add-cdi-devices-to-device-plugin-api` | implemented / stable | device plugin API 支持 CDI devices，把设备注入从 runtime-specific flags 转为标准 CDI spec。 |
| `4381-dra-structured-parameters` | implemented / stable | DRA structured parameters 成为 DRA 主线，替代 `3063` opaque control-plane negotiation 路线，使 scheduler/autoscaler 能理解设备可用性。 |
| `3063-dynamic-resource-allocation` | withdrawn | 早期 DRA with control-plane controller，因 Cluster Autoscaler 无法推理 opaque driver allocation、scheduler/driver 通过 apiserver 往返复杂而撤回。 |
| `4817-resource-claim-device-status` | implementable / stable | ResourceClaim status 暴露设备状态，可能包含网络接口等标准化数据。 |
| `5304-dra-attributes-downward-api` | implementable / beta | DRA device attributes 通过 Downward API 暴露给 Pod。 |
| `5677-dra-resource-availability-visibility` | implementable / alpha | 暴露 DRA resource availability，让用户和控制器能理解资源为什么不可用。 |
| `5945-dra-optional-node-preparation` | implementable / alpha | DRA NodePrepare 可选化，适合不需要节点准备的设备或轻量资源。 |
| `6072-dra-standard-numanode` | implementable / stable | DRA 标准化 `numaNode` 设备属性，连接 DRA 和 Topology Manager。 |

设计判断：DRA 追踪必须同时看 `sig-node` 和 `sig-scheduling`。`3063` 到 `4381` 的路线变化是关键设计教训：如果 Kubernetes 不能理解资源参数，调度和 autoscaling 就无法可靠推理。

### 5. Pod lifecycle / probes / sidecars

| KEP | 状态 | 方案要点 |
|---|---|---|
| `753-sidecar-containers` | implemented / stable | Sidecar 作为特殊 initContainer 语义，解决启动顺序、就绪、终止顺序、Job 完成和资源计算问题。 |
| `277-ephemeral-containers` | implemented / stable | debug container 进入 Pod 生命周期，用于线上排障而不改变常规 container spec。 |
| `2000-graceful-node-shutdown` | implementable / beta | 节点关机时 kubelet 按优雅终止流程处理 Pod。 |
| `2712-pod-priority-based-graceful-node-shutdown` | implementable / beta | 节点关机时按 Pod priority 分配关机顺序和时间。 |
| `5307-container-restart-policy` | implementable / beta | Container 级 restart rules，细化 Pod 内不同容器的重启语义。 |
| `4438-container-restart-termination` | implementable / alpha | Pod 终止期间 sidecar restart 行为，解决 sidecar termination 的边界条件。 |
| `4603-tune-crashloopbackoff` | implementable / alpha | CrashLoopBackOff 参数可调，改善不同 workload 的失败重试体验。 |
| `4939-grpc-probe-with-tls` | implementable / alpha | gRPC probe 支持 TLS，提升 probe 安全性。 |
| `5999-h2c-container-probes` | implementable / alpha | HTTP/2 cleartext probe 支持，适配更多应用协议。 |

设计判断：Pod lifecycle 线的设计难点是“API 语义看似小，实际影响 scheduler、Job controller、endpoint readiness、resource accounting 和 rollback”。

### 6. Security / isolation

| KEP | 状态 | 方案要点 |
|---|---|---|
| `135-seccomp` | implemented / stable | seccomp 支撑进入 Kubernetes。 |
| `2413-seccomp-by-default` | implementable / stable | 默认启用 seccomp profile，把安全默认值下沉到节点执行层。 |
| `127-user-namespaces` | implemented / stable | Pod 支持 user namespace，降低容器 root 与宿主 root 绑定风险。 |
| `2033-kubelet-in-userns-aka-rootless` | implementable / beta / v1.37 | kubelet rootless mode，进一步降低节点组件权限。 |
| `5607-hostnetwork-userns` | implementable / alpha | HostNetwork Pod 使用 user namespaces，处理网络特权和用户隔离交叉。 |
| `1898-hardened-exec` | implementable / alpha | 加固 kubelet exec endpoint，防 SSRF/代理滥用。 |
| `2862-fine-grained-kubelet-authz` | implementable / stable | kubelet API 细粒度授权，减少节点 API 面的权限过宽。 |
| `2254-cgroup-v2` | implementable / stable | cgroup v2 成为资源隔离基础。 |
| `5573-remove-cgroup-v1` | implementable / beta | 移除 cgroup v1，清理旧资源隔离路径。 |

设计判断：node security 不是单一 admission policy，而是 kubelet API、runtime、namespace、cgroup、exec/attach/probe 多条路径的组合。

### 7. Observability / node health

| KEP | 状态 | 方案要点 |
|---|---|---|
| `589-efficient-node-heartbeats` | implemented / stable | 降低 node heartbeat 成本，提高大规模集群节点状态同步效率。 |
| `727-resource-metrics-endpoint` | implemented / stable | kubelet resource metrics endpoint，是 [[metrics-server]] 和资源观测基础。 |
| `4205-psi-metric` | implemented / stable | 暴露 Pressure Stall Information，补足 CPU/memory/io pressure 信号。 |
| `5394-psi-node-conditions` | implementable / alpha | 将 PSI 上升为 Node Conditions，便于控制面自动化响应。 |
| `4680-add-resource-health-to-pod-status` | implementable / beta | Device Plugin / DRA 资源健康进入 Pod status，帮助用户理解设备异常。 |
| `5067-pod-generation` | implemented / stable | Pod generation 帮助区分 spec/status 同步代际。 |
| `5328-node-declared-features` | implementable / stable | Node 声明 features，和 [[node-feature-discovery]] 类项目形成对照。 |

设计判断：node observability 线要服务上层 scheduler/autoscaler/controller，而不只是给人看 metrics。PSI、resource health、Pod generation 都是控制面反馈闭环的一部分。

## 跨 SIG 设计链

| 设计链 | 关联 KEP | 为什么要联动追踪 |
|---|---|---|
| DRA structured parameters | `sig-node/4381`, `sig-node/3063`, `sig-scheduling/5007`, `5075`, `5517`, `6080`, `5963`, `sig-autoscaling/5030` | DRA 只有在 scheduler/autoscaler 能理解参数时才可生产化；opaque driver 协商路线已经被撤回。 |
| Workload/gang scheduling | `sig-scheduling/4671`, `5710`, `5832`, `6012`, `6089`, `sig-node/1287` | AI/HPC/batch 要求整组 Pod 语义，且 resize/preemption 会改变整组可行性。 |
| HPA metrics correctness | `sig-autoscaling/117`, `1610`, `5325`, `sig-node/727`, `2371`, `4205` | HPA 正确性依赖 node metrics、CRI stats、Pod selection 和指标 adapter。 |
| Topology-aware placement | `sig-scheduling/895`, `5732`, `sig-node/693`, `1769`, `6072`, `4742` | 拓扑从 zone/node spread 下沉到 NUMA/device，再通过 Downward API 暴露给 workload。 |
| In-place resource changes | `sig-node/1287`, `5419`, `5554`, `sig-scheduling/5836`, `sig-node/6122` | 资源从 immutable spec 变成 desired/actual 状态后，scheduler、kubelet、autoscaler 都要处理延迟和冲突。 |

## 当前 P0 跟踪清单

| 方向 | KEP | 当前状态 | 下一步追踪 |
|---|---|---|---|
| Gang / workload scheduling | `4671`, `5710`, `6012`, `6089` | v1.37 beta/alpha 活跃 | 跟 `GenericWorkload` feature gate、PodGroup API 是否稳定、与 Kueue/JobSet/LWS 的边界。 |
| DRA scheduling | `5075`, `5517`, `5941`, `5963`, `6080` | v1.37 beta/alpha/provisional | 跟 ResourceSlice/ResourceClaim API、scheduler perf、Cluster Autoscaler/Karpenter 推理能力。 |
| HPA behavior | `4951`, `2021`, `5679`, `5325` | v1.35-v1.37 活跃 | 跟 HPA API 字段是否进入 stable、metrics adapter failure 行为、scale from zero 约束。 |
| Node DRA/device | `4381`, `4817`, `5304`, `5677`, `5945`, `6072` | stable + v1.37 alpha | 跟 driver 实现、CDI、device health status、NUMA 属性标准化。 |
| Pod resources / resize | `1287`, `5419`, `5526`, `5554`, `6122`, `5836` | stable + v1.37 alpha/beta | 跟 in-place resize 的 scheduler preemption、Pod-level resources、static CPU manager。 |
| Node observability | `2371`, `4205`, `5394`, `4680`, `5328` | v1.36-v1.37 活跃 | 跟 CRI stats 替代 cAdvisor、PSI condition、resource health status。 |

## 后续维护规则

1. 新 KEP 先进入 [[kubernetes-keps-design-tracking]] 的 SIG 表，再决定是否需要单独源摘要。
2. 每个 KEP 至少记录：`KEP ID`、`目录`、`分类`、`status/stage/milestone`、`设计方案一句话`、`追踪优先级`。
3. 如果某个 KEP 改变跨 SIG 设计链，例如 DRA、PodGroup、in-place resize、metrics pipeline，要同步更新本页的“跨 SIG 设计链”。
4. 如果某个 KEP 从 alpha/beta 到 stable，补充 graduation 条件、metrics、feature gates 和 rollback 结论。
5. 第二轮应读取 `prod-readiness/sig-*/*.yaml`，把每个 P0/P1 KEP 的 production readiness 信息补到 tracking 表。
