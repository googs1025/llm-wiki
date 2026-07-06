---
title: Kubernetes KEPs Design Tracking
tags: [analysis, kubernetes, kep, design-tracking, sig-scheduling, sig-autoscaling, sig-node]
date: 2026-07-06
sources: [src-kubernetes-keps-design-tracking.md]
related: [[kubernetes]], [[src-kubernetes-keps-design-tracking]], [[kubernetes-dra]], [[kubernetes-workload-automation]], [[k8s-core-controller-map]], [[k8s-gpu-device-stack]], [[llm-d-kubernetes-sigs-candidate-map]]
---

# Kubernetes KEPs Design Tracking

这页是 KEP 设计方案追踪表，服务于后续长期更新。源摘要和设计脉络见 [[src-kubernetes-keps-design-tracking]]。

## 使用方式

- 先按 SIG 找到 KEP。
- 再看 `分类` 判断它属于哪条设计线。
- `优先级` 用于决定后续是否需要单独深挖：
  - `P0`：近期活跃、跨 SIG 影响大、或与 AI/HPC/GPU/平台工程强相关。
  - `P1`：稳定基础设计，适合作为背景知识或项目对照。
  - `P2`：历史、边缘或低频补充。

## SIG Scheduling

### P0 活跃设计线

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| workload/gang | `4671-gang-scheduling` | implementable / beta / v1.37 | 用 Workload/PodGroup 表达整组 Pod 调度，解决 minCount、组装、整体可行性、preemption、binding 和失败回退。 | P0 |
| workload/gang | `5710-workload-aware-preemption` | implementable / beta / v1.37 | 抢占从单 Pod 扩展到 workload 级，避免高优先级 gang 抢占后仍无法整体运行。 | P0 |
| workload/gang | `6012-composite-podgroup-api` | implementable / alpha / v1.37 | 表达组合 PodGroup，适合多组件 workload。 | P0 |
| workload/gang | `6089-was-controller-apis` | implementable / alpha / v1.37 | Workload Aware Scheduling controller API，给 controller 暴露 workload-aware 调度状态。 | P0 |
| queue | `6132-prequeueing-hints` | implementable / beta / v1.37 | 在 Pod 入 activeQ 前通过 hint 判断事件是否足以唤醒调度。 | P0 |
| queue | `5598-opportunistic-batching` | implementable / beta / v1.37 | 批量化调度机会，降低重复计算，提高吞吐。 | P0 |
| DRA scheduling | `5075-dra-consumable-capacity` | implementable / beta / v1.37 | DRA 支持可消费容量，不再只处理离散设备实例。 | P0 |
| DRA scheduling | `5517-dra-node-allocatable-resources` | implementable / alpha / v1.37 | 暴露 DRA node allocatable，支撑调度和容量推理。 | P0 |
| DRA scheduling | `5729-resourceclaim-support-for-workloads` | implementable / beta / v1.37 | ResourceClaim 支持 workload 级使用，和 PodGroup/gang 交叉。 | P0 |
| DRA scheduling | `5941-dra-shared-consumable-capacity` | implementable / alpha / v1.37 | 多设备共享同一 consumable capacity。 | P0 |
| DRA scheduling | `5963-device-compatibility-groups` | implementable / alpha / v1.37 | 设备兼容组，表达多设备组合约束。 | P0 |
| DRA scheduling | `6080-dra-derived-attributes` | provisional / alpha / v1.37 | 从设备属性派生拓扑/匹配属性，解决 driver 属性表达不一致。 | P0 |
| resize/preemption | `5836-scheduler-preemption-for-ippr` | implementable / alpha / v1.37 | scheduler 处理 in-place pod resize 引发的资源冲突和抢占。 | P0 |

