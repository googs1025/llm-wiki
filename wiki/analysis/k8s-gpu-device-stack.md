---
title: Kubernetes GPU / Device Stack 项目地图
tags: [kubernetes, gpu, device-plugin, dra, cdi, project-map]
date: 2026-09-27
sources: [src-k8s-gpu-device-plugins-stars, src-hami-architecture, src-gpu-operator-architecture, src-dra-driver-nvidia-gpu-architecture, src-k8s-device-plugin-architecture, src-node-feature-discovery-architecture]
related: ["[[kubernetes]]", "[[llm-inference]]", "[[device-plugin]]", "[[kubernetes-dra]]", "[[cdi]]", "[[gpu-sharing]]", "[[hami]]", "[[gpu-operator]]", "[[dra-driver-nvidia-gpu]]", "[[k8s-device-plugin]]", "[[node-feature-discovery]]", "[[kubernetes-dra-design-deep-dive]]"]
---

# Kubernetes GPU / Device Stack 项目地图

## 当前上游核验（2026-09-27）

以下 commit 是执行时官方默认分支快照，不代表 release 或整套 GPU 能力的成熟度。[[src-node-feature-discovery-architecture]]、[[src-gpu-operator-architecture]]、[[src-k8s-device-plugin-architecture]]、[[src-dra-driver-nvidia-gpu-architecture]] 与 [[src-hami-architecture]] 保留 2026-06 的 raw-backed Source 及原始 ASCII 图；相关 KEP 笔记保留 2026-07 的设计/演进语境。当前 DRA 基础能力与扩展阶段分别见 [[kubernetes-dra-design-deep-dive]]。

