---
title: Kubernetes Node Runtime Observability Security Design
tags: [analysis, kubernetes, kep, sig-node, kubelet, cri, observability, security, lifecycle, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/2040-kubelet-cri/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/2221-remove-dockershim/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/585-runtime-class/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/3570-cpumanager/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/1769-memory-manager/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/693-topology-manager/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/753-sidecar-containers/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/127-user-namespaces/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/2033-kubelet-in-userns-aka-rootless/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/2371-cri-pod-container-stats/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/5394-psi-node-conditions/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/4680-add-resource-health-to-pod-status/README.md]
related: [[kubernetes]], [[kubernetes-keps-feature-coverage]], [[kubernetes-keps-design-tracking]], [[kubernetes-in-place-pod-resize-design]], [[kubernetes-dra-design-deep-dive]], [[cri-tools]], [[security-profiles-operator]], [[node-feature-discovery]], [[metrics-server]]
---

# Kubernetes Node Runtime Observability Security Design

这页合并讲 `sig-node` 里除 DRA 和 in-place resize 之外的核心 feature：kubelet/CRI runtime 边界、CPU/Memory/Topology Manager、Pod lifecycle、安全隔离、节点可观测和 resource health。

## 一句话定位

SIG Node 的核心设计方向是把 kubelet 从“绑定某个 runtime 和一堆节点本地实现细节的执行器”，演进为“通过 CRI、resource managers、status/metrics、security primitives 管理节点执行状态的标准控制点”。

## Runtime Boundary: kubelet / CRI / RuntimeClass

`2040-kubelet-cri`、`2221-remove-dockershim`、`585-runtime-class` 是 runtime 边界的基础线：

```text
kubelet
  |
  +-- CRI
        |
        +-- containerd
        +-- CRI-O
        +-- sandboxed runtime
        +-- Windows / other runtimes

Pod.spec.runtimeClassName
  |
  +-- runtime handler selection
```

设计意义：

- kubelet 不再内置 Docker 特殊路径。
- runtime 能通过 CRI 独立演进。
- RuntimeClass 把 sandboxed runtime、gVisor/Kata-like runtime、特殊 runtime handler 变成 Pod 级选择。
- `4033-group-driver-detection-over-cri` 继续减少 kubelet/runtime cgroup driver 配置不一致。
- `5825-cri-pagination` 面向大规模节点 runtime API 性能。

边界判断：kubelet 负责 Kubernetes Pod lifecycle 和节点资源语义；runtime 负责容器创建、运行、状态、日志和低层隔离执行。

## Resource Managers

CPU Manager、Memory Manager、Topology Manager 是性能型 workload 的节点侧底座。

| Manager | 代表 KEP | 作用 |
|---|---|---|
| CPU Manager | `3570` | 为 Guaranteed / latency-sensitive workload 分配 cpuset。 |
| Memory Manager | `1769` | 管理 memory locality，与 Topology Manager 交换 hint。 |
| Topology Manager | `693`, `3545` | 聚合 CPU、memory、device 的 NUMA hint，决定是否满足拓扑对齐策略。 |
| Pod-level resource managers | `5526` | 从 container scope 扩展到 Pod scope。 |

这组 feature 和 [[kubernetes-in-place-pod-resize-design]] 强相关。resize 如果只改 spec，不理解 CPU Manager static policy、Memory Manager、Topology Manager，就会在高性能节点上失败或造成不可解释状态。

## Device Plugin / CDI / PodResources

传统 device plugin 仍然是 Kubernetes 设备接入的稳定路径：

- `3573-device-plugin` 提供 kubelet device plugin API。
- `4009-add-cdi-devices-to-device-plugin-api` 让 device plugin 返回 CDI devices，减少 runtime-specific 注入逻辑。
- `3695-pod-resources-for-dra` 扩展 PodResources API，使其包含 DRA resource。

这条线和 [[kubernetes-dra-design-deep-dive]] 的关系是：device plugin 是旧但稳定的离散设备模型；DRA 是新的结构化 claim 模型；CDI 是两者都可使用的 runtime 注入表达。

## Pod Lifecycle

SIG Node 的 lifecycle KEP 不是杂项，它们决定 kubelet 如何解释 Pod 内部容器关系：

| Feature | KEP | 设计意义 |
|---|---|---|
| Sidecar containers | `753` | 用特殊 initContainer 语义表达 sidecar 启动、就绪、终止顺序。 |
| Ephemeral containers | `277` | 支持 debug container 注入，不改变正常 workload spec。 |
| Graceful node shutdown | `2000`, `2712` | 节点关机时按优先级有序终止 Pod。 |
| Container restart policy | `5307` | 细化 container 级 restart 行为。 |
| Container restart termination | `4438` | 处理 Pod 终止期间 sidecar restart 行为。 |
| EvictionRequest API | `4563` | 给 eviction 请求更清晰的 API 表达。 |