### P1 基础设计线

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| framework | `624-scheduling-framework` | implemented / stable / v1.19 | scheduler plugin 扩展点体系，是后续所有调度 KEP 的底座。 | P1 |
| config | `785-scheduler-component-config-api` | implemented / stable / v1.25 | versioned scheduler ComponentConfig。 | P1 |
| config | `1451-multi-scheduling-profiles` | implementable / beta / v1.19 | 一个 scheduler 实例支持多个 profile。 | P1 |
| queue | `3521-pod-scheduling-readiness` | implemented / stable / v1.30 | scheduling gates 控制 Pod 是否进入调度。 | P1 |
| queue | `4247-queueinghint` | implemented / stable / v1.34 | plugin-specific QueueingHint，减少无效 requeue。 | P1 |
| queue | `5142-pop-backoffq-when-activeq-empty` | implementable / beta / v1.33 | activeQ 空时提前处理 backoffQ。 | P1 |
| queue | `5501-reflect-preenqueue-rejections-in-pod-status` | implementable / beta / v1.35 | PreEnqueue 拒绝原因进入 Pod status。 | P1 |
| topology | `895-pod-topology-spread` | implemented / stable / v1.19 | Pod 拓扑分布基础设计。 | P1 |
| topology | `1258-default-pod-topology-spread` | implementable / stable / v1.24 | 默认拓扑分布策略。 | P1 |
| topology | `3022-min-domains-in-pod-topology-spread` | implemented / stable / v1.30 | PodTopologySpread 最小 domain。 | P1 |
| topology | `3094-pod-topology-spread-considering-taints` | implemented / stable / v1.33 | skew 计算考虑 taints/tolerations。 | P1 |
| topology | `3243-respect-pod-topology-spread-after-rolling-upgrades` | implementable / beta / v1.34 | rolling upgrade 后继续尊重 spread。 | P1 |
| affinity | `2249-pod-affinity-namespace-selector` | implementable / stable / v1.24 | Pod affinity 支持 namespace selector。 | P1 |
| affinity | `3633-matchlabelkeys-to-podaffinity` | implemented / stable / v1.33 | affinity/anti-affinity 支持 matchLabelKeys。 | P1 |
| scoring | `2458-node-resource-score-strategy` | implementable / beta / v1.22 | 节点资源打分策略可配置。 | P1 |
| preemption | `4832-async-preemption` | implementable / beta / v1.33 | 异步化 preemption。 | P1 |
| preemption | `5278-nominated-node-name-for-expectation` | implementable / beta / v1.35 | 改善 nominated node 期望表达。 | P1 |
| DRA scheduling | `5007-device-attach-before-pod-scheduled` | implementable / beta / v1.36 | 设备绑定条件进入调度路径。 | P1 |
| DRA scheduling | `5004-dra-extended-resource` | implementable / stable / v1.37 | Extended resources 通过 DRA driver 处理。 | P1 |
| DRA scheduling | `5055-dra-device-taints-and-tolerations` | implementable / stable / v1.37 | 设备级 taints/tolerations。 | P1 |
| DRA scheduling | `4815-dra-partitionable-devices` | implementable / beta / v1.36 | 可分区设备。 | P1 |
| DRA scheduling | `4816-dra-prioritized-list` | implementable / stable / v1.36 | 设备请求优先级备选列表。 | P1 |
| DRA scheduling | `5234-dra-resourceslice-mixins` | implementable / alpha / v1.34 | ResourceSlice mixins。 | P1 |
| DRA scheduling | `5491-dra-list-types-for-attributes` | implementable / alpha / v1.37 | DRA 属性支持 list 类型。 | P1 |
| placement | `5732-topology-aware-workload-scheduling` | implementable / beta / v1.37 | workload 级拓扑感知调度。 | P1 |
| scheduler/API | `5229-asynchronous-api-calls-during-scheduling` | implementable / beta / v1.34 | 调度期间 API 调用异步化。 | P1 |

