---
title: Kubernetes Resource Orchestration KEPs
tags: [source, kubernetes, scheduling, autoscaling, node, kep]
date: 2026-07-06
sources: [/Users/zhenyu.jiang/enhancements/keps/sig-scheduling, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling, /Users/zhenyu.jiang/enhancements/keps/sig-node]
related: [[kubernetes]], [[kubernetes-resource-orchestration]], [[kubernetes-scheduling-design]], [[kubernetes-autoscaling-design]], [[kubernetes-node-design]], [[kubernetes-dra]], [[kubernetes-workload-automation]]
---

# Kubernetes Resource Orchestration KEPs

这页整理 `/Users/zhenyu.jiang/enhancements/keps` 中 `sig-scheduling`、`sig-autoscaling`、`sig-node` 三个 SIG 的 KEP 设计脉络。它不是单篇 KEP 摘要，而是为 wiki 新开一个 [[kubernetes-resource-orchestration]] 业务域：把 Pod 放置、工作负载伸缩、节点资源执行三条线放在同一张设计地图里。

## 一句话定位

Kubernetes 资源编排的核心不是单个 scheduler、HPA 或 kubelet 功能，而是一个跨控制面的闭环：[[kubernetes-scheduling-design]] 决定 workload 是否、何时、放到哪里；[[kubernetes-autoscaling-design]] 根据资源和业务信号调整副本或容量；[[kubernetes-node-design]] 在节点上落实 CPU、内存、设备、runtime、安全和可观测状态。

## 核心架构图

```text
User / Controller / Workload API
        |
        v
Pod / Job / Workload / HPA / ResourceClaim
        |
        +-----------------------+
        |                       |
        v                       v
Scheduling control loop     Autoscaling control loop
queue, filter, score,       HPA metrics, behavior,
permit, preemption, DRA     tolerance, fallback, scale subresource
        |                       |
        +-----------+-----------+
                    |
                    v
Node execution boundary
kubelet, CRI, CPU/Memory/Topology managers, device plugin, DRA, cgroups, probes
                    |
                    v
Status / metrics / events / conditions feed back to controllers
```

## 范围

本轮只聚焦三个 SIG 的 KEP README：

| SIG | 规模 | 主要问题域 |
|---|---:|---|
| `sig-scheduling` | 58 篇 README | scheduler framework、队列、抢占、PodGroup/gang、拓扑、DRA 调度语义。 |
| `sig-autoscaling` | 9 篇 README | HPA API、指标选择、scale velocity、tolerance、scale from zero、外部指标容错。 |
| `sig-node` | 125 篇 README | kubelet、CRI、CPU/Memory/Topology Manager、device plugin、DRA、cgroup、probe、Pod lifecycle、安全。 |

没有纳入 `prod-readiness/*` YAML；这些更适合作为第二轮补充，用来对每条设计线增加成熟度、回滚、可观测和发布风险视角。

## Scheduling 主线

[[kubernetes-scheduling-design]] 的 KEP 演进可以分为五层：

| 层次 | 代表 KEP | 设计含义 |
|---|---|---|
| 扩展框架 | `624-scheduling-framework`, `785-scheduler-component-config-api`, `1451-multi-scheduling-profiles`, `1819-scheduler-extender` | 从外部 webhook/extender 转向编译进 scheduler 的 plugin API，并让不同 profile 复用一个 scheduler 实例。 |
| 队列与重试 | `3521-pod-scheduling-readiness`, `4247-queueinghint`, `6132-prequeueing-hints`, `5142-pop-backoffq-when-activeq-empty`, `5501-reflect-preenqueue-rejections-in-pod-status` | scheduler 不再只是“失败后指数退避”，而是让插件表达什么时候值得重新入队、什么时候应该先等外部条件。 |
| 放置策略 | `895-pod-topology-spread`, `1258-default-pod-topology-spread`, `2458-node-resource-score-strategy`, `2249-pod-affinity-namespace-selector`, `3633-matchlabelkeys-to-podaffinity` | 调度策略从节点资源拟合扩展到拓扑、亲和、命名空间、标签、默认 spread 和 score 策略。 |
| 抢占与工作负载 | `268-priority-preemption`, `902-non-preempting-priorityclass`, `4832-async-preemption`, `5710-workload-aware-preemption`, `4671-gang-scheduling`, `6012-composite-podgroup-api` | 抢占从单 Pod 行为扩展为 workload/gang 级别的容量获取和干扰控制。 |
| DRA 调度语义 | `5007-device-attach-before-pod-scheduled`, `5075-dra-consumable-capacity`, `5517-dra-node-allocatable-resources`, `5729-resourceclaim-support-for-workloads`, `6080-dra-derived-attributes`, `5963-device-compatibility-groups` | [[kubernetes-dra]] 把设备请求、拓扑、容量和调度约束推进 scheduler 核心路径。 |

