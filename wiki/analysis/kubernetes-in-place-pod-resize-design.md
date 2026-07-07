---
title: Kubernetes In-Place Pod Resize Design
tags: [analysis, kubernetes, kep, sig-node, sig-scheduling, kubelet, pod-resize, resource-management, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/1287-in-place-update-pod-resources/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/5419-pod-level-resources-in-place-resize/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/5526-pod-level-resource-managers/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/5554-in-place-update-pod-resources-alongside-static-cpu-manager-policy/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/6122-configurable-scaling-delay-with-pod-resource-exposure/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5836-scheduler-preemption-for-ippr/README.md]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-keps-implementation-matrix]], [[kubernetes-workload-automation]], [[metrics-server]], [[karpenter]], [[node-feature-discovery]], [[scheduler-plugins]]
---

# Kubernetes In-Place Pod Resize Design

这页拉出 `sig-node` 和 `sig-scheduling` 交叉的一组重要设计文档：`1287-in-place-update-pod-resources` 是主线，`5419`、`5526`、`5554`、`6122`、`5836` 继续扩展到 Pod-level resources、CPU/Memory manager、static CPU policy、延迟暴露和 scheduler preemption。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]。

## 一句话定位

In-place Pod resize 让 Pod 的 CPU/memory requests/limits 可以在不重建 Pod、不重启容器的情况下更新。它把 Pod resource 从“创建时不可变配置”改成“spec desired state + status actual/allocated state”的控制循环。

## 为什么重要

传统 Kubernetes 要改 Pod 资源，必须重建 Pod。对无状态服务这通常可以接受，但对这些场景代价很高：

- Stateful workload 重建会影响可用性和数据 locality。
- Batch / training workload 重启会浪费已经运行的计算进度。
- LLM serving 或多副本少的服务，重启一个 Pod 就可能造成明显容量缺口。
- VPA 想调整资源时，必须用 eviction/recreate，行为粗糙。

In-place resize 的目标不是接管所有生命周期，而是提供底层能力：资源可以被请求变更，kubelet 尽量在本节点原地完成，失败时把状态暴露给上层 controller 决策。

## 核心状态模型

`1287` 的关键是把资源状态拆成四层：

```text
Desired
  what user/controller wants
  Pod.spec.containers[*].resources
    |
    v
Allocated
  what kubelet admitted and checkpointed
  Pod.status.containerStatuses[*].allocatedResources
    |
    v
Actuated
  what kubelet passed to runtime/cgroup
  local checkpoint, not API
    |
    v
Actual
  what runtime reports as running config
  Pod.status.containerStatuses[*].resources
```

这个拆分解决了一个长期问题：`spec.resources` 不能再被理解为“实际正在使用的资源”，它只是 desired state。真实资源要从 status 看。

## API 设计

资源变更只能通过 Pod `/resize` subresource 进行，允许修改：

- `.spec.containers[*].resources`
- `.spec.initContainers[*].resources`，仅限 sidecar 场景
- `.spec.resizePolicy`

普通 Pod update 仍不能直接改 resources。这样做的原因是 resize 有独立 validation、status、权限和 rollout 语义，不应该混进普通 Pod spec update。

`resizePolicy` 允许用户为 CPU/memory 指定是否需要重启容器：

| 策略 | 含义 |
|---|---|
| `NotRequired` | 默认，尽量不重启容器原地调整。 |
| `RestartContainer` | 资源变化需要重启容器才能生效。 |

这不是强保证。runtime 如果知道无法无重启完成，应该返回错误，kubelet 后续重试或由上层处理。

## Resize Conditions

Resize 通过 Pod conditions 暴露进度：

| Condition | 含义 |
|---|---|
| `PodResizePending` | desired resources 已变化，但 kubelet 尚未分配。 |
| `PodResizeInProgress` | allocated 和 actual/actuated 不一致，正在执行。 |
| `PodResizePreemptionDisabled` | 节点策略禁止为 resize 触发 preemption。 |

`PodResizePending` 细分两个重要 reason：

- `Deferred`：理论可行，但当前节点空闲资源不足，后续会重试。
- `Infeasible`：不可行，不会自动重试，例如超过节点容量、static pod、某些 policy 不支持。