### P2 历史和补充

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| extender | `1819-scheduler-extender` | implemented / stable / v1.19 | HTTP extender 历史扩展路径。 | P2 |
| priority | `268-priority-preemption` | implementable / alpha | Priority/preemption 基础线。 | P2 |
| priority | `902-non-preempting-priorityclass` | implemented / stable / v1.24 | 高优先级但不抢占。 | P2 |
| preemption | `3280-guarantee-pdb-when-preemption-happens` | implementable / alpha / v1.27 | 抢占时保护 PDB。 | P2 |
| job | `2926-job-mutable-scheduling-directives` | implemented / stable / v1.27 | Job scheduling directives 可变。 | P2 |
| pod | `3838-pod-mutable-scheduling-directives` | implementable / stable / v1.30 | Pod scheduling directives 可变。 | P2 |
| taint | `382-taint-node-by-condition` | implemented / stable | Node condition taint。 | P2 |
| taint | `3902-decoupled-taint-manager` | implemented / stable / v1.34 | TaintManager 从 NodeLifecycleController 解耦。 | P2 |
| daemonset | `548-schedule-daemonset-pods` | implemented / stable | DaemonSet pods 交给 scheduler。 | P2 |
| quota | `986-resource-quota-scope-selectors` | implemented / stable | ResourceQuota scope selectors。 | P2 |
| quota | `2372-node-labels-quota` | provisional | 基于 node labels 的 ResourceQuota。 | P2 |
| score | `964-binpacking-priority` | implementable / alpha | RequestedToCapacityRatio 支持 extended resource binpacking。 | P2 |
| historical | `583-coscheduling` | provisional | gang scheduling 前身。 | P2 |
| historical | `5832-decouple-podgroup-api` | implementable / alpha / v1.36 | PodGroup API 解耦。 | P2 |
| config | `2891-simplified-config` | implementable / beta / v1.23 | scheduler config 简化。 | P2 |
| placement | `5471-enable-sla-based-scheduling` | implementable / alpha / v1.35 | threshold-based placement。 | P2 |
| DRA scheduling | `5027-dra-admin-controlled-device-attributes` | provisional / alpha / v1.33 | 管理员控制设备属性。 | P2 |

## SIG Autoscaling

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| HPA behavior | `4951-configurable-hpa-tolerance` | implementable / stable / v1.37 | per-HPA / per-direction tolerance，避免全局 10% 过粗。 | P0 |
| HPA behavior | `853-configurable-hpa-scale-velocity` | implemented / stable | HPA behavior policies、stabilization window、scale up/down velocity。 | P1 |
| HPA API | `2702-graduate-hpa-api-to-GA` | implemented / stable / v1.23 | HPA v2 API GA。 | P1 |
| metrics | `1610-container-resource-autoscaling` | implemented / stable / v1.30 | container-level resource metrics，解决 sidecar 稀释主容器指标。 | P0 |
| metrics | `117-hpa-metrics-specificity` | implemented / stable | custom/external metrics label selector。 | P1 |
| metrics | `5325-hpa-pod-selection-accuracy` | implementable / v1.35 | 更准确的 HPA Pod selection，避免读到非 target Pod 指标。 | P0 |
| scale from zero | `2021-scale-from-zero` | implementable / beta / v1.37 | HPA 基于 object/external metrics 从 0 副本启动。 | P0 |
| failure policy | `5679-external-metric-fallback` | implementable / alpha / v1.36 | 外部指标失败时 fallback，降低 metrics adapter 故障影响。 | P0 |
| cluster autoscaler | `5030-attach-limit-autoscaler` | implementable / beta / v1.37 | CSI volume attach limit 进入 Cluster Autoscaler 推理。 | P0 |

## SIG Node

