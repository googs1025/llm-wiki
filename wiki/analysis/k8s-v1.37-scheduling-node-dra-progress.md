---
title: Kubernetes v1.37 Scheduling / Node / DRA Progress
tags: [analysis, kubernetes, kep, sig-scheduling, sig-node, sig-autoscaling, dra, v1.37]
date: 2026-07-15
sources: [src-kubernetes-keps-design-tracking.md, https://github.com/kubernetes/enhancements]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-keps-feature-coverage]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-workload-gang-scheduling-design]], [[kubernetes-dra-design-deep-dive]], [[kubernetes-in-place-pod-resize-design]], [[kubernetes-node-runtime-observability-security-design]], [[kubernetes-dra]]
---

# Kubernetes v1.37 Scheduling / Node / DRA Progress

这页记录 2026-07-15 对 `kubernetes/enhancements` `master` 的最新核验，重点回答：近期 Kubernetes 在调度、Node、DRA 和相关 autoscaling KEP 上推进到了哪里。基础设计脉络见 [[src-kubernetes-keps-design-tracking]]，逐项状态矩阵见 [[kubernetes-keps-implementation-matrix]]。

## 总体判断

v1.37 的主线不是单点调度优化，而是三条线汇合：

1. [[kubernetes-workload-gang-scheduling-design]] 把 PodGroup / Workload 作为调度单位推进到 beta/alpha 组合。
2. [[kubernetes-dra-design-deep-dive]] 把 DRA 从结构化资源模型扩展到 capacity、workload claim、NUMA、status 和 Pod 内可见性。
3. [[kubernetes-in-place-pod-resize-design]] 与 [[kubernetes-node-runtime-observability-security-design]] 把 Pod-level resources、resize、Memory QoS、rootless kubelet 和节点状态补齐到 Node 路径。

```text
v1.37 feature direction
  |
  +-- workload-aware scheduling
  |     +-- Gang Scheduling beta
  |     +-- Topology-aware workload scheduling beta
  |     +-- Controller APIs alpha
  |     +-- CompositePodGroup alpha
  |
  +-- DRA device/resource model
  |     +-- ResourceClaim for workloads beta
  |     +-- Consumable capacity beta
  |     +-- Shared capacity / compatibility groups alpha
  |     +-- ResourceClaim device status stable
  |     +-- DRA attributes Downward API beta
  |     +-- Standard numaNode stable
  |
  +-- node resource/runtime maturity
        +-- Pod-level resource managers beta
        +-- Memory QoS beta
        +-- Rootless kubelet beta
        +-- Pod checkpoint/restore alpha
        +-- EvictionRequest API alpha
```

## SIG Scheduling

| KEP | 当前进展 | 意义 |
|---|---|---|
| `4671-gang-scheduling` | `implementable / beta / v1.37`，目标 stable `v1.38` | Workload / PodGroup 成为调度单位，AI/HPC/batch 不再只靠 out-of-tree coscheduling。 |
| `5732-topology-aware-workload-scheduling` | `implementable / beta / v1.37`，目标 stable `v1.39` | 一组 Pod 作为整体选择 topology placement，连接 GPU/NIC/zone/rack 放置。 |
| `6089-was-controller-apis` | `implementable / alpha / v1.37` | 给 Job/JobSet/LWS 等 controller 提供 workload-aware scheduling building blocks。 |
| `6012-composite-podgroup-api` | `implementable / alpha / v1.37` | 表达多组件 workload 的组合调度单元。 |
| `6132-prequeueing-hints` | `implementable / beta / v1.37` | 在 Pod 进入 activeQ 前过滤无效事件，减少 DRA/gang/resize 等等待场景的 requeue 噪声。 |
| `5598-opportunistic-batching` | `implementable / beta`，近期扩展 rescoring，目标 stable `v1.38` | 面向大规模调度吞吐，把批量机会和重新打分纳入 scheduler 路径。 |
| `5836-scheduler-preemption-for-ippr` | `implementable / alpha / v1.37` | 已绑定 Pod 的 in-place resize 资源冲突可交给 scheduler 抢占处理。 |

调度侧近期提交集中在 2026-06-15 到 2026-06-17：`KEP-6089` 初始合入、`KEP-6012` 初始文档、`KEP-6132` 合入、`KEP-5598` rescoring 扩展、`KEP-4671` preemption 行为调整。这里的信号是：workload-aware scheduling 已经从单一 gang KEP 变成 API、拓扑、抢占、队列和批处理共同推进。

## DRA / Device-Aware Scheduling

| KEP | 当前进展 | 意义 |
|---|---|---|
| `5075-dra-consumable-capacity` | `implementable / beta / v1.37`，目标 stable `v1.38` | 设备资源不再只表达离散设备，也能表达 GPU memory、带宽、license 等可消费容量。 |
| `5729-resourceclaim-support-for-workloads` | `implementable / beta / v1.37` | ResourceClaim 支持 workload 级消费者，直接连接 DRA 与 PodGroup/gang scheduling。 |
| `5517-dra-node-allocatable-resources` | `implementable / alpha / v1.37` | 暴露 DRA node allocatable，给 scheduler/autoscaler 容量推理使用。 |
| `5941-dra-shared-consumable-capacity` | `implementable / alpha / v1.37` | 多个 logical devices 共享同一 capacity pool。 |
| `5963-device-compatibility-groups` | `implementable / alpha / v1.37` | 表达多设备组合兼容性，适合多卡/多 NIC 配对。 |
| `6080-dra-derived-attributes` | `provisional / alpha / v1.37` | 从 driver 属性派生调度可用属性，仍应视为设计观察项。 |

这些 KEP 把 DRA 从 “ResourceSlice + ResourceClaim” 推进到复杂设备组合。对 AI 平台最关键的是 `5729` 和 `5075`：前者让一组 Pod 共享或引用 workload 级 claim，后者让 claim 不只消费一个设备编号，而是消费容量。

## SIG Node

| KEP | 当前进展 | 意义 |
|---|---|---|
| `4817-resource-claim-device-status` | `implementable / stable / v1.37` | DRA 分配结果和设备信息进入 ResourceClaim status，成为稳定可观测面。 |
| `5304-dra-attributes-downward-api` | `implementable / beta / v1.37`，目标 stable `v1.38` | Pod 内 workload 可看到 DRA device attributes。 |
| `6072-dra-standard-numanode` | `implementable / stable / v1.37` | 标准化 `numaNode` 设备属性，连接 DRA 和 topology-aware placement。 |
| `5945-dra-optional-node-preparation` | `implementable / alpha / v1.37` | 某些设备场景可跳过强制 NodePrepare，降低轻量路径成本。 |
| `5526-pod-level-resource-managers` | `implementable / beta / v1.37`，目标 stable `v1.39` | CPU/Memory/Topology Manager 从 container scope 扩展到 Pod scope。 |
| `6122-configurable-scaling-delay-with-pod-resource-exposure` | `implementable / alpha / v1.37` | Pod resource exposure 后的 scaling delay 可配置，给应用处理资源收缩窗口。 |
| `2570-memory-qos` | `implementable / beta / v1.37` | Memory QoS 重新进入 beta 路径。 |
| `2033-kubelet-in-userns-aka-rootless` | `implementable / beta / v1.37` | rootless kubelet 进入 beta，降低 kubelet 特权面。 |
| `5823-pod-level-checkpoint-restore` | `implementable / alpha / v1.37` | Pod 级 checkpoint/restore 进入 KEP 路径。 |
| `4563-eviction-request-api` | `implementable / alpha / v1.37` | eviction 请求 API 化，给节点驱逐更清晰的表达。 |
| `5683-lifecycle-conditions` | `implementable / alpha / v1.37` | Node lifecycle conditions 进入 alpha。 |

Node 侧的重点是把调度决策需要的节点事实标准化：DRA status、DRA attributes、NUMA、Pod-level resource manager、Memory QoS 和 resource exposure 都是在为“更复杂的调度/弹性决策”提供可信输入。

## Autoscaling 联动

| KEP | 当前进展 | 意义 |
|---|---|---|
| `4951-configurable-hpa-tolerance` | `implementable / stable / v1.37` | HPA tolerance 从全局粗粒度参数变成 HPA/方向级配置。 |
| `2021-scale-from-zero` | `implementable / beta / v1.37` | object/external metrics 支持 0 副本恢复。 |
| `5030-attach-limit-autoscaler` | `implementable / beta / v1.37` | Cluster Autoscaler 模拟 CSI volume attach limit。 |
| `5679-external-metric-fallback` | `implementable / alpha / v1.36`，目标 beta `v1.37` | external metric 失败时可 fallback，降低指标系统故障对 HPA 的影响。 |

autoscaling 不是本页主角，但它决定这些调度能力能否被容量系统理解。DRA、PodGroup、volume attach limit、topology 和 scale-from-zero 都要求 autoscaler 不只是“加节点”，而是能模拟 scheduler 约束。

## 选型和跟踪建议

对 AI/HPC/GPU 平台，优先跟踪这四组：

1. `4671` + `5732` + `6089`：Kubernetes 是否能原生表达 workload 级调度。
2. `5729` + `5075` + `5517`：DRA 是否能让 workload 和 autoscaler 理解设备容量。
3. `4817` + `5304` + `6072`：DRA 设备状态、属性和 NUMA 是否形成稳定可观测面。
4. `5526` + `6122` + `5836`：Pod-level resources 和 in-place resize 是否闭环到 scheduler。

采用判断：

| 场景 | 判断 |
|---|---|
| 普通生产 workload | 继续依赖稳定 scheduler、HPA、device plugin 路径，避免直接押注 alpha DRA 扩展。 |
| AI/HPC batch / training | 重点验证 PodGroup/gang、topology-aware workload scheduling、Kueue/JobSet/LWS 集成。 |
| GPU/NIC/DPU 平台 | 跟踪 DRA consumable capacity、ResourceClaim for workloads、standard `numaNode` 和厂商 driver 实现。 |
| 节点资源隔离 | 关注 Pod-level resource managers、Memory QoS、rootless kubelet，但生产采用仍要看 feature gate 默认值和 kubelet 行为。 |

## 下一步核验

`kubernetes/enhancements` 只表示 KEP 元数据和设计状态。后续要继续核验：

- `kubernetes/kubernetes` 对应实现 PR 是否已合入。
- feature gate 默认值、API group/version 和 release notes。
- conformance / e2e 覆盖，尤其是 gang scheduling、DRA workload claim、Pod-level resource managers。
- [[karpenter]] / Cluster Autoscaler 是否能理解 PodGroup、DRA structured parameters 和 volume attach limit。
- [[dra-driver-nvidia-gpu]] 等真实 driver 是否跟进 v1.37 DRA 字段。