这使上层 controller 能区分“等一等可能成功”和“这次 resize 设计上不可能成功”。

## Kubelet 控制流

```text
Pod /resize request
  |
  +-- API validation
  |
kubelet observes updated Pod
  |
  +-- check node allocatable and current allocations
  +-- allocate or mark Deferred/Infeasible
  +-- checkpoint allocated resources
  +-- call CRI UpdateContainerResources
  +-- update Pod status resources/conditions
```

Kubelet 负责本节点 admission 和执行。它会按优先级处理 pending resize：

1. 不增加 request 的 resize 优先，因为通常应当更容易成功。
2. 高 PriorityClass。
3. 高 QoS class。
4. 等待时间更长的 resize。

这只是 kubelet 内部处理顺序，不等于 scheduler 级抢占策略。

## CRI 变化

In-place resize 要求 CRI 的 `UpdateContainerResources` 语义更清晰：

- 调整 CPU/memory 时应尽量不故意重启容器。
- `ContainerStatus` 能报告当前资源配置。
- Pod-level cgroup 变化后，kubelet 可以通过 `UpdatePodSandboxResources` 通知 runtime/NRI plugin。

`UpdatePodSandboxResources` 被设计成 best effort。它失败不阻塞 kubelet 完成 resize，因为 kubelet 仍是 Pod-level cgroup 的主要执行者。

## Pod-level Resources

`5419-pod-level-resources-in-place-resize` 把 resize 从 container-level 扩到 Pod-level resources。它的难点是“有效 Pod 资源需求”不再只是 container 资源求和：

- API defaulting 可能影响 Pod-level 和 container-level 的最终值。
- kubelet、scheduler、cgroup、quota 都要理解 Pod-level resources。
- status 需要暴露 Pod-level allocated/actual，避免用户只看到 container 层。

这条线和 `5526-pod-level-resource-managers` 强相关，因为 CPU/Memory/Topology Manager 原本多以 container 为 scope 管理资源。

## Static CPU Manager 和 Scale-down Delay

`5554` 与 `6122` 处理更难的高性能场景：static CPU Manager 下，Pod 可能拥有 exclusive CPUs。缩容 exclusive CPUs 不是简单改 cgroup：

- 应用可能需要先停止使用某些 CPU。
- kubelet 直接移除 cpuset 可能造成性能抖动或错误。
- 工作负载需要知道即将被收回哪些 CPU。

因此 `6122` 引入“资源暴露 + configurable scaling delay”方向：先通过 Downward API 暴露 desired/assigned CPU 信息，给应用一个准备窗口，再执行实际收缩。

这是 Kubernetes 从“资源由平台单向强制”走向“平台和高性能 workload 协调”的信号。

## Scheduler Preemption for Resize

`5836-scheduler-preemption-for-ippr` 解决 `Deferred` resize 的下一步：如果当前节点资源不足，是否可以抢占低优先级 Pod 来让已运行 Pod 扩容？

关键点：

- resize Pod 已经绑定到节点，所以 scheduler 只能在该节点评估。
- `NodeName` / `NodeResourcesFit` 路径需要特殊处理已调度 Pod。
- 如果 resize 不 fit，`DefaultPreemption` 可以选择 victim。
- victim 删除后，deferred Pod 重新进入队列评估。
- scheduler 不需要额外 reservation，因为它按 `max(desired, allocated, actual)` 看资源，desired 已经占位。

这把 resize 从 kubelet 本地重试，扩展到 scheduler 参与的资源重排。

## Node-level Preemption Policy

有些节点由外部系统支持“节点扩容”或“动态调大节点容量”。这些节点上，为了让一个 Pod resize 而抢占别的 Pod，可能不是最佳选择。

因此 `5836` 提出 node-level policy：

```text
Node.spec.podPreemptionPolicy.disableResizePreemption
```

设计上不是让 scheduler 直接读 Node policy 后自己决定，而是让 kubelet 读本节点 policy，并在 Pod status 设置 `PodResizePreemptionDisabled` condition。scheduler 继续以 Pod condition 为入口，避免把 resize preemption path 直接耦合到 Node spec 细节。

这个设计保持了责任边界：