### P0 活跃设计线

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| DRA/device | `4381-dra-structured-parameters` | implemented / stable / v1.35 | DRA structured parameters，取代 opaque allocation 路线，是 DRA 主线。 | P0 |
| DRA/device | `3063-dynamic-resource-allocation` | withdrawn / alpha / v1.32 | 早期 opaque DRA controller 协商方案，因 autoscaler 不可推理和 apiserver 往返复杂而撤回。 | P0 |
| DRA/device | `4817-resource-claim-device-status` | implementable / stable / v1.37 | ResourceClaim status 标准化设备信息。 | P0 |
| DRA/device | `5304-dra-attributes-downward-api` | implementable / beta / v1.37 | DRA device attributes 暴露到 Pod。 | P0 |
| DRA/device | `5677-dra-resource-availability-visibility` | implementable / alpha / v1.37 | DRA resource availability 可见性。 | P0 |
| DRA/device | `5945-dra-optional-node-preparation` | implementable / alpha / v1.37 | DRA NodePrepare 可选化。 | P0 |
| DRA/device | `6072-dra-standard-numanode` | implementable / stable / v1.37 | DRA 标准 `numaNode` 属性。 | P0 |
| resize/resources | `1287-in-place-update-pod-resources` | implemented / stable / v1.35 | Pod resource requests/limits 原地更新。 | P0 |
| resize/resources | `5419-pod-level-resources-in-place-resize` | implementable / beta / v1.36 | Pod-level resources 的 in-place resize。 | P0 |
| resize/resources | `5526-pod-level-resource-managers` | implementable / beta / v1.37 | Pod-level resource managers。 | P0 |
| resize/resources | `5554-in-place-update-pod-resources-alongside-static-cpu-manager-policy` | implementable / alpha / v1.37 | in-place resize 与 static CPU Manager policy 协作。 | P0 |
| resize/resources | `6122-configurable-scaling-delay-with-pod-resource-exposure` | implementable / alpha / v1.37 | Pod resource exposure 后的 scaling delay。 | P0 |
| observability | `2371-cri-pod-container-stats` | implementable / beta / v1.37 | CRI-full container/pod stats，减少 cAdvisor 依赖。 | P0 |
| observability | `5394-psi-node-conditions` | implementable / alpha / v1.36 | PSI 信号进入 Node Conditions。 | P0 |
| observability | `4680-add-resource-health-to-pod-status` | implementable / beta / v1.36 | Device Plugin/DRA resource health 进入 Pod status。 | P0 |
| security | `2033-kubelet-in-userns-aka-rootless` | implementable / beta / v1.37 | rootless kubelet。 | P0 |
| security | `5607-hostnetwork-userns` | implementable / alpha / v1.36 | HostNetwork Pod 使用 user namespaces。 | P0 |
| lifecycle | `4438-container-restart-termination` | implementable / alpha / v1.37 | Pod 终止期间 sidecar restart 行为。 | P0 |
| lifecycle | `4563-eviction-request-api` | implementable / alpha / v1.37 | EvictionRequest API。 | P0 |

