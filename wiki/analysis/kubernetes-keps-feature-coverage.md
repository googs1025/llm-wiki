---
title: Kubernetes KEP Feature Coverage
tags: [analysis, kubernetes, kep, feature-coverage, sig-scheduling, sig-autoscaling, sig-node]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md]
related: [[kubernetes]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-keps-design-tracking]], [[kubernetes-scheduler-core-design]], [[kubernetes-workload-gang-scheduling-design]], [[kubernetes-dra-design-deep-dive]], [[kubernetes-hpa-autoscaling-design]], [[kubernetes-in-place-pod-resize-design]], [[kubernetes-node-runtime-observability-security-design]]
---

# Kubernetes KEP Feature Coverage

这页回答“到底整理了哪些 feature”。这里的 feature 不是逐个 feature gate，而是可长期追踪的 **合并设计组**：把同一设计问题下的多个 KEP 合并讲，避免后续按 KEP 编号碎片化。

## 覆盖原则

- **重要 feature 都要入组**：P0/P1 必须进入一个合并设计组；P2 只作为历史或边界补充。
- **相关设计合并讲**：例如 DRA 不拆成 node/scheduling 两套，而是合并为一个跨 SIG 设计组。
- **总表追踪，矩阵看状态，详解讲设计**：[[kubernetes-keps-design-tracking]] 保留完整 KEP 表；[[kubernetes-keps-implementation-matrix]] 追踪 Alpha/Beta/GA、是否实现和 feature gates；本页说明 feature 覆盖；详解页解释为什么这样设计。
- **优先覆盖影响生产系统的问题**：调度正确性、容量推理、autoscaling 可靠性、kubelet/runtime 边界、设备资源、可观测、安全和升级回滚。

## 当前合并设计组

| 设计组 | 覆盖 SIG | 代表 KEP | 详解页 | 覆盖状态 |
|---|---|---|---|---|
| Scheduler core / queue / placement | scheduling | `624`, `785`, `1451`, `3521`, `4247`, `6132`, `5598`, `895`, `1258`, `3022`, `3094`, `4832`, `5229` | [[kubernetes-scheduler-core-design]] | 已详解 |
| Workload / gang / workload-aware scheduling | scheduling | `4671`, `5710`, `6012`, `6089`, `5732`, `5832`, `583` | [[kubernetes-workload-gang-scheduling-design]] | 已详解 |
| DRA / device resource model | node + scheduling + autoscaling | `4381`, `3063`, `5007`, `5075`, `5517`, `5729`, `5941`, `5963`, `6080`, `5055`, `4815`, `4816`, `5030` | [[kubernetes-dra-design-deep-dive]] | 已详解 |
| HPA / metrics / scale from zero | autoscaling | `4951`, `853`, `2702`, `1610`, `117`, `5325`, `2021`, `5679`, `5030` | [[kubernetes-hpa-autoscaling-design]] | 已详解 |
| In-place Pod resize / resource mutation | node + scheduling | `1287`, `5419`, `5526`, `5554`, `6122`, `5836` | [[kubernetes-in-place-pod-resize-design]] | 已详解 |
| Node runtime / resource managers / observability / security | node | `2040`, `2221`, `585`, `3570`, `1769`, `693`, `753`, `127`, `2033`, `2371`, `4205`, `5394`, `4680`, `5328` | [[kubernetes-node-runtime-observability-security-design]] | 已详解 |

实现状态、Alpha/Beta/GA、feature gates 和关键实现路径统一见 [[kubernetes-keps-implementation-matrix]]。这里的 “已详解” 只表示已经有设计讲解页，不等于所有 KEP 都已经 GA。

## SIG Scheduling Feature 覆盖

| Feature | 合并到 | 重要性 |
|---|---|---|
| Scheduler Framework | [[kubernetes-scheduler-core-design]] | 所有后续调度 KEP 的 plugin 扩展底座。 |
| Scheduler ComponentConfig / profiles | [[kubernetes-scheduler-core-design]] | 让调度策略可配置、可多 profile 共存。 |
| Pod scheduling readiness / queueing hints / prequeueing hints | [[kubernetes-scheduler-core-design]] | 减少无效调度和 pending pod 抖动，是 DRA、gang、resize 场景的性能基础。 |
| Opportunistic batching / async API calls | [[kubernetes-scheduler-core-design]] | 面向大规模集群和高吞吐调度。 |
| Pod topology spread / affinity extension | [[kubernetes-scheduler-core-design]] | 普通 workload placement 的稳定基础。 |
| Async preemption / nominated node expectation | [[kubernetes-scheduler-core-design]] | 降低抢占阻塞和状态不一致。 |
| Workload / PodGroup / gang scheduling | [[kubernetes-workload-gang-scheduling-design]] | AI/HPC/batch 的核心调度语义。 |
| Workload-aware preemption | [[kubernetes-workload-gang-scheduling-design]] | 让抢占从单 Pod 扩展到 workload 级。 |
| Topology-aware workload scheduling | [[kubernetes-workload-gang-scheduling-design]] | 让一组 Pod 作为整体选择 topology placement。 |
| DRA-aware scheduling | [[kubernetes-dra-design-deep-dive]] | 让设备资源进入 scheduler 可推理路径。 |
| Scheduler preemption for in-place resize | [[kubernetes-in-place-pod-resize-design]] | 让已运行 Pod 的 resize 也能触发调度层资源重排。 |