- kubelet 负责节点本地 resize 生命周期。
- scheduler 负责是否排队、是否抢占。
- Node policy 由 kubelet转译成 Pod status 信号。

## 关键失败模式

| 失败模式 | 设计处理 |
|---|---|
| spec 和实际资源不一致 | desired / allocated / actuated / actual 四层状态。 |
| resize 后 runtime 没真正应用 | `ContainerStatus.resources` 暴露 actual，kubelet 重试或报错。 |
| node 资源不足 | `Deferred` condition，后续重试。 |
| resize 永远不可能成功 | `Infeasible` condition，交给上层处理。 |
| scheduler 过度抢占 | node-level preemption policy + PodResizePreemptionDisabled。 |
| static CPU 缩容伤害 workload | scaling delay + Downward API 暴露 assigned cpuset。 |
| 与 workload-aware preemption 冲突 | Alpha 先按单 Pod resize 处理，Beta 需设计 group-wide 协调。 |

## 和 autoscaling 的关系

In-place resize 是 VPA 和 HPA 之间的底层能力补位：

- HPA 通过改 replicas 横向扩缩。
- VPA 或类似 controller 可以通过 `/resize` 纵向改资源。
- 如果 resize 被 `Deferred`，scheduler preemption 或 node autoscaler 可能介入。
- 如果节点支持动态扩容，`disableResizePreemption` 可以偏向 node upsizing，而不是驱逐 Pod。

未来重要问题是：VPA、Cluster Autoscaler、Karpenter、kubelet resize queue、scheduler preemption 如何形成统一优先级。

## 阅读顺序

1. `1287-in-place-update-pod-resources`：主线，先理解状态模型和 `/resize`。
2. `5419-pod-level-resources-in-place-resize`：理解 Pod-level resources。
3. `5526-pod-level-resource-managers`：理解 CPU/Memory/Topology manager 如何支持 Pod scope。
4. `5554` / `6122`：理解 static CPU、exclusive CPUs 和 scaling delay。
5. `5836-scheduler-preemption-for-ippr`：理解 scheduler 如何为 deferred resize 抢占。

## 关键 KEP 实现状态

| KEP | 当前状态 | Alpha / Beta / GA | Feature gate | 关键实现路径 |
|---|---|---|---|---|
| `1287-in-place-update-pod-resources` | `implemented / stable`，已实现/GA | v1.27 / v1.33 / v1.35 | `InPlacePodVerticalScaling`, `InPlacePodVerticalScalingAllocatedStatus` | Pod `/resize` subresource，desired/allocated/actual 状态和 kubelet resize loop。 |
| `5419-pod-level-resources-in-place-resize` | `implementable / beta`，仍在 beta | v1.35 / v1.36 / - | `InPlacePodLevelResourcesVerticalScaling`, `PodLevelResources` | Pod-level resources 参与 in-place resize。 |
| `5526-pod-level-resource-managers` | `implementable / beta`，仍在 beta | v1.36 / v1.37 / v1.39 | `PodLevelResources`, `PodLevelResourceManagers` | CPU/Memory/Topology Manager 支持 Pod scope 管理。 |
| `5554-in-place-update-pod-resources-alongside-static-cpu-manager-policy` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.39 | `InPlacePodVerticalScalingExclusiveCPUs` | static CPU Manager exclusive CPUs 场景下支持 resize。 |
| `6122-configurable-scaling-delay-with-pod-resource-exposure` | `implementable / alpha`，仍在 alpha | v1.37 / v1.39 / v1.40 | `DownwardAPIAssignedResources` 等 | 先向 Pod 暴露 assigned resources，再延迟收回 exclusive CPUs。 |
| `5836-scheduler-preemption-for-ippr` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.39 | `SchedulerPreemptionForPodResize` | scheduler 为 `Deferred` resize 在已绑定节点上选择 victim。 |

## 追踪重点

- `/resize` subresource 是否被 VPA、StatefulSet、Job controller 等真实使用。
- status 中 allocated/actual resources 是否被 metrics pipeline 和用户工具正确展示。
- static CPU Manager / Memory Manager / Topology Manager 的策略兼容性。
- resize-induced preemption 与 workload-aware preemption 的后续设计。
- node autoscaling 与 resize preemption 的优先级冲突。
