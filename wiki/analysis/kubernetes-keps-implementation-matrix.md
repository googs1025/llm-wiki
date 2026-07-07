---
title: Kubernetes KEP Implementation Matrix
tags: [analysis, kubernetes, kep, implementation, feature-gates, sig-scheduling, sig-autoscaling, sig-node]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps]
related: [[kubernetes]], [[kubernetes-keps-feature-coverage]], [[kubernetes-keps-design-tracking]], [[kubernetes-scheduler-core-design]], [[kubernetes-workload-gang-scheduling-design]], [[kubernetes-dra-design-deep-dive]], [[kubernetes-hpa-autoscaling-design]], [[kubernetes-in-place-pod-resize-design]], [[kubernetes-node-runtime-observability-security-design]]
---

# Kubernetes KEP Implementation Matrix

这页补齐 “每个重要 KEP 到底有没有实现、现在是 alpha / beta / GA、关键 feature gate 是什么、核心实现或设计是什么”。它和 [[kubernetes-keps-feature-coverage]] 的关系是：覆盖矩阵按 feature group 合并阅读，本页按 KEP 逐项追踪实现状态。

## 状态判读

| 字段 | 含义 |
|---|---|
| `implemented + stable` | KEP metadata 已标实现，并且成熟度是 stable；可视为已实现 / GA。 |
| `implementable + stable` | KEP 已可实现，目标成熟度为 stable；通常表示 GA 设计线已完成或进入 GA 目标，但 metadata 还未改成 `implemented`。 |
| `implementable + beta` | 设计可实现，处于 beta；默认可试用但仍要关注 feature gate、升级和指标。 |
| `implementable + alpha` | 设计可实现但仍是 alpha；生产采用需要明确开关、回滚和兼容性风险。 |
| `provisional` | 设计仍在早期，不能按落地能力依赖。 |
| `withdrawn / removed` | 设计已撤回或移除，只作为历史对照。 |

## P0 Landmark KEPs

这些是当前最重要、最应该逐个追踪的 KEP。`著名度` 不是社区 star，而是这里的阅读优先级：是否改变核心 API、是否跨 SIG、是否影响调度/弹性/节点生产路径。