## SIG Autoscaling Feature 覆盖

| Feature | 合并到 | 重要性 |
|---|---|---|
| HPA v2 / behavior policies | [[kubernetes-hpa-autoscaling-design]] | HPA API 稳定底座。 |
| Configurable HPA tolerance | [[kubernetes-hpa-autoscaling-design]] | 把全局 10% tolerance 下放到 workload 和方向级别。 |
| Container resource autoscaling | [[kubernetes-hpa-autoscaling-design]] | 避免 sidecar 稀释主容器指标。 |
| Metrics specificity / label selector | [[kubernetes-hpa-autoscaling-design]] | 让 custom/external metrics 精确匹配目标。 |
| Pod selection accuracy | [[kubernetes-hpa-autoscaling-design]] | 防止 HPA 把同 label 但非同 owner 的 Pod 算进分母。 |
| Scale from zero | [[kubernetes-hpa-autoscaling-design]] | 让高成本 workload 能基于 object/external metrics 缩到 0 再拉起。 |
| External metric fallback | [[kubernetes-hpa-autoscaling-design]] | 降低外部指标系统故障对扩缩容的影响。 |
| Volume attach limit autoscaler | [[kubernetes-hpa-autoscaling-design]], [[kubernetes-dra-design-deep-dive]] | 代表 autoscaler 必须理解 scheduler 约束，而不只是加节点。 |

## SIG Node Feature 覆盖

| Feature | 合并到 | 重要性 |
|---|---|---|
| kubelet / CRI / dockershim removal / RuntimeClass | [[kubernetes-node-runtime-observability-security-design]] | kubelet 与 runtime 解耦的基础。 |
| CPU / Memory / Topology Manager | [[kubernetes-node-runtime-observability-security-design]] | 性能型 workload 的资源隔离和 NUMA 对齐基础。 |
| Pod-level resources | [[kubernetes-in-place-pod-resize-design]], [[kubernetes-node-runtime-observability-security-design]] | 从 container resource 走向 pod scope resource 管理。 |
| Device Plugin / CDI / PodResources API | [[kubernetes-dra-design-deep-dive]], [[kubernetes-node-runtime-observability-security-design]] | 连接传统设备插件和下一代 DRA。 |
| DRA structured parameters / ResourceClaim status | [[kubernetes-dra-design-deep-dive]] | 设备资源标准化主线。 |
| In-place resource resize | [[kubernetes-in-place-pod-resize-design]] | Pod resource 从 immutable spec 变成 desired/actual 状态机。 |
| Sidecar / restart policy / graceful shutdown | [[kubernetes-node-runtime-observability-security-design]] | Pod lifecycle 语义补全，影响 Job、服务网格和 agent workload。 |
| User namespaces / rootless kubelet / seccomp / cgroup v2 | [[kubernetes-node-runtime-observability-security-design]] | 节点隔离和最小权限方向。 |
| CRI stats / PSI / resource health / node declared features | [[kubernetes-node-runtime-observability-security-design]] | 可观测和自动化调度/修复的输入信号。 |

## 还没有单独展开的补充项

这些不是漏掉，而是归入补充或后续低优先级：

| 类别 | KEP / feature | 当前处理 |
|---|---|---|
| 历史 extender / coscheduling | `1819`, `583` | 作为 scheduler framework 和 Workload/Gang 的历史对照。 |
| ResourceQuota / node labels quota | `986`, `2372` | 放在 P2，除非后续要专门整理 quota/capacity governance。 |
| probe/log 细节 | gRPC probe、CRI log rotation、stdout/stderr split | 放在 Node lifecycle 补充，不作为第一批详解。 |
| storage/resource 小项 | hugepages、ephemeral storage、memory-backed volumes | 暂归 P2；如后续做 storage/resource 管理专题再拉出。 |
| node config | kubelet drop-in config、dynamic kubelet config removed | 放在 Node runtime 页的边界说明。 |

## 后续维护动作

1. 新增 KEP 先落到本页的合并设计组，再进入 [[kubernetes-keps-design-tracking]] 的 SIG 表。
2. 如果一个 KEP 同时影响多个设计组，例如 DRA + autoscaler + scheduler，要在两个详解页互链，而不是复制两份解释。
3. 如果某组超过 20 个活跃 KEP，再拆二级页；否则保持合并讲解。
4. 下一轮应补 `prod-readiness` 数据，把每个设计组的 feature gates、metrics、rollback、upgrade/downgrade 汇总到本页。