| 项目 | 当前 commit | 当前职责 / allocation 边界 | M5-C 层 |
|---|---|---|---|
| [[node-feature-discovery]] | [`386fda4332ba`](https://github.com/kubernetes-sigs/node-feature-discovery/commit/386fda4332ba5f049c6f0b107f9a58cd46f5af04) | worker/master 发布节点能力与 labels，NodeFeature/NodeFeatureRule 表达发现和规则，topology-updater/GC 管拓扑数据及清理；不执行每次 Pod 设备分配 | Discovery / capability |
| [[gpu-operator]] | [`60526e35efee`](https://github.com/NVIDIA/gpu-operator/commit/60526e35efeeedef584d8f40db0bac8864f98f26) | 管理 GPU 软件组件生命周期；官方 26.7 文档区分 Device Plugin 的 ClusterPolicy 路线与 DRA 的 GPUCluster 路线，后者不直接管理 GPU driver | Node software lifecycle |
| [[k8s-device-plugin]] | [`86142cf1a93f`](https://github.com/NVIDIA/k8s-device-plugin/commit/86142cf1a93fb68a99c5927b9599e13392e27e15) | kubelet 注册、ListAndWatch/health、Allocate 与 extended resources；按配置返回 env/mount/CDI 设备交接信息 | Device Plugin allocation / injection handoff |
| [[dra-driver-nvidia-gpu]] | [`495bf4c59b94`](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/commit/495bf4c59b9423080aa1fe2163955f44a495012c) | DRA GPU 与 ComputeDomain 插件/控制面，发布设备库存并执行节点 Prepare/Unprepare；GPU 配置能力和 ComputeDomain 支持范围需按安装版本分别判断 | DRA driver / node preparation |
| [[hami]] | [`a2dd191b2e7f`](https://github.com/Project-HAMi/HAMi/commit/a2dd191b2e7fb1f289833e9b4fcef16289ec89b3) | scheduler/extender 计算设备共享与 reservation，annotation 交接给 device-plugin Allocate，HAMi-core 在容器侧实施相应隔离 | Sharing / allocation handoff / isolation |

官方依据：[NFD 当前介绍](https://github.com/kubernetes-sigs/node-feature-discovery/blob/386fda4332ba5f049c6f0b107f9a58cd46f5af04/docs/get-started/introduction.md)、[GPU Operator 26.7 DRA 管理路径](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)、[NVIDIA Device Plugin README](https://github.com/NVIDIA/k8s-device-plugin/blob/86142cf1a93fb68a99c5927b9599e13392e27e15/README.md)、[NVIDIA DRA README](https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu/blob/495bf4c59b9423080aa1fe2163955f44a495012c/README.md) 与 [HAMi FAQ](https://project-hami.io/docs/faq)。通过 `NVIDIA/k8s-dra-driver-gpu` 查询当前 HEAD 时，GitHub 返回的规范 commit 链接仍位于 `kubernetes-sigs/dra-driver-nvidia-gpu`，这里采用实际返回的链接。

共存与版本边界：GPU Operator 26.7 文档规定集群使用 GPUCluster 或 ClusterPolicy 之一，不支持两者并存或直接原地迁移；HAMi FAQ 要求避免同一节点上的插件争用同一 GPU resource。上述 NVIDIA DRA 仓库 README 仍区分受支持的 ComputeDomain 与未正式支持、默认关闭的独立 GPU plugin，不能用它推定 Operator 26.7 所管理 driver 的相同默认值。部署判断须绑定具体 release、Helm 配置和 feature gates，不能只看 [[device-plugin]]、[[kubernetes-dra]]、[[cdi]] 或 [[gpu-sharing]] 名称。

这页把 [[src-k8s-gpu-device-plugins-stars]] 从 star list 整理成 Kubernetes GPU / 异构设备资源层地图。核心结论：LLM serving 的 GPU 底座已经不只是“把 `/dev/nvidia0` 挂进 Pod”，而是 driver/operator、container runtime、device discovery、DRA/CDI、sharing、scheduler、observability、diagnostics 和 fake device 测试环境的组合。

## D1 · GPU Device Stack

```text
DISCOVERY / CAPABILITY
  NFD: NodeFeature / NodeFeatureRule / labels / NodeResourceTopology
    - - published capability: informs placement / operator policy - ->
NODE SOFTWARE LIFECYCLE
  GPU Operator: reconcile selected policy and managed components
  Driver / runtime prerequisites must match the chosen installation path
    ├── configure Path A ──> ClusterPolicy / Device Plugin
    │                        extended resource / kubelet Allocate
    │                        ── env / mounts / optional CDI ──> runtime
    └── configure Path B ──> GPUCluster / DRA driver
                             DeviceClass + ResourceSlice / ResourceClaim
                             scheduler allocation / kubelet NodePrepareResources
                             ── CDI device handoff ──> runtime

Path A OR Path B: alternative GPU Operator management modes
Telemetry / health - - observed state - -> operators / node recovery
```

图例：实线 `── label ──>` 表示有序控制动作、API 调用或节点交接；虚线 `- - label - ->` 表示发现发布、reconcile、watch/health 反馈及重试。上层发现信号供控制器决策，不表示每次分配都同步调用 NFD。[[node-feature-discovery]] 发现能力，[[gpu-operator]] 管理组件生命周期；[[device-plugin]] / [[kubernetes-dra]] 承担各自的 allocation 路径，[[cdi]] 位于设备注入和 runtime 交接处，不是第三种 scheduler 或 allocator。

图中的分叉表示选择，不表示把两条 GPU 管理路径同时安装。按 [GPU Operator 26.7 文档](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/26.7/dra-intro-install.html)，ClusterPolicy 与 GPUCluster 不能在同一集群并存，也不支持从 ClusterPolicy/独立 DRA Helm 安装直接原地迁移到 GPUCluster。GPUCluster 不管理 GPU driver，需独立 NVIDIADriver 或预装 driver，并事先准备 CDI-compatible runtime；不能把 ClusterPolicy 的 driver/toolkit 管理默认套到另一条路径。即使脱离 Operator 手动部署，也须确保同一物理设备及资源名有明确分配所有权，避免被不同 allocator 重复分配。

## D2 · Device Plugin Allocation

```text
Device plugin ── register endpoint / resource name ──> kubelet
Device plugin - - ListAndWatch: devices / health - -> kubelet device manager
kubelet - - Node status publication - -> API: capacity / allocatable

Pod extended-resource request + observed Node allocatable
  ── scheduler Node fit / bind ──> Pod assigned to Node
  - - Pod watch - -> kubelet
kubelet ── select device IDs / Allocate RPC ──> device plugin
device plugin ── Allocate response: env / mounts / device specs / CDI IDs ──> kubelet
kubelet ── CRI container configuration ──> container runtime
runtime ── apply configured device injection / start ──> workload

Device health change - - ListAndWatch update - -> allocatable update / future scheduling
```

这是传统 extended-resource 路径：scheduler 先按节点资源数量等条件选 Node，节点侧 kubelet/device plugin 完成具体设备分配与容器配置。NVIDIA 的 device-list strategy 决定 envvar、volume-mounts、CDI annotation 或 CDI CRI 交接方式；不是所有安装都走 CDI。健康设备变为 unhealthy 时，kubelet 减少相应 allocatable，capacity 保持原值；这不等于自动迁移或修复已使用故障设备的容器。参见 [Kubernetes Device Plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/) 和 [NVIDIA plugin 配置](https://github.com/NVIDIA/k8s-device-plugin/blob/86142cf1a93fb68a99c5927b9599e13392e27e15/README.md)。

## D3 · Discovery / Operator Control Loops

```text
NFD worker ── scan hardware / OS / local feature sources ──> feature set
feature set - - publish NodeFeature - -> Kubernetes API
NodeFeature / NodeFeatureRule - - watch / evaluate rules - -> NFD master
NFD master ── update labels / configured annotations or resources ──> Node
NFD topology-updater - - publish topology - -> NodeResourceTopology
NFD GC - - observe stale / removed nodes - -> cleanup obsolete NFD objects
Node capability / topology - - consumed state - -> scheduler / operator / policy

Admin ── apply ClusterPolicy OR GPUCluster ──> Kubernetes API
desired policy / operand changes - - watch / enqueue - -> GPU Operator reconcile
GPU Operator ── create / update managed operands ──> DaemonSets / Deployments / config
operand readiness / errors - - observed feedback - -> GPU Operator
GPU Operator ── write conditions / status ──> policy object
retryable error / further change - - requeue - -> GPU Operator reconcile
```

NFD 的 labels、feature 与 topology 数据是已观测状态，可能受扫描周期、API/watch 延迟或 worker 故障影响；NFD GC 清理过期对象不等于硬件故障恢复。Operator 的 Ready 描述所管理组件状态，不承诺每个 Pod 的 GPU 请求都能满足。分配哪块设备、Prepare 是否成功以及容器内隔离是否生效，仍属于后续路径。NFD 组件与数据对象见 [当前 Introduction](https://github.com/kubernetes-sigs/node-feature-discovery/blob/386fda4332ba5f049c6f0b107f9a58cd46f5af04/docs/get-started/introduction.md)。

## D4 · DRA Resource 生命周期

| 阶段 | 对象 / 操作与负责方 | 必须区分的状态 |
|---|---|---|
| 类别与库存 | 管理员或 driver 安装流程提供 DeviceClass；DRA driver 发布 ResourceSlice 设备库存、属性和容量 | DeviceClass 是选择/配置规则，ResourceSlice 是库存；NFD labels 不能替代设备库存 |
| 请求 | 用户或 workload controller 创建 ResourceClaim；也可通过 ResourceClaimTemplate 为 Pod 派生 Claim | 请求存在不等于已分配，模板本身不是一次 allocation |
| 分配与绑定 | scheduler 根据 Claim、class、slice 与 Node 约束选择设备并写 allocation/reservation；启用相关扩展时等待 binding conditions，再绑定 Pod | 已分配、已绑定、外部设备就绪是不同状态；条件等待依赖相应 feature 和 driver |
| 节点准备 | kubelet 调用 DRA plugin 的 NodePrepareResources；driver 配置设备并维护节点侧状态，返回 CDI 设备信息 | Claim status 成功不证明节点硬件配置/CDI 已完成；可选 node operations 有独立阶段限制 |
| Runtime 交接 | kubelet 经 CRI 把 CDI device IDs 交给兼容 runtime，由 runtime 按 CDI spec 应用设备配置 | CDI 是注入接口，不决定 Claim 分配或共享额度 |
| 终止与回收 | kubelet 在节点不再需要该 Claim 时执行 NodeUnprepareResources；控制面按 Claim/消费者生命周期处理 reservation、删除及 allocation 回收 | 节点 unprepare 不等于所有消费者已退出或持久 Claim 已释放；不能因一个 Pod 退出就盲删共享状态 |

完整状态所有权、binding conditions、Prepare/checkpoint/CDI 与回收细节见 [[kubernetes-dra-design-deep-dive]]；官方流程见 [How DRA Works](https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/how-dra-works/)。基础 DRA 自 v1.35 stable，各扩展和厂商 driver 的支持阶段仍须分别核验。

## Sharing / Isolation Overlay

[[hami]] 的经典路径横跨调度、分配交接和容器隔离：scheduler/extender 根据节点设备视图计算 memory/core/count 与设备 reservation，再写 Pod allocation annotations；device-plugin 在 kubelet Allocate 时读取这些信息并返回设备、环境与挂载配置；HAMi-core 在容器内执行相应 CUDA 调用拦截和限制。`hami.io/vgpu-devices-to-allocate` 与 `hami.io/bind-phase` 是分配进度协议，不是业务 Ready 标志，也不应由用户手工伪造。参见 [HAMi Protocol](https://project-hami.io/docs/developers/protocol)。

同一节点不能让 HAMi 与 NVIDIA 官方 device plugin 同时争用 `nvidia.com/gpu`；GPU Operator 可负责其他软件组件，但要按目标版本关闭冲突的 allocation operand。HAMi-core 的软件拦截、MIG 的硬件分区以及 time-slicing 的共享策略也不能视为等价隔离保障，需验证实际调用路径、显存限制和尾延迟。[HAMi FAQ](https://project-hami.io/docs/faq) 说明了插件共存及软件隔离边界。[HAMi-DRA](https://project-hami.io/docs/get-started/choose-your-setup) 改变的是 Claim/设备分配路径，仍可使用同一 HAMi-core 隔离层；切换分配 API 不会自动升级隔离强度。

## D5 · 失败边界

| 失败点 / 可见影响 | API、节点或 Operator 自动恢复边界 | 需要人工确认 / 修复的情况 |
|---|---|---|
| NFD 状态陈旧：labels/topology 与节点不符 | worker 恢复扫描、master 更新与 GC 清理可重新收敛；消费者需等待新观测 | 检查 worker 权限、feature source、规则和节点实际硬件；修复标签来源，不能只反复调度 |
| Operator operand 未就绪：driver/toolkit/plugin/validator 阻塞 | reconcile 可重建或更新所管理对象并持续报告 conditions | 内核/driver 不兼容、镜像/权限、安装模式冲突或外部 runtime 配置需修复；重建 Pod 不能保证硬件恢复 |
| Device Plugin 注册、Allocate 或 health 失败：资源消失/容器无法启动 | plugin 按实现重注册，kubelet 更新健康和 allocatable，并重试相应启动路径 | 检查 socket/API 版本、NVML/driver、资源名争用及 Allocate 错误；运行中 GPU 故障可能需要节点处置或重建 workload |
| ResourceSlice / Claim 状态漂移：库存过期、设备无匹配或 allocation 不一致 | driver 发布新库存、scheduler/controller 重读与重试可处理暂时不同步 | 错 driver/device identity、pool generation、selector 或存量 Claim 与硬件变化冲突需核对；不盲改已分配 Claim status |
| Binding conditions 等待超时：设备已选但 Pod 未绑定 | scheduler 依条件和超时路径结束本次尝试、清理相应保留状态并重试 | 外部准备 controller、状态权限或条件协议永久失败需要修复；单纯延长超时不产生设备就绪 |
| NodePrepare / CDI / checkpoint 错误：Pod 已绑定但不能启动或清理 | kubelet/plugin 对可重试错误重试，driver 按自身 checkpoint 恢复节点状态；Operator 可恢复受管进程 | 核对 CDI runtime/spec、checkpoint 与真实设备状态；不直接删除 checkpoint/finalizer 来掩盖未完成清理 |
| MIG / VFIO / ComputeDomain 部分变更：API 与节点/IMEX 状态不一致 | 各 driver/controller 按支持的幂等与恢复路径重算；API 重试本身不回滚硬件修改 | 按模式检查 MIG 实例、驱动绑定、IMEX/域成员；必要时排空节点后人工修复，评估其他消费者影响 |
| HAMi annotation 交接失败：reservation 与 Allocate 进度不一致 | scheduler/device-plugin 依协议更新 pending allocation 与完成状态，可重试的 API 错误按实现恢复 | 检查版本、编码、目标节点、锁/缓存和设备状态；不能伪造 success 或仅重写注解当作已分配 |
| 隔离或 overcommit 不符预期：OOM、抢占干扰或尾延迟恶化 | 配额记账与进程重启不能自动修复软件拦截绕过、配置错误或硬件容量不足 | 验证 HAMi-core 注入、调用兼容性、共享倍率与真实负载；按隔离目标调整配置或设备模式 |

失败矩阵是按职责归纳的排障边界，不承诺所有实现都可自动恢复。先判断故障停在 API 记账、节点准备、组件生命周期还是容器隔离，再对照 D2–D4 和具体 driver 的 conditions、events、日志与设备状态。

## 一句话分层

| 层 | 代表项目 | 要解决的问题 |
|---|---|---|
| 节点发现 | [[node-feature-discovery]] | 发布能力标签、规则结果与拓扑信号，供 placement/operator 使用 |
| 驱动与节点软件栈 | [[gpu-operator]], NVIDIA container toolkit, DCGM | 节点怎样安装、升级和暴露 GPU 软件栈 |
| 设备暴露 | [[k8s-device-plugin]], Intel device plugins, host device plugin | kubelet 如何发现并分配专用设备 |
| 声明式设备分配 | [[kubernetes-dra]], [[dra-driver-nvidia-gpu]] | Pod 如何声明更复杂的设备需求和分配结果 |
| Runtime 注入 | [[cdi]], NVIDIA container toolkit | 怎样把已分配设备的 runtime 配置交给容器引擎 |
| GPU sharing / vGPU | [[hami]], Volcano vGPU, gpushare, vgpu-scheduler | 多租户如何切分、调度和隔离 GPU |
| 调度与队列 | [[kueue]], [[scheduler-plugins]], autoscaler | GPU batch / AI workload 如何排队和扩缩 |
| 观测与诊断 | DCGM exporter, GPUd, fake-gpu | 怎么发现 GPU 健康、利用率和测试调度逻辑 |

## 核心项目边界

### [[node-feature-discovery]]

NFD 提供 worker/master、topology-updater 与 GC，发布硬件/系统能力、规则标签及资源拓扑。它帮助 scheduler 和 Operator 识别节点，不维护每个 Pod 的设备 allocation，也不替代 Device Plugin 或 DRA driver。

### [[k8s-device-plugin]]

NVIDIA 官方 GPU device plugin 是传统路径的基线：通过 NVML/CUDA discovery 向 kubelet gRPC 注册 `nvidia.com/gpu` 等资源，并在 Allocate 阶段用 env、volume、CDI 等方式交接设备配置。它可提供配置支持的 MIG/time-slicing/MPS 资源暴露，但不负责 driver 生命周期、完整多租户治理或模型 serving。

### [[gpu-operator]]

GPU Operator 是生产集群运维入口：传统 `ClusterPolicy` / `NVIDIADriver` 路径管理 driver、container toolkit、device plugin、DCGM、MIG manager、validator 等组件；当前 `GPUCluster` 提供另一条 DRA 管理路径，依赖独立 driver/runtime 准备。它解决“节点 GPU 软件栈怎样持续正确”，不决定单次 Pod 获得哪块设备。

### [[hami]]

HAMi 是 GPU sharing / vGPU 方向的重要样本。它通过 webhook、scheduler extender、device plugin 和多厂商 device abstraction，把 GPU 显存、算力、切分和调度策略放到 K8s 资源模型旁边。它解决“多个 workload 如何共享 GPU”，但也带来调度、隔离、观测和兼容性的复杂度。

### [[dra-driver-nvidia-gpu]]

NVIDIA DRA driver 把设备库存与节点准备接入 `ResourceClaim` / `ResourceSlice` 分配模型，GPU 与 ComputeDomain 路径具有各自生命周期。基础 DRA 已稳定，但动态设备、sharing、VFIO 等能力仍需按 Kubernetes 扩展和厂商 release 分别评估，不能无条件替代现有 device plugin 部署。

## 和 LLM serving 的关系

[[llm-inference]] 会把 GPU 资源层进一步拉进架构设计：

- Prefill/Decode 分离要求不同 GPU 池承担不同负载。
- KV cache offload 让显存、CPU 内存、NVMe 和网络都成为资源决策。
- LoRA / adapter serving 需要更细的内存与模型资产管理。
- GPU sharing 会影响 tail latency，不能只看平均利用率。
- DRA/CDI 会影响 serving operator 如何把“设备分配结果”交给 runtime。

所以 GPU stack 不应只作为运维背景，而应和 [[llm-d]]、[[aibrix]]、[[kserve]]、[[gpustack]]、[[kubeai]]、[[kueue]]、[[node-feature-discovery]] 等项目分层比较，区分 model serving、准入与节点发现。

## 选型提示

- 生产 NVIDIA GPU 集群基础栈：先看 [[gpu-operator]] + [[k8s-device-plugin]]。
- 多租户共享和 vGPU：看 [[hami]]，同时关注隔离和性能尾延迟。
- 下一代设备 API：看 [[kubernetes-dra]] + [[dra-driver-nvidia-gpu]] + [[cdi]]。
- LLM serving 平台：GPU 栈只是底座，还需要 [[llm-inference]]、[[inference-routing]]、[[model-serving-operator]] 和可观测能力。
