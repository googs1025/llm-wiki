---
title: Kubernetes DRA Design Deep Dive
tags: [analysis, kubernetes, kep, sig-node, sig-scheduling, dra, device, gpu, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/4381-dra-structured-parameters/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/3063-dynamic-resource-allocation/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5007-device-attach-before-pod-scheduled/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5075-dra-consumable-capacity/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4815-dra-partitionable-devices/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4816-dra-prioritized-list/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5055-dra-device-taints-and-tolerations/README.md]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-dra]], [[k8s-gpu-device-stack]], [[device-plugin]], [[cdi]], [[node-feature-discovery]], [[dra-driver-nvidia-gpu]], [[karpenter]]
---

# Kubernetes DRA Design Deep Dive

这页拉出 Kubernetes Dynamic Resource Allocation 的关键设计文档。核心是 `sig-node/4381-dra-structured-parameters`，它把早期 `3063-dynamic-resource-allocation` 的 opaque driver 协商路线反转为主线：设备参数必须结构化地暴露给 scheduler 和 autoscaler，Kubernetes 才能可靠做调度和容量推理。

## 一句话定位

DRA 是 Kubernetes 对 GPU、NIC、FPGA、DPU、network-attached accelerator、可分区设备和共享容量的下一代设备资源模型。它不是 device plugin 的简单替代，而是把“设备发现、设备选择、claim 状态、节点准备、CDI 注入、scheduler 推理、autoscaler 模拟”放到同一个 API 体系里。

## 为什么 device plugin 不够

Device Plugin API 适合“节点本地、离散、可计数”的资源，例如 `nvidia.com/gpu: 1`。但新设备场景更复杂：

- 设备可能不在节点本地，而是通过 fabric 动态连接。
- 一个设备可能能切成多个 partition，例如 MIG-like GPU。
- 多个容器或多个 Pod 可能共享同一已初始化设备。
- 用户需要选择设备属性，例如型号、内存、PCIe root、driver version、NUMA locality。
- scheduler 和 autoscaler 必须能知道“新增一个节点后是否能满足 claim”。

如果设备选择完全由 vendor driver 在调度后 opaque 决定，scheduler 只能猜，Cluster Autoscaler / [[karpenter]] 也无法模拟。

## 4381 的核心模型

```text
DRA driver
  |
  +-- publishes ResourceSlice
        devices + attributes + capacities

User / controller
  |
  +-- creates ResourceClaim / ResourceClaimTemplate
        device requests + selectors + config

kube-scheduler
  |
  +-- evaluates ResourceClaim against ResourceSlices
  +-- writes allocation result into ResourceClaim status

kubelet
  |
  +-- calls DRA kubelet plugin
  +-- NodePrepareResource / NodeUnprepareResource
  +-- passes CDI devices to runtime
```

`ResourceSlice` 是 driver 发布的资源库存。每个 device 有名字、属性和 capacity。属性可以被 CEL selector 匹配，capacity 用 quantity 表达。

`DeviceClass` 是集群管理员定义的设备类别，承载通用 selector 和配置。用户侧 `ResourceClaim` 引用它，并可继续补充 request selector 和 config。

`ResourceClaim` 是用户或 controller 要的资源。它的 spec 不变，status 由系统写入 allocation result、reservation、设备结果等状态。

## 结构化参数的关键价值

早期 `3063` 让 DRA driver 通过 control-plane controller 参与 allocation。问题是 scheduler / autoscaler 看不懂 driver 的自定义逻辑。`4381` 的结构化参数让 Kubernetes 至少能理解：

- 有哪些设备。
- 设备在哪些节点或资源池。
- 每个设备有哪些标准化或 vendor-specific 属性。
- request 如何用 selector 表达过滤条件。
- claim 是否已经被 allocated / reserved。
- allocation 结果能否被 kubelet 和 driver 重放。

这不是为了让 Kubernetes 理解所有 vendor 细节，而是把“调度必须知道的部分”变成 API 结构，剩下的配置参数仍可 opaque 地传给 driver。

## Scheduler 插件路径

DRA scheduler plugin 不是只在 Filter 阶段做一次检查。它覆盖多个 extension point：

| 阶段 | 作用 |
|---|---|
| `EventsToRegister` | 注册 ResourceClaim、ResourceSlice、DeviceClass 等事件，并通过 queueing hints 精准唤醒相关 Pod。 |
| `PreEnqueue` | 快速检查 Pod 引用的 claim 是否存在，不存在就先不要进入正常调度。 |
| `PreFilter` | 收集 claim、class、slice、已分配资源和 in-flight allocation，准备高效 filter。 |
| `Filter` | 判断候选节点是否能满足 claim，执行 selector/capacity/match-attribute 等检查。 |
| `Reserve` | 节点已选定后，在内存里计算 allocation result。 |
| `PreBind` | 在独立 goroutine 中把 allocation/reservation 写回 ResourceClaim status。 |
| `Unreserve` | 绑定失败或调度失败时释放 reservation，避免 deadlock。 |

这个设计把昂贵或阻塞 API 写操作放到 `PreBind` 旁路，减少主 scheduling cycle 的阻塞。

## ResourceClaim 状态机

DRA 的状态核心在 `ResourceClaim.status`：

```text
unallocated
  |
  +-- scheduler chooses node/device
  v
allocated
  |
  +-- reservedFor includes consumer
  v
in use by Pod / other consumer
  |
  +-- consumer removed or completed
  v
deallocated / reusable
```

几个设计点很关键：