关键设计趋势：scheduler 在保持核心 loop 简单的同时，把可变策略放到插件、profile、queue hints 和 workload API 上；复杂场景不再都靠 fork scheduler 或外部 extender。

## Autoscaling 主线

[[kubernetes-autoscaling-design]] 在这些 KEP 中主要围绕 HPA API 可表达性展开：

| 代表 KEP | 设计含义 |
|---|---|
| `853-configurable-hpa-scale-velocity` | 用 `behavior.scaleUp/scaleDown`、policies、stabilization window 替代硬编码扩缩速率。 |
| `4951-configurable-hpa-tolerance` | 把全局 tolerance 下放到 per-HPA / per-direction，避免大规模 workload 被统一 10% 容忍度拖慢或扰动。 |
| `1610-container-resource-autoscaling` | 从 Pod 总资源指标转向 container 级指标，解决主容器和 sidecar 资源变化不同步的问题。 |
| `117-hpa-metrics-specificity` | 给 custom/external metrics 增加 label selector，让 HPA 能选中更具体的业务指标序列。 |
| `2021-scale-from-zero` | 让 object/external metrics 支持从 0 副本启动，前提是指标能在无 Pod 时仍然可读。 |
| `5679-external-metric-fallback` | 外部指标失败时提供 fallback，避免指标系统短暂异常直接造成错误扩缩。 |
| `5325-hpa-pod-selection-accuracy` | 从纯 label selector 补强到更准确的 Pod 选择，减少 HPA 读到非目标 Pod 指标的风险。 |

关键设计趋势：HPA 的中心问题从“按 CPU 算一个副本数”变成“把指标来源、目标对象选择、容忍区间、扩缩速度和失败策略都变成 workload 级配置”。

## Node 主线

[[kubernetes-node-design]] 的 KEP 设计覆盖 kubelet 的执行边界：

| 层次 | 代表 KEP | 设计含义 |
|---|---|---|
| 资源管理 | `3570-cpumanager`, `1769-memory-manager`, `693-topology-manager`, `1287-in-place-update-pod-resources`, `5419-pod-level-resources-in-place-resize`, `5526-pod-level-resource-managers` | 节点不只是执行 Pod，还要在 CPU、内存、NUMA、QoS、in-place resize 之间做可恢复的本地决策。 |
| 设备与 DRA | `3573-device-plugin`, `4009-add-cdi-devices-to-device-plugin-api`, `3063-dynamic-resource-allocation`, `4381-dra-structured-parameters`, `4817-resource-claim-device-status`, `5677-dra-resource-availability-visibility`, `6072-dra-standard-numanode` | 从 device plugin 的 extended resource 走向 [[cdi]]、[[device-plugin]]、[[kubernetes-dra]] 和结构化设备属性。 |
| Runtime / CRI | `2040-kubelet-cri`, `2221-remove-dockershim`, `585-runtime-class`, `4216-image-pull-per-runtime-class`, `5825-cri-pagination`, `2371-cri-pod-container-stats` | kubelet 与 runtime 的边界持续收敛到 CRI、RuntimeClass、镜像/日志/统计 API。 |
| Pod 生命周期 | `753-sidecar-containers`, `277-ephemeral-containers`, `2000-graceful-node-shutdown`, `2712-pod-priority-based-graceful-node-shutdown`, `5307-container-restart-policy`, `4603-tune-crashloopbackoff` | Pod 生命周期从 start/stop 扩展到 sidecar 顺序、debug container、优先级关机、容器级重启策略和故障退避。 |
| 安全与隔离 | `135-seccomp`, `2413-seccomp-by-default`, `127-user-namespaces`, `2033-kubelet-in-userns-aka-rootless`, `1898-hardened-exec`, `2862-fine-grained-kubelet-authz`, `2254-cgroup-v2` | 节点安全逐步从 admission/policy 下沉到 kubelet、runtime、namespace、exec、cgroup 和默认 profile。 |
| 可观测与健康 | `589-efficient-node-heartbeats`, `727-resource-metrics-endpoint`, `4205-psi-metric`, `5394-psi-node-conditions`, `4680-add-resource-health-to-pod-status`, `5067-pod-generation` | 节点状态反馈从粗粒度 condition 扩展到资源压力、设备健康、Pod generation 和更高效 heartbeat。 |

