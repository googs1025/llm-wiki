---
title: Kubernetes DRA Design Deep Dive
tags: [analysis, kubernetes, kep, sig-node, sig-scheduling, dra, device, gpu, design-deep-dive]
date: 2026-09-27
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/4381-dra-structured-parameters/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-node/3063-dynamic-resource-allocation/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5007-device-attach-before-pod-scheduled/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5075-dra-consumable-capacity/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4815-dra-partitionable-devices/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/4816-dra-prioritized-list/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-scheduling/5055-dra-device-taints-and-tolerations/README.md]
related: ["[[kubernetes]]", "[[kubernetes-keps-design-tracking]]", "[[kubernetes-keps-implementation-matrix]]", "[[kubernetes-dra]]", "[[k8s-gpu-device-stack]]", "[[device-plugin]]", "[[cdi]]", "[[node-feature-discovery]]", "[[dra-driver-nvidia-gpu]]", "[[karpenter]]", "[[gpu-sharing]]", "[[gpu-operator]]", "[[k8s-device-plugin]]", "[[hami]]"]
---

# Kubernetes DRA Design Deep Dive

## 当前上游核验（2026-09-27）

本节区分当前官方证据与下文 2026-07 的 KEP 设计/状态笔记；[[src-dra-driver-nvidia-gpu-architecture]] 是 2026-06 的 raw-backed Source 快照，保留其历史仓库/HEAD 和 ASCII 图。当前默认分支 commit 不代表 release，基础 DRA 稳定也不等于所有 Kubernetes 扩展或 NVIDIA driver 功能都已稳定。完整设备栈边界见 [[k8s-gpu-device-stack]]。