### P1 基础设计线

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| resource manager | `3570-cpumanager` | implemented / stable / v1.26 | CPU Manager cpuset 分配。 | P1 |
| resource manager | `1769-memory-manager` | implemented / stable / v1.32 | Memory Manager 和 Topology Manager hint 协作。 | P1 |
| resource manager | `693-topology-manager` | implemented / stable / v1.27 | CPU/Memory/Device NUMA hint 聚合。 | P1 |
| resource manager | `3545-improved-multi-numa-alignment` | implemented / stable / v1.32 | 多 NUMA 对齐改进。 | P1 |
| resource manager | `2837-pod-level-resource-spec` | implementable / stable / v1.37 | Pod-level resource spec。 | P1 |
| resource manager | `2570-memory-qos` | implementable / beta / v1.37 | Memory QoS with cgroup v2。 | P1 |
| resource manager | `2902-cpumanager-distribute-cpus-policy-option` | implementable / beta / v1.33 | CPUManager 分散 CPU policy。 | P1 |
| resource manager | `4540-strict-cpu-reservation` | implemented / stable / v1.35 | strict CPU reservation。 | P1 |
| device | `3573-device-plugin` | implemented / stable / v1.26 | Device Plugin API。 | P1 |
| device | `4009-add-cdi-devices-to-device-plugin-api` | implemented / stable / v1.31 | Device Plugin 返回 CDI devices。 | P1 |
| device | `3695-pod-resources-for-dra` | implemented / stable / v1.36 | PodResources API 包含 DRA resources。 | P1 |
| runtime | `2040-kubelet-cri` | implementable / beta / v1.23 | kubelet CRI 支撑。 | P1 |
| runtime | `2221-remove-dockershim` | implemented / stable / v1.24 | 移除 dockershim。 | P1 |
| runtime | `585-runtime-class` | implemented / stable / v1.20 | RuntimeClass。 | P1 |
| runtime | `4033-group-driver-detection-over-cri` | implemented / stable / v1.37 | CRI 发现 cgroup driver。 | P1 |
| runtime | `5825-cri-pagination` | implementable / alpha / v1.36 | CRI list streaming/pagination。 | P1 |
| lifecycle | `753-sidecar-containers` | implemented / stable / v1.33 | Sidecar containers。 | P1 |
| lifecycle | `277-ephemeral-containers` | implemented / stable / v1.25 | Ephemeral containers。 | P1 |
| lifecycle | `2000-graceful-node-shutdown` | implementable / beta / v1.21 | Graceful node shutdown。 | P1 |
| lifecycle | `2712-pod-priority-based-graceful-node-shutdown` | implementable / beta / v1.24 | Priority-based graceful shutdown。 | P1 |
| lifecycle | `5307-container-restart-policy` | implementable / beta / v1.35 | Container restart policy。 | P1 |
| security | `127-user-namespaces` | implemented / stable / v1.36 | User namespaces。 | P1 |
| security | `2413-seccomp-by-default` | implementable / stable / v1.27 | Seccomp by default。 | P1 |
| security | `2862-fine-grained-kubelet-authz` | implementable / stable / v1.36 | Kubelet API 细粒度授权。 | P1 |
| security | `2254-cgroup-v2` | implementable / stable / v1.25 | cgroup v2。 | P1 |
| security | `5573-remove-cgroup-v1` | implementable / beta / v1.35 | 移除 cgroup v1。 | P1 |
| observability | `727-resource-metrics-endpoint` | implemented / stable / v1.29 | Kubelet resource metrics endpoint。 | P1 |
| observability | `4205-psi-metric` | implemented / stable / v1.36 | PSI metrics。 | P1 |
| observability | `5067-pod-generation` | implemented / stable / v1.35 | Pod generation。 | P1 |
| observability | `5328-node-declared-features` | implementable / stable / v1.37 | Node declared features。 | P1 |

### P2 补充清单