关键设计趋势：node 侧越来越像“资源执行操作系统”：本地管理器给 scheduler 和 autoscaler 提供可用性信号，同时把 apiserver 期望状态落到 runtime/cgroup/device 层。

## 三条线的交叉点

| 交叉点 | 相关 KEP / 概念 | 解释 |
|---|---|---|
| DRA | `3063`, `4381`, `5007`, `5075`, `5517`, `5677`, `6080` | DRA 同时改变 scheduler 的设备可行性判断、node 的设备准备路径、autoscaler 的容量推理能力。 |
| In-place resize | `1287`, `5419`, `5836`, `6122` | Pod 资源可以运行时变化后，scheduler 需要处理 resize 诱发的抢占，node 需要落实 CRI/cgroup 更新，autoscaler 需要理解暴露和延迟。 |
| Workload / PodGroup | `4671`, `5710`, `5832`, `6012`, `6089` | AI/HPC/batch 场景要求一组 Pod 作为整体进入调度、抢占和状态机，而不是独立 Pod 最优。 |
| Topology | `895`, `3022`, `5732`, `693`, `1769`, `6072` | 拓扑从节点间 spread 延伸到 NUMA、设备、内存和 workload 级放置。 |
| Metrics feedback | `727`, `4205`, `5394`, `117`, `1610`, `5325` | autoscaling 依赖 metrics；node 提供资源/压力/健康信号；scheduler 也开始依赖更精细的状态。 |

## 设计哲学

1. **把策略下放到 API，而不是只留全局 flag**：HPA behavior/tolerance、scheduler profiles、Pod scheduling gates、PodGroup、ResourceClaim 都体现了这个方向。
2. **让控制环只在必要事件上重试**：QueueingHint、PreEnqueue、PodSchedulingReadiness 和 DRA 的等待路径都在降低无效 scheduling cycles。
3. **把资源语义从 scalar 扩展到结构化对象**：CPU/memory/device/topology/sidecar/resource claim 都不是一个简单数字能表达的。
4. **承认局部控制面的边界**：scheduler 不直接配置 runtime，kubelet 不替 autoscaler 决定副本数，HPA 不负责节点供给，但三者通过 status、metrics、events 和 API 对象耦合。
5. **生产化设计必须包含回滚和可观测性**：后续若纳入 `prod-readiness` YAML，应重点补每个 KEP 的 feature gate、metrics、failure mode 和 rollback 条件。

## 选型和研究入口

如果目标是平台工程设计，优先阅读：

- 调度扩展底座：`sig-scheduling/624-scheduling-framework`
- 队列效率：`sig-scheduling/4247-queueinghint`
- 工作负载整体调度：`sig-scheduling/4671-gang-scheduling`
- HPA 行为表达：`sig-autoscaling/853-configurable-hpa-scale-velocity`
- HPA 精度：`sig-autoscaling/1610-container-resource-autoscaling`、`5325-hpa-pod-selection-accuracy`
- 节点资源执行：`sig-node/1287-in-place-update-pod-resources`
- NUMA / 本地资源：`sig-node/3570-cpumanager`、`1769-memory-manager`、`693-topology-manager`
- 设备演进：`sig-node/3573-device-plugin`、`4381-dra-structured-parameters`

这组 KEP 最适合和当前 wiki 已有的 [[kueue]]、[[karpenter]]、[[scheduler-plugins]]、[[descheduler]]、[[metrics-server]]、[[prometheus-adapter]]、[[node-feature-discovery]]、[[kube-scheduler-simulator]]、[[kubernetes-dra]]、[[device-plugin]]、[[cdi]] 对照阅读。