| KEP | SIG | 著名度 | 状态 | Alpha / Beta / GA | Feature gate | 关键实现 / 设计 |
|---|---|---|---|---|---|---|
| `4671-gang-scheduling` | scheduling | Landmark | `implementable / beta` | v1.35 / v1.37 / v1.38 | `GenericWorkload` | 引入 `Workload` / `PodGroup`，scheduler 以组为单位做准入、permit、binding 和失败回退。 |
| `5710-workload-aware-preemption` | scheduling | Landmark | `implementable / beta` | v1.36 / v1.37 / v1.39 | `GenericWorkload` | 抢占从 Pod 级扩展到 PodGroup / workload 级，避免抢占后仍不能整体运行。 |
| `6012-composite-podgroup-api` | scheduling | Important | `implementable / alpha` | v1.37 / v1.38 / v1.40 | `CompositePodGroup` | 表达多组件 workload 的组合 PodGroup，是 JobSet/LWS/训练任务接入 gang 语义的 API 补充。 |
| `6089-was-controller-apis` | scheduling | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `WorkloadWithJob` | 给 controller 提供 workload-aware scheduling building blocks，而不是强制所有 workload 使用同一顶层 API。 |
| `6132-prequeueing-hints` | scheduling | Important | `implementable / beta` | - / v1.37 / v1.39 | `SchedulerPreQueueingHints` | 在 Pod 入 activeQ 前判断事件是否值得唤醒，降低 DRA/gang/resize 等等待型场景的无效重试。 |
| `5598-opportunistic-batching` | scheduling | Important | `implementable / beta` | - / v1.35 / v1.38 | `OpportunisticBatching` | scheduler 批量处理可调度机会，提高大规模集群吞吐。 |
| `4381-dra-structured-parameters` | node + scheduling + autoscaling | Landmark | `implemented / stable` | v1.30 / v1.32 / v1.34 | `DynamicResourceAllocation`, `DRASchedulerFilterTimeout` | DRA 主线：`ResourceSlice`/`ResourceClaim` 结构化设备参数，让 scheduler/autoscaler 可推理设备。 |
| `3063-dynamic-resource-allocation` | node | Historical | `withdrawn / alpha` | v1.26 / - / - | `DynamicResourceAllocation`, `DRAControlPlaneController` | 早期 opaque DRA controller allocation 路线，已撤回；主要价值是解释为什么转向 structured parameters。 |
| `5075-dra-consumable-capacity` | scheduling | Landmark | `implementable / beta` | v1.34 / v1.36 / v1.38 | `DRAConsumableCapacity` | 设备不再只是离散实例，也可以有可消费 capacity，例如 GPU memory、带宽、license。 |
| `5517-dra-node-allocatable-resources` | scheduling | Important | `implementable / alpha` | v1.36 / v1.38 / v1.39 | `DRANodeAllocatableResources` | 暴露 DRA node allocatable，给调度和容量推理提供节点级库存信号。 |
| `5729-resourceclaim-support-for-workloads` | scheduling | Important | `implementable / beta` | v1.36 / v1.37 / - | `DRAWorkloadResourceClaims` | ResourceClaim 支持 workload 级使用，连接 DRA 和 PodGroup/gang scheduling。 |
| `5941-dra-shared-consumable-capacity` | scheduling | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `DRASharedConsumableCapacity` | 多个 logical device 共享同一个 capacity pool，处理共享 buffer、memory 或 fabric bandwidth。 |
| `5963-device-compatibility-groups` | scheduling | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `DRADeviceCompatibilityGroups` | 表达多个设备必须兼容或来自同一组合集合，适合多卡/多 NIC 配对。 |
| `6080-dra-derived-attributes` | scheduling | Watch | `provisional / alpha` | v1.37 / v1.38 / v1.40 | `DRADerivedAttributes` | 从 driver 属性派生标准化匹配属性；还不是稳定实现主线。 |
| `4817-resource-claim-device-status` | node | Important | `implementable / stable` | v1.32 / v1.33 / v1.37 | `DRAResourceClaimDeviceStatus` | 将分配到的设备信息写入 ResourceClaim status，给用户和控制器可观测结果。 |
| `5304-dra-attributes-downward-api` | node | Important | `implementable / beta` | v1.36 / v1.37 / v1.38 | `NA` | 把 DRA device attributes 暴露给 Pod，方便 workload 发现自己拿到的设备属性。 |
| `5677-dra-resource-availability-visibility` | node | Important | `implementable / alpha` | v1.36 / - / - | `DRAResourcePoolStatus` | 暴露资源池可用性，减少用户只看到 claim pending 却不知道设备库存原因。 |
| `5945-dra-optional-node-preparation` | node | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `DRAOptionalNodePreparation` | 允许某些 DRA 场景跳过强制 NodePrepare，降低轻量设备或无需节点准备的路径成本。 |
| `6072-dra-standard-numanode` | node | Important | `implementable / stable` | - / - / v1.37 | - | 标准化 DRA `numaNode` 属性，连接 DRA 和 Topology Manager / NUMA-aware scheduling。 |
| `4951-configurable-hpa-tolerance` | autoscaling | Important | `implementable / stable` | v1.33 / v1.35 / v1.37 | `HPAConfigurableTolerance` | 把 HPA tolerance 从全局参数下放到 HPA scaleUp/scaleDown 规则。 |
| `1610-container-resource-autoscaling` | autoscaling | Important | `implemented / stable` | v1.20 / v1.27 / v1.30 | `HPAContainerMetrics` | HPA 可按指定 container 的 CPU/memory 扩缩，避免 sidecar 稀释主容器指标。 |
| `5325-hpa-pod-selection-accuracy` | autoscaling | Important | `implementable / alpha` | v1.35 / v1.36 / v1.37 | `HPASelectionStrategy` | HPA 可按 owner reference 过滤 Pod，避免 label selector 误选其他 workload。 |
| `2021-scale-from-zero` | autoscaling | Landmark | `implementable / beta` | v1.16 / v1.37 / x.y | `HPAScaleToZero` | HPA 基于 object/external metrics 支持 0 副本恢复，用 condition 区分自动缩零与用户暂停。 |
| `5679-external-metric-fallback` | autoscaling | Important | `implementable / alpha` | v1.36 / v1.37 / v1.38 | `HPAExternalMetricFallback` | external metric 连续失败时使用固定 fallback replicas，并进入 HPA 多指标 max 合并。 |
| `5030-attach-limit-autoscaler` | autoscaling | Important | `implementable / beta` | v1.35 / v1.37 / v1.38 | `VolumeLimitScaling` | Cluster Autoscaler 模拟 CSI volume attach limit，避免加了节点仍不可调度。 |
| `1287-in-place-update-pod-resources` | node | Landmark | `implemented / stable` | v1.27 / v1.33 / v1.35 | `InPlacePodVerticalScaling`, `InPlacePodVerticalScalingAllocatedStatus` | Pod `/resize` subresource 与 desired/allocated/actual 状态模型，支持 CPU/memory 原地调整。 |
| `5419-pod-level-resources-in-place-resize` | node | Important | `implementable / beta` | v1.35 / v1.36 / - | `InPlacePodLevelResourcesVerticalScaling`, `PodLevelResources` | 将 in-place resize 扩展到 Pod-level resources。 |
| `5526-pod-level-resource-managers` | node | Important | `implementable / beta` | v1.36 / v1.37 / v1.39 | `PodLevelResources`, `PodLevelResourceManagers` | CPU/Memory/Topology Manager 从 container scope 扩展到 Pod scope。 |
| `5554-in-place-update-pod-resources-alongside-static-cpu-manager-policy` | node | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `InPlacePodVerticalScalingExclusiveCPUs` | 处理 static CPU Manager exclusive CPUs 下的原地 resize。 |
| `6122-configurable-scaling-delay-with-pod-resource-exposure` | node | Important | `implementable / alpha` | v1.37 / v1.39 / v1.40 | `DownwardAPIAssignedResources` 等 | 在收回 exclusive CPUs 前暴露资源变化并给应用准备窗口。 |
| `5836-scheduler-preemption-for-ippr` | scheduling | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `SchedulerPreemptionForPodResize` | scheduler 为 deferred in-place resize 在已绑定节点上触发抢占。 |
| `2371-cri-pod-container-stats` | node | Important | `implementable / beta` | v1.29 / v1.37 / - | `PodAndContainerStatsFromCRI` | kubelet stats 从 cAdvisor 迁往 CRI，影响 metrics-server/HPA 的输入可靠性。 |
| `5394-psi-node-conditions` | node | Important | `implementable / alpha` | v1.36 / - / - | `PSINodeCondition` | 将 PSI pressure 升级为 Node Conditions，便于调度、排障和自动化响应。 |
| `4680-add-resource-health-to-pod-status` | node | Important | `implementable / beta` | v1.31 / v1.36 / v1.37 | `ResourceHealthStatus` | Device Plugin / DRA 资源健康进入 Pod status。 |
| `2033-kubelet-in-userns-aka-rootless` | node | Important | `implementable / beta` | v1.22 / v1.37 / - | `KubeletInUserNamespace` | kubelet 以 user namespace/rootless 模式运行，降低节点控制面特权。 |
| `5607-hostnetwork-userns` | node | Important | `implementable / alpha` | v1.35 / - / - | `UserNamespacesHostNetworkSupport` | HostNetwork Pod 也可使用 user namespaces，补上高权限网络场景隔离。 |
| `4438-container-restart-termination` | node | Important | `implementable / alpha` | v1.37 / v1.38 / v1.39 | `SidecarsRestartableDuringPodTermination` | 明确 Pod 终止期间 sidecar 是否可 restart，修补 lifecycle 边界。 |
| `4563-eviction-request-api` | node | Important | `implementable / alpha` | v1.37 / - / - | `EvictionRequestAPI` | 给 eviction 请求更清晰的 API 表达。 |

