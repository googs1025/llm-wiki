---
title: Kubernetes Node Design
tags: [concept, kubernetes, node, kubelet, cri, device, kep]
date: 2026-07-06
sources: [src-kubernetes-resource-orchestration-keps.md]
related: [[kubernetes-resource-orchestration]], [[kubernetes]], [[kubernetes-dra]], [[device-plugin]], [[cdi]], [[node-feature-discovery]], [[gpu-sharing]], [[kubernetes-scheduling-design]], [[kubernetes-autoscaling-design]]
---

# Kubernetes Node Design

Kubernetes node design 关注 kubelet 如何把 apiserver 的期望状态落到本地 runtime、cgroup、device、volume、probe、安全和状态反馈。它是 [[kubernetes-resource-orchestration]] 的执行边界。

## 设计分层

| 层次 | 代表 KEP | 设计关注点 |
|---|---|---|
| 本地资源管理 | `3570-cpumanager`, `1769-memory-manager`, `693-topology-manager`, `3545-improved-multi-numa-alignment`, `1287-in-place-update-pod-resources` | CPU、内存、NUMA、QoS 和运行时资源变更。 |
| Pod 级资源语义 | `2837-pod-level-resource-spec`, `5419-pod-level-resources-in-place-resize`, `5526-pod-level-resource-managers`, `6122-configurable-scaling-delay-with-pod-resource-exposure` | 从 container 级资源扩展到 Pod 级资源和资源暴露延迟。 |
| 设备路径 | `3573-device-plugin`, `4009-add-cdi-devices-to-device-plugin-api`, `3063-dynamic-resource-allocation`, `4381-dra-structured-parameters`, `4817-resource-claim-device-status`, `5677-dra-resource-availability-visibility` | [[device-plugin]]、[[cdi]] 和 [[kubernetes-dra]] 的设备发现、分配、准备和状态反馈。 |
| CRI / runtime | `2040-kubelet-cri`, `2221-remove-dockershim`, `585-runtime-class`, `4216-image-pull-per-runtime-class`, `2371-cri-pod-container-stats`, `5825-cri-pagination` | runtime 抽象、镜像拉取、统计、日志和 dockershim 移除后的边界。 |
| Pod 生命周期 | `753-sidecar-containers`, `277-ephemeral-containers`, `2000-graceful-node-shutdown`, `2712-pod-priority-based-graceful-node-shutdown`, `5307-container-restart-policy`, `4438-container-restart-termination` | sidecar、debug、关机、restart policy、termination 行为。 |
| 安全隔离 | `135-seccomp`, `2413-seccomp-by-default`, `127-user-namespaces`, `2033-kubelet-in-userns-aka-rootless`, `1898-hardened-exec`, `2862-fine-grained-kubelet-authz`, `2254-cgroup-v2` | seccomp、user namespace、rootless、exec hardening、kubelet API 授权和 cgroup v2。 |
| 可观测和健康 | `589-efficient-node-heartbeats`, `727-resource-metrics-endpoint`, `4205-psi-metric`, `5394-psi-node-conditions`, `4680-add-resource-health-to-pod-status`, `5067-pod-generation` | resource metrics、PSI、设备健康、Pod generation、heartbeat 优化。 |

## 核心判断

Node 侧 KEP 的共同方向是把 kubelet 从“Pod 启停器”提升为节点资源管理器。它必须在本地保持可恢复状态，和 CRI/device plugin/DRA driver 协作，并把状态通过 PodStatus、NodeStatus、metrics、conditions 和 events 反馈给 scheduler/autoscaler/controller。

## 关键趋势

- **NUMA 和设备拓扑成为常规资源语义**：CPU Manager、Memory Manager、Topology Manager、DRA structured parameters 都在表达硬件局部性。
- **Pod 资源开始可变**：in-place resize 让资源请求从 immutable spec 变成 desired/actual 状态同步问题。
- **runtime 边界更清晰**：dockershim 移除、CRI stats、RuntimeClass、CDI 都把 kubelet/runtime/device 的责任拆开。
- **安全默认值下沉到节点**：seccomp-by-default、user namespaces、rootless kubelet、fine-grained kubelet authz 都说明 node 是安全边界核心。
- **node health 需要更细粒度反馈**：PSI、resource health、efficient heartbeats 让控制面能更早理解节点压力和设备异常。

## 和现有概念的关系

[[kubernetes-node-design]] 是 [[device-plugin]]、[[cdi]]、[[kubernetes-dra]]、[[gpu-sharing]] 和 [[node-feature-discovery]] 的上位设计背景。对 GPU/AI 平台来说，它解释了为什么单独安装 device plugin 不够，还要理解 topology、ResourceClaim、CDI、kubelet metrics 和 runtime class。