- `allocation` 是否非空决定 claim 是否已分配。
- `reservedFor` 决定 claim 是否正被某些 consumer 使用。
- 多 scheduler 并发时，status update conflict 是正常同步机制。
- `Unreserve` 必须释放 reservation，否则两个 Pod 各占一个 claim 等另一个 claim，会形成永久 deadlock。
- kube-controller-manager 清理完成 Pod 的 reservation，并释放不再使用的 allocation。

## kubelet 和 DRA plugin

kubelet 通过 plugin registration 发现 DRA kubelet plugin。Pod 绑定到节点并且 claim 已 allocated/reserved 后，kubelet 调用：

- `NodePrepareResource`：让 driver 在本节点准备设备，返回 CDI device IDs 或等价注入信息。
- `NodeUnprepareResource`：Pod 不再使用资源时释放节点准备状态。

这条路径的关键是：scheduler 决定“用哪个设备”，kubelet/driver 负责“把设备准备好并注入容器”。如果设备在 scheduler 决定后消失，kubelet plugin 必须二次确认，Pod 可能保持无法启动直到资源恢复或被重新处理。

## DRA 与 Autoscaler

DRA 最重要的教训来自 `3063` 到 `4381` 的路线变化：Cluster Autoscaler 需要模拟未来节点上的资源可用性。对于 node-local 设备，如果 claim 参数 opaque，autoscaler 无法知道加哪类节点能满足 Pod。

结构化参数让 autoscaler 至少可以读取 `ResourceSlice` 模型和 claim selector，判断“创建某个 node group 的节点是否可能让 pending Pod 调度成功”。这也是 DRA 为什么不能只停留在 driver 自定义 allocation 的原因。

## 关键扩展 KEP

| KEP | 解决的问题 | 设计意义 |
|---|---|---|
| `5007-device-attach-before-pod-scheduled` | 设备 attach/初始化可能是异步的，Pod 不应先绑定再失败。 | 把 device binding conditions 放入 scheduler PreBind 等待路径。 |
| `5075-dra-consumable-capacity` | 设备不一定是离散实例，也可能有可消费容量。 | 支撑 GPU memory、带宽、license、共享 buffer 等容量型设备。 |
| `5941-dra-shared-consumable-capacity` | 多个设备共享一组 capacity。 | 处理多个 logical device 背后共享同一个物理资源池。 |
| `4815-dra-partitionable-devices` | 设备可以动态切分。 | 让 MIG-like 或 TPU-like partition 不再只能预先静态发布。 |
| `4816-dra-prioritized-list` | 用户可接受多种设备配置。 | 用优先级备选列表表达“首选 A，不行则 B”。 |
| `5055-dra-device-taints-and-tolerations` | 设备健康或策略需要暂时排除。 | 将 node taint 思路下沉到 device 层。 |
| `6080-dra-derived-attributes` | 不同 driver 属性表达不一致。 | 用派生属性对齐调度可用的 topology/compatibility 语义。 |

## 失败模式和风险

| 风险 | 解释 | 设计处理 |
|---|---|---|
| stale ResourceSlice | driver 发布的设备状态过期。 | kubelet plugin 在 NodePrepare 时二次确认。 |
| scheduler filter 成本高 | CEL、设备数量、claim 数量、match attributes 会放大计算成本。 | Filter timeout、queueing hints、scheduler metrics。 |
| claim 并发 reservation | 多 scheduler 或多个 Pod 争同一 claim。 | ResourceVersion/UID/status conflict 作为同步点。 |
| node reboot / kubelet restart | 旧 ResourceSlice 可能残留。 | kubelet 启动时删除本节点 ResourceSlices，等待 driver 重建。 |
| opaque 参数过多 | autoscaler 和 scheduler 无法推理。 | structured parameters 作为 GA 主线，opaque config 仅用于 driver 准备。 |
| non-graceful node shutdown | NodeUnprepare 不一定被调用。 | driver 需要在 Deallocate 或外部状态中恢复。 |

## 和 GPU 生态的关系

- [[device-plugin]] 仍适合简单离散资源；DRA 适合需要属性、claim、共享、拓扑、partition、跨 Pod 生命周期的资源。
- [[cdi]] 是设备注入 runtime 的标准表达，DRA kubelet plugin 可以返回 CDI devices。
- [[dra-driver-nvidia-gpu]] 是观察 DRA 在真实 GPU/MIG/VFIO 场景落地的重要项目。
- [[node-feature-discovery]] 仍然有价值，但它更多发布节点能力标签；DRA 发布的是可分配设备库存。
- [[k8s-gpu-device-stack]] 应该把 DRA 作为下一代 GPU 资源抽象主线，而不是 device plugin 的旁支。

## 阅读顺序

1. `4381-dra-structured-parameters`：DRA 主线设计。
2. `3063-dynamic-resource-allocation`：理解为什么 opaque control-plane allocation 被降级。
3. `4815` / `5075` / `5941`：理解 partition 和 capacity。
4. `5007`：理解 device attach/readiness 如何进入调度。
5. `5055` / `4816` / `6080`：理解生产化调度表达。

## 追踪重点

- DRA API 版本从 beta 到 GA 的字段稳定性。
- scheduler DRA plugin 的性能数据，尤其是 Filter latency 和 queueing hint 命中率。
- Cluster Autoscaler / [[karpenter]] 对 DRA structured parameters 的真实支持。
- NVIDIA、其他 GPU/NIC/DPU driver 是否采用 ResourceSlice/ResourceClaim 标准路径。
- DRA 与 Workload/PodGroup、Topology Manager、NUMA、CDI 的联动是否形成闭环。