## P1 Foundation KEPs

这些 KEP 是底座。它们不一定都需要单独长文，但阅读 P0 时经常要回到这里确认前提。

| KEP | SIG | 状态 | Alpha / Beta / GA | Feature gate | 关键实现 / 设计 |
|---|---|---|---|---|---|
| `624-scheduling-framework` | scheduling | `implemented / stable` | v1.16 / - / v1.19 | - | kube-scheduler extension points，后续 DRA、gang、queueing、preemption 都依赖它。 |
| `785-scheduler-component-config-api` | scheduling | `implemented / stable` | - / v1.19 / v1.25 | - | scheduler config 版本化。 |
| `1451-multi-scheduling-profiles` | scheduling | `implementable / beta` | v1.18 / v1.19 / v1.22 | - | 一个 scheduler 实例支持多个 profile。 |
| `3521-pod-scheduling-readiness` | scheduling | `implemented / stable` | v1.26 / v1.27 / v1.30 | `PodSchedulingReadiness` | scheduling gates 控制 Pod 何时进入调度。 |
| `4247-queueinghint` | scheduling | `implemented / stable` | v1.26 / v1.32 / v1.34 | `SchedulerQueueingHints` | plugin-specific requeue hint。 |
| `895-pod-topology-spread` | scheduling | `implemented / stable` | v1.16 / v1.18 / v1.19 | `EvenPodsSpread` | Pod 副本按 topology domain 分散。 |
| `3633-matchlabelkeys-to-podaffinity` | scheduling | `implemented / stable` | v1.29 / v1.31 / v1.33 | `MatchLabelKeysInPodAffinity` | affinity/anti-affinity 支持 matchLabelKeys / mismatchLabelKeys。 |
| `4832-async-preemption` | scheduling | `implementable / beta` | v1.32 / v1.33 / - | `SchedulerAsyncPreemption` | 抢占异步化，减少 scheduling cycle 阻塞。 |
| `5007-device-attach-before-pod-scheduled` | scheduling | `implementable / beta` | v1.34 / v1.36 / v1.37 | `DRADeviceBindingConditions` | 设备 attach / readiness 条件进入调度等待路径。 |
| `5055-dra-device-taints-and-tolerations` | scheduling | `implementable / stable` | v1.33 / v1.36 / v1.37 | `DRADeviceTaints`, `DRADeviceTaintRules` | 设备级 taints/tolerations。 |
| `4815-dra-partitionable-devices` | scheduling | `implementable / beta` | v1.33 / v1.36 / - | `DRAPartitionableDevices` | 动态或逻辑分区设备。 |
| `4816-dra-prioritized-list` | scheduling | `implementable / stable` | v1.33 / v1.34 / v1.36 | `DRAPrioritizedList` | 用户可表达设备请求的优先级备选列表。 |
| `5732-topology-aware-workload-scheduling` | scheduling | `implementable / beta` | v1.36 / v1.37 / v1.39 | `TopologyAwareWorkloadScheduling` | PodGroup / workload 级 topology placement。 |
| `5229-asynchronous-api-calls-during-scheduling` | scheduling | `implementable / beta` | - / v1.34 / - | `SchedulerAsyncAPICalls` | 调度期间 API 写操作异步化。 |
| `853-configurable-hpa-scale-velocity` | autoscaling | `implemented / stable` | - / - / - | - | HPA behavior policies、stabilization window、scale velocity。 |
| `2702-graduate-hpa-api-to-GA` | autoscaling | `implemented / stable` | - / - / v1.23 | - | HPA v2 API GA。 |
| `117-hpa-metrics-specificity` | autoscaling | `implemented / stable` | - / - / - | - | custom/external metrics label selector。 |
| `3570-cpumanager` | node | `implemented / stable` | v1.8 / v1.10 / v1.26 | `CPUManager` | Guaranteed workload 的 cpuset 分配。 |
| `1769-memory-manager` | node | `implemented / stable` | v1.21 / v1.22 / v1.32 | `MemoryManager` | NUMA-aware memory allocation。 |
| `693-topology-manager` | node | `implemented / stable` | v1.16 / v1.18 / v1.27 | `TopologyManager` | 汇总 CPU/memory/device hints。 |
| `2837-pod-level-resource-spec` | node | `implementable / stable` | v1.33 / v1.34 / v1.37 | `PodLevelResources` | Pod-level resource spec，是 pod-scope resource managers 的 API 前提。 |
| `3573-device-plugin` | node | `implemented / stable` | v1.8 / v1.10 / v1.26 | `DevicePlugins` | 传统设备插件 API。 |
| `4009-add-cdi-devices-to-device-plugin-api` | node | `implemented / stable` | v1.28 / v1.29 / v1.31 | `DevicePluginCDIDevices` | device plugin 返回 CDI devices。 |
| `3695-pod-resources-for-dra` | node | `implemented / stable` | v1.27 / v1.34 / v1.36 | `KubeletPodResourcesDynamicResource` | PodResources API 包含 DRA allocation。 |
| `2040-kubelet-cri` | node | `implementable / beta` | v1.5 / v1.23 / - | - | kubelet/runtime 通过 CRI 解耦。 |
| `2221-remove-dockershim` | node | `implemented / stable` | - / - / - | - | kubelet 移除内置 dockershim。 |
| `585-runtime-class` | node | `implemented / stable` | v1.12 / v1.14 / v1.20 | `RuntimeClass` | Pod 选择 runtime handler。 |
| `753-sidecar-containers` | node | `implemented / stable` | v1.28 / v1.29 / v1.33 | `SidecarContainers` | 用 restartable init container 表达 sidecar lifecycle。 |
| `127-user-namespaces` | node | `implemented / stable` | v1.25 / v1.35 / v1.36 | `UserNamespacesSupport` | Pod user namespace 隔离。 |
| `2413-seccomp-by-default` | node | `implementable / stable` | v1.22 / v1.25 / v1.27 | `SeccompDefault` | 默认启用 seccomp runtime default。 |
| `2862-fine-grained-kubelet-authz` | node | `implementable / stable` | v1.32 / v1.33 / v1.36 | `KubeletFineGrainedAuthz` | kubelet API 细粒度授权。 |
| `2254-cgroup-v2` | node | `implementable / stable` | v1.18 / v1.22 / v1.25 | - | cgroup v2 支撑现代资源控制。 |
| `727-resource-metrics-endpoint` | node | `implemented / stable` | v1.14 / - / v1.29 | - | kubelet `/metrics/resource` 稳定入口。 |
| `4205-psi-metric` | node | `implemented / stable` | v1.33 / v1.34 / v1.36 | `KubeletPSI` | kubelet 暴露 PSI metrics。 |
| `5328-node-declared-features` | node | `implementable / stable` | v1.35 / v1.36 / v1.37 | `NodeDeclaredFeatures` | 节点声明能力，供调度/控制器使用。 |