Sidecar containers 对 Job、service mesh、agent runtime 都很重要：没有明确 sidecar 语义时，Job 完成、主容器退出、sidecar 终止顺序会变得混乱。

## Security / Isolation

节点安全线覆盖 user namespace、rootless kubelet、seccomp、cgroup v2 和 kubelet authz：

| Feature | 代表 KEP | 设计意义 |
|---|---|---|
| User namespaces | `127` | Pod 内 root 不再等价宿主 root，降低逃逸影响面。 |
| Rootless kubelet | `2033` | kubelet 自身降低特权运行需求。 |
| HostNetwork userns | `5607` | 让 HostNetwork Pod 也能受 user namespace 保护。 |
| Seccomp by default | `2413` | 默认系统调用限制。 |
| Fine-grained kubelet authz | `2862` | 缩小 kubelet API 权限面。 |
| cgroup v2 / remove cgroup v1 | `2254`, `5573` | 统一现代 Linux resource control 基础。 |

这组 KEP 的共同方向是：把“容器隔离靠 runtime 默认行为”升级为“Pod API、kubelet、runtime、kernel primitives 明确协作”。

## Observability / Node Health

可观测线是 autoscaling、scheduling 和排障的输入信号：

| Feature | KEP | 作用 |
|---|---|---|
| Resource metrics endpoint | `727` | kubelet 资源指标标准入口。 |
| CRI pod/container stats | `2371` | 从 cAdvisor 依赖转向 CRI stats。 |
| PSI metrics | `4205` | 暴露 CPU/memory/io pressure stall information。 |
| PSI node conditions | `5394` | 将 PSI 上升为 Node Conditions，便于调度/自动化响应。 |
| Resource health in Pod status | `4680` | Device Plugin / DRA 资源健康进入 Pod status。 |
| Node declared features | `5328` | 节点能力声明，为调度和控制器提供结构化输入。 |

`2371` 对 [[metrics-server]] 和 HPA 都重要：如果 kubelet 的 stats 来源不稳定，autoscaling 的输入就不可靠。`4680` 对 GPU/DRA workload 重要：Pod pending 或 degraded 时，用户需要知道是设备健康而不是普通资源不足。

## 合并设计图

```text
Pod API
  |
  +-- runtimeClass / sidecar / userns / resize / resource claims
  |
kubelet
  |
  +-- CRI runtime boundary
  +-- CPU / Memory / Topology Manager
  +-- Device Plugin / DRA kubelet plugin / CDI
  +-- Pod lifecycle and eviction
  +-- Pod status / Node conditions / metrics
  |
container runtime + kernel
  |
  +-- cgroups / namespaces / seccomp / devices
```

## 和其他设计页的关系

- [[kubernetes-in-place-pod-resize-design]] 依赖 resource managers、CRI resource update、status/metrics。
- [[kubernetes-dra-design-deep-dive]] 依赖 kubelet plugin、CDI、PodResources API、resource health。
- [[kubernetes-hpa-autoscaling-design]] 依赖 kubelet stats、CRI stats、metrics-server。
- [[kubernetes-scheduler-core-design]] 依赖 node labels、resource health、Node Conditions、declared features 作为调度输入。

## 关键失败模式

| 失败模式 | 设计处理 |
|---|---|
| kubelet/runtime 配置不一致 | CRI cgroup driver detection、RuntimeClass。 |
| container stats 来源不统一 | CRI pod/container stats。 |
| NUMA/CPU/device 不对齐 | Topology Manager 聚合 hints。 |
| sidecar 阻塞 Job 完成或终止 | Sidecar containers 明确 lifecycle。 |
| Pod root 权限过大 | user namespaces、rootless kubelet、seccomp。 |
| 设备异常不可见 | resource health in Pod status。 |
| 节点 pressure 只能靠人工看指标 | PSI metrics -> Node Conditions。 |

## 追踪重点

- CRI stats 是否足够替代 cAdvisor 依赖，并被 [[metrics-server]] 稳定消费。
- resource health status 是否覆盖 DRA 和传统 device plugin。
- rootless kubelet / HostNetwork userns 是否有清晰生产约束。
- CPU/Memory/Topology Manager 与 Pod-level resources、in-place resize 的兼容性。
- sidecar containers 与 Job、LWS、agent runtime 的实际行为是否符合用户直觉。