| 分类 | KEP | 状态 / 阶段 | 设计方案 | 优先级 |
|---|---|---|---|---|
| storage/resource | `1029-ephemeral-storage-quotas` | implementable / beta | Ephemeral storage quota。 | P2 |
| storage/resource | `1539-hugepages` | implemented / stable | HugePages。 | P2 |
| storage/resource | `1967-size-memory-backed-volumes` | implemented / stable | memory-backed volume size。 | P2 |
| storage/resource | `6030-dynamic-resize-of-memory-backed-volumes` | implementable / alpha | memory-backed volume 动态 resize。 | P2 |
| runtime | `1547-building-kubelet-without-docker` | implemented / stable | Dockerless kubelet。 | P2 |
| runtime | `4216-image-pull-per-runtime-class` | implementable / alpha | RuntimeClass 维度镜像拉取。 | P2 |
| runtime | `4191-split-image-filesystem` | implementable / beta | split image filesystem。 | P2 |
| runtime | `4210-max-image-gc-age` | implemented / stable | image GC max age。 | P2 |
| runtime | `5365-ImageVolume-with-image-digest` | implementable / alpha | ImageVolume with digest。 | P2 |
| probe/log | `2727-grpc-probe` | implemented / stable | gRPC probe。 | P2 |
| probe/log | `4939-grpc-probe-with-tls` | implementable / alpha | gRPC probe with TLS。 | P2 |
| probe/log | `5999-h2c-container-probes` | implementable / alpha | h2c probes。 | P2 |
| probe/log | `2411-cri-container-log-rotation` | implemented / stable | CRI log rotation。 | P2 |
| probe/log | `3288-separate-stdout-from-stderr` | implementable / alpha | stdout/stderr split stream。 | P2 |
| lifecycle | `3960-pod-lifecycle-sleep-action` | implemented / stable | PreStop sleep action。 | P2 |
| lifecycle | `4818-allow-zero-value-for-sleep-action-of-prestop-hook` | implemented / stable | PreStop sleep zero value。 | P2 |
| lifecycle | `4960-container-stop-signals` | implementable / beta | Container stop signals。 | P2 |
| lifecycle | `5532-restart-all-containers-on-container-exits` | implementable / beta | Restart all containers on exits。 | P2 |
| lifecycle | `5593-configure-the-max-crashloopbackoff-delay` | implementable / beta | CrashLoopBackOff max delay。 | P2 |
| security | `135-seccomp` | implemented / stable | Seccomp GA。 | P2 |
| security | `24-apparmor` | implementable / stable | AppArmor。 | P2 |
| security | `1898-hardened-exec` | implementable / alpha | Harden exec against SSRF。 | P2 |
| security | `213-run-as-group` | implemented / stable | RunAsGroup。 | P2 |
| security | `3619-supplemental-groups-policy` | implemented / stable | SupplementalGroups policy。 | P2 |
| security | `4265-proc-mount` | implementable / stable | ProcMount option。 | P2 |
| security | `5474-enable-writable-cgroups` | implementable / alpha | Writable cgroups。 | P2 |
| security | `5855-noexec-emptyDir` | implementable / alpha | emptyDir mount options。 | P2 |
| node status | `589-efficient-node-heartbeats` | implemented / stable | Efficient node heartbeat。 | P2 |
| node status | `3085-pod-conditions-for-starting-completition-of-sandbox-creation` | implementable / stable | Pod networking ready condition。 | P2 |
| node status | `5683-lifecycle-conditions` | implementable / alpha | Node lifecycle conditions。 | P2 |
| node feature | `793-node-os-arch-labels` | implementable / alpha | OS/arch labels GA。 | P2 |
| node feature | `4742-node-topology-downward-api` | implementable / beta | Node topology labels via Downward API。 | P2 |
| node config | `281-dynamic-kubelet-configuration` | removed | Dynamic kubelet config，已移除。 | P2 |
| node config | `3983-drop-in-configuration` | implemented / stable | kubelet drop-in config dir。 | P2 |
| node config | `4580-deprecate-kubelet-runonce` | provisional / alpha | Deprecate kubelet runonce。 | P2 |
| misc | `2400-node-swap` | implemented / stable | Node swap。 | P2 |
| misc | `2535-ensure-secret-pulled-images` | implementable / beta | Ensure secret pulled images。 | P2 |
| misc | `4639-oci-volume-source` | implemented / stable | OCI images as VolumeSource。 | P2 |
| misc | `5758-per-container-ulimits-configuration` | implementable / alpha | Per-container ulimits。 | P2 |
| misc | `5823-pod-level-checkpoint-restore` | implementable / alpha | Pod-level checkpoint/restore。 | P2 |
| misc | `6035-exec-session-identity` | implementable / alpha | Exec session identity propagation。 | P2 |
| misc | `6063-pod-pid-limit` | implementable / alpha | Per-Pod PID limit。 | P2 |

## 下一轮要补的数据

1. 从 `prod-readiness/sig-scheduling/*.yaml`、`prod-readiness/sig-autoscaling/*.yaml`、`prod-readiness/sig-node/*.yaml` 补 feature gates、metrics、rollback、scalability、upgrade/downgrade。
2. 对 P0 KEP 建单页深挖，优先顺序：`4671/5710`、`4381 + DRA scheduling KEPs`、`1287/5419/5836`、`4951/2021/5679`。
3. 增加 “版本视图”：按 `latest-milestone` 输出 v1.35、v1.36、v1.37 的活跃 KEP 列表。
4. 增加 “跨项目视图”：把 KEP 和 [[kueue]]、[[karpenter]]、[[scheduler-plugins]]、[[metrics-server]]、[[prometheus-adapter]]、[[node-feature-discovery]]、[[k8s-gpu-device-stack]] 对齐。