## 设计阅读索引

| 想理解的问题 | 先读 |
|---|---|
| 为什么 gang scheduling 不是普通 Pod 队列插件 | [[kubernetes-workload-gang-scheduling-design]] |
| 为什么 DRA 需要 structured parameters | [[kubernetes-dra-design-deep-dive]] |
| HPA 为什么需要 tolerance、owner filtering、fallback | [[kubernetes-hpa-autoscaling-design]] |
| `/resize` 为什么要拆 desired/allocated/actual | [[kubernetes-in-place-pod-resize-design]] |
| kubelet/CRI/resource managers/安全/可观测如何连接 | [[kubernetes-node-runtime-observability-security-design]] |
| scheduler framework、queue、preemption 的底座 | [[kubernetes-scheduler-core-design]] |

## 后续追踪规则

1. 新 KEP 进入本页时，必须记录 `status`、`stage`、`latest-milestone`、Alpha/Beta/GA milestones 和 feature gate。
2. `implementable + stable` 不自动等同于 metadata 已标 `implemented`；需要继续看 KEP implementation history 和 release note。
3. `provisional` 和 `withdrawn` 不放入生产能力清单，只用于设计脉络解释。
4. 若一个 KEP 同时影响多个 SIG，例如 DRA 和 autoscaler，要在对应设计页互链并说明边界。