| 项目 | 当前 commit | 当前证据边界 |
|---|---|---|
| [[kubernetes]] | [`6c1c7702cf20`](https://github.com/kubernetes/kubernetes/commit/6c1c7702cf2052245ef10e699d45f071af306f59) | Kubernetes DRA API、scheduler allocation 与 kubelet Prepare/Unprepare；各扩展阶段按官方文档及该 commit 的 feature 定义单独核验 |
| [[dra-driver-nvidia-gpu]] | [`495bf4c59b94`](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/commit/495bf4c59b9423080aa1fe2163955f44a495012c) | NVIDIA GPU/ComputeDomain 驱动实现；通过 NVIDIA 仓库入口查询时返回此规范链接，不以 Kubernetes 的 feature stage 替代厂商支持矩阵 |

| 能力 / feature gate | 本次核验的阶段与版本 | 本页相关边界 / 官方依据 |
|---|---|---|
| 基础 DRA / `DynamicResourceAllocation` | Stable，自 Kubernetes v1.35 | [DRA 概览](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/)；基础 Claim/设备分配稳定不覆盖下列所有扩展 |
| Device binding conditions / `DRADeviceBindingConditions` | Beta，自 v1.36，默认启用 | 延迟 Pod binding 以等待外部设备准备；[当前 feature 定义](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/features/kube_features.go#L1413)；仍需对应 driver/status 支持 |
| Consumable capacity / `DRAConsumableCapacity` | Beta，自 v1.36，默认启用 | 多 Claim 消耗同一设备容量；[DRA Features](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-features/#consumable-capacity) |
| Partitionable devices / `DRAPartitionableDevices` | Beta，自 v1.36，默认启用 | 通过共享计数器表达逻辑设备资源重叠；[DRA Features](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-features/#partitionable-devices) |
| Prioritized list / `DRAPrioritizedList` | GA，自 v1.36；v1.37 锁定启用 | 按优先级尝试设备请求候选；[当前 feature 定义](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/features/kube_features.go#L1468) |
| Device taints / `DRADeviceTaints` | 当前源码 v1.37 条目标记 GA、默认启用；v1.38 条目锁定启用 | 设备 taint/toleration 的阶段不同于相关附加规则；[当前 feature 定义](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/features/kube_features.go#L1429)，版本化源码条目不是未来 release 已发布的证明 |
| Optional node operations / `DRAOptionalNodeOperations` | Alpha，自 v1.37，默认关闭 | driver 可声明跳过特定 node-local 操作，不能推广为所有 GPU 都无需 Prepare；[DRA Features](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-features/#optional-node-operations) |

该表只列本页相关且已核验的能力，不是完整 feature 清单。API 对象语义见 [DRA API Objects](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/)。NVIDIA 侧须分别核对 [锚定 driver README](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/495bf4c59b9423080aa1fe2163955f44a495012c/README.md) 和 [GPU Operator 26.7 管理路径](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)：独立仓库 GPU plugin 的支持说明与 Operator 管理版本的默认启用方式不能混用。下文 KEP 状态表属于历史演进记录，不覆盖本节的当前阶段核验。

## M5-C 中的职责边界

[[k8s-gpu-device-stack]] 是设备栈入口，本页聚焦 [[kubernetes-dra]] 的 Claim、调度分配、节点准备与回收。Kubernetes 提供 DRA API 和 scheduler allocation；driver 发布 ResourceSlice 库存及设备约束，解释厂商配置并完成相应准备。DeviceClass 可由管理员或 driver 安装流程提供；[[node-feature-discovery]] 的节点标签不能替代它或 ResourceSlice。

kubelet 驱动节点侧 Prepare/Unprepare，[[dra-driver-nvidia-gpu]] 等插件操作具体设备，[[cdi]] 把已准备设备交给兼容 runtime 注入。[[gpu-operator]] 管理受管组件部署和升级，[[karpenter]] 管理节点容量；两者都不是单次 DRA Claim 的通用分配器。是否支持特定扩展仍以页首 feature-stage 表和目标 driver/release 为准，这里不重复或提升其阶段。

## DRA Allocation / Binding Lifecycle

```text
Admin / driver installation ── create selectors + config ──> DeviceClass
DRA driver - - publish inventory / attributes / capacities - -> ResourceSlice
User / workload controller ── create directly ──> ResourceClaim
User ── create ResourceClaimTemplate + referencing Pod ──> API
Pod/template - - watch / reconcile - -> resourceclaim controller
resourceclaim controller ── create owned Claim / record Pod claim reference ──> API

Pod + Claim + DeviceClass + ResourceSlice - - watch / scheduling input - -> scheduler
PreFilter / Filter ── evaluate feasible Node + devices ──> select compatible Node
Reserve ── retain candidate allocation in memory ──> PreBind
PreBind ── API write ──> Claim.status.allocation + reservedFor
  ├── no binding conditions ──> continue binding
  └── binding conditions enabled + present ──> wait in PreBind
Claim allocation - - observed by external driver controller - -> device preparation
driver controller ── write device conditions ──> Claim.status.devices
device conditions - - observed ready / failed / timeout - -> PreBind result
PreBind success ──> Bind Pod to compatible Node
PreBind failure ──> Unreserve / cleanup this attempt - - retry feedback - -> queue
```

图例：实线 `── label ──>` 表示有序调用、API 写入或节点动作，虚线 `- - label - ->` 表示发布、watch、反馈与重试。图按引用 Claim 的普通 Pod 路径展开：已经分配的 Claim 会被校验和复用，不能把每一轮都理解成覆盖 allocation；模板需要由 resourceclaim controller 实例化，不是 scheduler 直接把模板当作已存在的 Claim。API 写入者也分开：scheduler 负责本次分配与消费者 reservation，外部 driver/controller 按协议更新设备 conditions，resourceclaim controller 管理派生 Claim 与消费者生命周期。

锚定版本的 [DynamicResources 插件](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/scheduler/framework/plugins/dynamicresources/dynamicresources.go) 在 Reserve 记录候选，在 PreBind 的 `bindClaim` 写回 allocation/reservation，然后按启用的扩展与设备声明等待 binding conditions。没有该条件时直接继续 binding；出现 failure condition 或超时则本次绑定失败。后续 Filter/PostFilter 可按 Claim 的消费者限制决定是否清除失败 allocation，不能把 Unreserve 等同于无条件清空所有共享 Claim。

binding conditions 允许外部准备发生在 Pod binding 前；它不是节点侧 `NodePrepareResources` 的另一种名字。后者通常在 Pod 已绑定、kubelet 准备容器时发生。Claim 分配成功、外部条件就绪、Pod 绑定成功、节点准备成功和容器运行是不同检查点。对象语义与模板控制器分别见 [DRA API Objects](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/dra-api/) 和 [resourceclaim controller](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/controller/resourceclaim/controller.go)。

## kubelet Prepare / CDI / Release

```text
Bound Pod + allocated/reserved Claim - - observed state - -> kubelet DRA manager
kubelet ── track Pod/Claim reference + checkpoint ──> node-local state
kubelet ── NodePrepareResources ──> vendor DRA plugin
plugin ── validate allocation / configure device / recover own state ──> device + checkpoint
plugin ── prepare CDI spec + return CDI device IDs ──> kubelet
kubelet ── checkpoint prepared result / CRI device configuration ──> runtime
runtime ── resolve CDI spec / inject devices / start container ──> running workload

Pod termination - - node reconciliation - -> kubelet drops this Pod reference
  ├── other local Pods still use Claim ──> retain shared prepared state
  └── no local users ──> NodeUnprepareResources ──> plugin cleanup
      ── successful result ──> kubelet updates cache / checkpoint
Pod completion / deletion - - API watch - -> resourceclaim controller
controller ── remove completed consumer reservation ──> Claim status
last consumer released ── eligible deallocation / finalizer cleanup ──> reusable Claim
owned Claim deletion ── owner / GC lifecycle ──> Claim removed when cleanup permits
```

两条终止分支分别处理节点状态和 API 状态，不是跨组件事务，也不保证总按图中文字顺序完成。当前 [kubelet DRA manager](https://github.com/kubernetes/kubernetes/blob/6c1c7702cf2052245ef10e699d45f071af306f59/pkg/kubelet/cm/dra/manager.go) 在 RPC 前后记录 Claim/Pod 与准备结果；其他本地 Pod 仍引用同一 Claim 时延迟 Unprepare。kubelet checkpoint 与 vendor plugin 自己的 checkpoint/config 是不同责任：重启恢复需同时对照 API、节点记录及真实硬件，不能把删除任一记录当作已完成设备释放。

当前 resourceclaim controller 在最后消费者从“仍使用”转为“不再使用”时，可清除相应 allocation 和不再需要的 finalizer，使保留的 Claim 以后重新分配。模板派生 Claim 随 owner 生命周期回收；用户直接创建的持久 Claim 对象可以保留，但保留对象不意味着永久保留同一设备。多消费者场景不能因其中一个 Pod 退出就清空全部 reservation 或拆掉共享准备状态。

图中 Prepare/Unprepare 是常规 node-local 路径。页首 `DRAOptionalNodeOperations` 仍为独立 Alpha 扩展：只有启用该能力且 allocation 携带合法 skip 声明时，kubelet 才跳过指定节点操作；这不是所有 GPU 默认行为。CDI 负责容器注入，不保证硬件准备、健康或隔离策略本身正确。正式 RPC 名称为复数 `NodePrepareResources` / `NodeUnprepareResources`，下方历史笔记的单数简写不应作为接口名使用。

## DRA 失败与恢复路径

| 失败点 / 可见影响 | 自动恢复 / API 与节点边界 | Operator 与人工处理边界 |
|---|---|---|
| ResourceSlice 陈旧或 pool 不完整：设备不可选或节点准备发现不符 | driver 重新发布完整库存，scheduler 根据相关更新重试；节点 plugin 仍须校验设备现状 | Operator 可恢复受管 driver，但错误设备 identity/generation、权限或硬件丢失需修复 |
| Allocation / reservation 并发冲突：PreBind status 写入失败 | API 并发检查拒绝冲突写入，scheduler 重读重算并清理本次保留；不覆盖其他消费者 | 持续争用、错误 UID/字段所有权或自定义控制器乱写 status 需修正 |
| Binding conditions 超时或失败：有 allocation 但 Pod 未绑定 | PreBind 失败触发 Unreserve/重试；后续 deallocation 受 Claim reservation 条件限制，不保证立即换设备 | 修复外部准备 controller、设备条件/RBAC 协议或不可恢复资源故障；延长超时不能制造 Ready |
| Driver / kubelet 重启及 checkpoint 不一致：准备状态难以恢复 | kubelet 重连插件并依据引用/准备记录重试；vendor plugin 按自己的幂等恢复规则核对硬件 | Operator 重建进程不等于硬件回滚；损坏/丢失 checkpoint、升级不兼容需受控恢复 |
| Prepare 或 Unprepare 失败：容器无法启动或节点清理未完成 | kubelet 对可重试错误再次调用，插件需容忍重复 RPC 和部分完成；共享 Claim 按本地引用计数处理 | 检查配置、权限、设备占用和插件错误；永久错误需人工处置，不能仅删除 finalizer |
| CDI spec / runtime 不匹配：Claim 与 Prepare 成功但容器启动失败 | 修复配置后启动路径可重试；CDI 注入不负责重新选择设备 | 核对 CDI IDs、spec 路径、runtime 支持与 driver/toolkit 版本；Operator 只修复其管理范围 |
| MIG / VFIO / ComputeDomain 部分变更：API、checkpoint 与硬件/IMEX 不一致 | driver/controller 按具体模式重放或清理；API 重试没有通用硬件补偿保证 | 确认其他消费者后处理 MIG 实例、驱动绑定、域成员或排空节点；不能假设一次重启全部恢复 |
| 节点失联或非优雅关机：NodeUnprepare 可能未执行 | 控制面继续观察消费者和节点状态；节点返回后由 kubelet/plugin 重新协调，外部设备可能需独立清理 | 对无法返回的节点须核实设备/网络连接已隔离及外部状态已释放，再处理遗留 Claim；API 删除不证明旧节点已停止使用 |

排障应分别核对 Claim allocation/reservedFor/device conditions、Pod binding、kubelet checkpoint、vendor plugin 状态及 runtime 配置。上表是当前职责归纳；下方保留的 KEP 风险条目不能直接当成所有版本/driver 的通用恢复保证。

## KEP 设计与演进（历史笔记）

以下保留 Kubernetes Dynamic Resource Allocation 的历史设计脉络。核心是 `sig-node/4381-dra-structured-parameters`，它把早期 `3063-dynamic-resource-allocation` 的 opaque driver 协商路线反转为主线：设备参数必须结构化地暴露给 scheduler 和 autoscaler，Kubernetes 才能可靠做调度和容量推理。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]；当前阶段以页首核验表为准。

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

历史模型按四个角色拆分：DRA driver 发布带 devices/attributes/capacities 的 ResourceSlice；用户/controller 创建带 requests/selectors/config 的 ResourceClaim 或模板；kube-scheduler 对照库存评估请求并写 allocation status；kubelet 调用 DRA plugin Prepare/Unprepare，再将 CDI 设备交给 runtime。当前完整顺序与模板实例化、条件等待的细分见上方两张图。

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

历史状态模型依次描述：unallocated；scheduler 选择 node/device 后 allocated；`reservedFor` 纳入消费者后被 Pod 或其他 consumer 使用；消费者退出后进入 deallocated/reusable。它概括的是控制面生命周期，不应把其中一条状态转换当成所有节点准备状态已经同步释放，具体回收边界见上方 kubelet Prepare / CDI / Release。

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

## 关键 KEP 实现状态

| KEP | 当前状态 | Alpha / Beta / GA | Feature gate | 关键实现路径 |
|---|---|---|---|---|
| `4381-dra-structured-parameters` | `implemented / stable`，已实现/GA | v1.30 / v1.32 / v1.34 | `DynamicResourceAllocation`, `DRASchedulerFilterTimeout` | `ResourceSlice`/`ResourceClaim`/`DeviceClass` 结构化参数，scheduler 和 autoscaler 可推理。 |
| `3063-dynamic-resource-allocation` | `withdrawn / alpha`，已撤回 | v1.26 / - / - | `DynamicResourceAllocation`, `DRAControlPlaneController` | opaque control-plane allocation 路线，因调度和 autoscaler 不可推理被 4381 取代。 |
| `5007-device-attach-before-pod-scheduled` | `implementable / beta`，仍在 beta | v1.34 / v1.36 / v1.37 | `DRADeviceBindingConditions` | device binding/readiness 条件进入 scheduler PreBind 等待路径。 |
| `5075-dra-consumable-capacity` | `implementable / beta`，仍在 beta | v1.34 / v1.36 / v1.38 | `DRAConsumableCapacity` | 设备可表达可消费 capacity，而不是只表达离散实例。 |
| `5729-resourceclaim-support-for-workloads` | `implementable / beta`，仍在 beta | v1.36 / v1.37 / - | `DRAWorkloadResourceClaims` | ResourceClaim 支持 workload 级消费者，连接 DRA 和 PodGroup。 |
| `5941-dra-shared-consumable-capacity` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.39 | `DRASharedConsumableCapacity` | 多个设备共享同一 capacity pool。 |
| `5963-device-compatibility-groups` | `implementable / alpha`，仍在 alpha | v1.37 / v1.38 / v1.39 | `DRADeviceCompatibilityGroups` | 表达多设备组合兼容性。 |
| `4815-dra-partitionable-devices` | `implementable / beta`，仍在 beta | v1.33 / v1.36 / - | `DRAPartitionableDevices` | 动态或逻辑分区设备进入 ResourceSlice 模型。 |
| `4816-dra-prioritized-list` | `implementable / stable`，GA 目标已达 | v1.33 / v1.34 / v1.36 | `DRAPrioritizedList` | 用户可声明设备请求的优先级备选列表。 |
| `5055-dra-device-taints-and-tolerations` | `implementable / stable`，GA 目标已达 | v1.33 / v1.36 / v1.37 | `DRADeviceTaints`, `DRADeviceTaintRules` | 设备级 taints/tolerations，支持健康和策略隔离。 |
| `4817-resource-claim-device-status` | `implementable / stable`，GA 目标已达 | v1.32 / v1.33 / v1.37 | `DRAResourceClaimDeviceStatus` | 分配结果和设备信息进入 ResourceClaim status。 |
| `5304-dra-attributes-downward-api` | `implementable / beta`，仍在 beta | v1.36 / v1.37 / v1.38 | `NA` | 将 DRA device attributes 暴露给 Pod 内 workload。 |
| `4680-add-resource-health-to-pod-status` | `implementable / beta`，仍在 beta | v1.31 / v1.36 / v1.37 | `ResourceHealthStatus` | Device Plugin/DRA resource health 进入 Pod status。 |

## 追踪重点

- DRA API 版本从 beta 到 GA 的字段稳定性。
- scheduler DRA plugin 的性能数据，尤其是 Filter latency 和 queueing hint 命中率。
- Cluster Autoscaler / [[karpenter]] 对 DRA structured parameters 的真实支持。
- NVIDIA、其他 GPU/NIC/DPU driver 是否采用 ResourceSlice/ResourceClaim 标准路径。
- DRA 与 Workload/PodGroup、Topology Manager、NUMA、CDI 的联动是否形成闭环。
