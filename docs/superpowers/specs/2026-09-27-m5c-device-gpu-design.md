# M5-C Kubernetes Device / GPU 地图设计

## 背景

当前 `k8s-gpu-device-stack.md` 将 Device Plugin、GPU Operator、HAMi 和 NVIDIA DRA Driver 平铺分层，但没有完整解释节点发现、软件栈管理、设备分配、runtime 注入与 sharing/isolation 的差异，也容易让读者误以为 Device Plugin、DRA 和 HAMi 可以在同一节点上无条件叠加。

`kubernetes-dra-design-deep-dive.md` 已覆盖 ResourceClaim/ResourceSlice、scheduler 和 kubelet plugin，但形成于 2026-07，早于当前 DRA 稳定状态及 NVIDIA GPU Operator 的 `GPUCluster` 管理路径。

2026-09-27 当前官方仓库 HEAD：

- Node Feature Discovery `386fda4332ba`
- NVIDIA GPU Operator `60526e35efee`
- NVIDIA Kubernetes Device Plugin `86142cf1a93f`
- NVIDIA DRA Driver for GPUs `495bf4c59b94`
- HAMi `a2dd191b2e7f`
- Kubernetes `6c1c7702cf20`

这些是 dated default-branch snapshots，不是 release 标识。

## 目标

- 把 `k8s-gpu-device-stack.md` 建成 M5-C L1 入口。
- 区分 discovery、node software lifecycle、allocation、runtime injection 和 sharing/isolation。
- 明确 Device Plugin 与 DRA 两条 allocation 路径及共存限制。
- 重画 DRA 的 ResourceClaim → scheduler → kubelet → CDI 生命周期。
- 解释 HAMi scheduler、device plugin、annotation protocol 和 HAMi-core 的职责。
- 同步四个 Concept 与五个 Entity 的当前定位和证据边界。
- 保留历史 Source/ASCII 图；只有真实冲突才做双向 warning。

## 非目标

- 不在本 change 中展开 Workload/Kueue/Karpenter 主线；它们属于 M5-B。
- 不重画 HPA/KEDA/metrics；它们属于 M5-D。
- 不创建 M5 总 backbone。
- 不把 GPU Operator 当作单次 allocation 算法。
- 不把 CDI 当 scheduler 或 allocator。
- 不宣称 Device Plugin、DRA、HAMi 或多个 GPU device plugin 可以在同一节点无条件共存。
- 不把所有 DRA 扩展能力都标成 stable；基础 DRA 与各扩展 feature stage 分开表达。

## 页面范围

### Analysis

- `wiki/analysis/k8s-gpu-device-stack.md`
- `wiki/analysis/kubernetes-dra-design-deep-dive.md`

### Concept

- `wiki/concepts/device-plugin.md`
- `wiki/concepts/kubernetes-dra.md`
- `wiki/concepts/cdi.md`
- `wiki/concepts/gpu-sharing.md`

### Entity

- `wiki/entities/node-feature-discovery.md`
- `wiki/entities/gpu-operator.md`
- `wiki/entities/k8s-device-plugin.md`
- `wiki/entities/dra-driver-nvidia-gpu.md`
- `wiki/entities/hami.md`

### 导航和生成层

- 更新 `wiki/index.md` 和 `wiki/log.md`。
- 重建 `wiki/html/`、index 和 graph。

## D1：GPU Device Stack

```text
Discovery / capability
  NFD worker/master/topology-updater/GC
  → labels · NodeFeature · NodeFeatureRule · NodeResourceTopology
                  │ informs placement / operator policy
                  ▼
Node software lifecycle
  NVIDIA GPU Operator
  → driver · container toolkit · telemetry · allocation operands
                  │ choose allocation mode
        ┌─────────┴─────────┐
        ▼                   ▼
Device Plugin path       DRA path
ClusterPolicy            GPUCluster / DRA driver
extended resource        DeviceClass / ResourceSlice
kubelet Allocate         ResourceClaim allocation
env/mount/CDI            NodePrepare / CDI
```

当前 NVIDIA GPU Operator 文档中，`ClusterPolicy` 管理 Device Plugin 路线，`GPUCluster` 管理 DRA 路线；同一集群/节点的实际共存与迁移条件必须按目标 release 核验。

## D2：Device Plugin 路径

```text
Device plugin registers with kubelet
        │ advertise extended resource
        ▼
Node.status.capacity / allocatable
        │ Pod requests resource
        ▼
kube-scheduler filters Node capacity
        │ Pod bound
        ▼
kubelet calls Allocate
        │ env / mount / CDI annotation or devices
        ▼
container runtime starts workload
```

该路径的核心限制是 extended resource 粒度与 kubelet Allocate 接口；复杂 sharing、配置参数和 topology 往往需要额外 scheduler/annotations 或 vendor-specific logic。

## D3：Discovery 与 Operator 控制循环

```text
NFD worker detects CPU/kernel/PCI/topology
      - - publish - -> NodeFeature / labels / NodeResourceTopology
                              │
                              └ - consumed by - -> scheduler/operator/policy

GPU Operator desired policy
      - - reconcile - -> driver/toolkit/device allocation/telemetry operands
                              │ status / health
                              └ - feedback - -> ClusterPolicy or GPUCluster
```

Discovery 数据可能陈旧；Operator 负责组件生命周期，不决定每个 Pod 获得哪块 GPU。

## D4：DRA Resource 生命周期

```text
Driver publishes DeviceClass / ResourceSlice
Workload creates ResourceClaimTemplate / ResourceClaim
        │
        ▼
kube-scheduler filters/selects device and writes allocation
        │ optional binding conditions / PreBind wait
        ▼
Pod binds to compatible Node
        │
        ▼
kubelet → NodePrepareResources → DRA kubelet plugin
        │ generate/use CDI device assignment
        ▼
container runtime starts workload
        │ Pod termination
        ▼
NodeUnprepareResources / release / cleanup
```

基础 DRA 自 Kubernetes v1.35 stable。Device binding conditions、consumable capacity、partitionable devices、optional node operations、extended-resource translation 等能力必须分别标注 feature stage 和目标版本。

## Sharing / Isolation Overlay

HAMi 的默认路径跨越三个层：

- hami-scheduler / extender：选择节点与物理设备，计算 memory/core/count reservation。
- hami-device-plugin：向 kubelet 注册资源并在 Allocate 阶段读取 Pod annotation 完成设备交接。
- HAMi-core：在容器内拦截 runtime 调用，执行 memory/core isolation。

Pod annotation 是 scheduler 与 device plugin 的交接协议。当前 HAMi 文档建议同一节点避免 HAMi、Volcano vGPU 与 NVIDIA official device plugin 争用同一 GPU resource。HAMi-DRA 改变 allocation path，不等于自动替代 isolation layer。

## D5：失败边界

覆盖：

- NFD feature/label/topology 陈旧或 GC 不一致。
- GPU Operator operand、driver、toolkit、certificate 或 telemetry 未就绪。
- Device Plugin registration/ListAndWatch/Allocate 失败。
- extended resource capacity 与实际 device health 不一致。
- DRA ResourceSlice/Claim allocation 陈旧、binding condition timeout。
- NodePrepare/NodeUnprepare/checkpoint/CDI 注入失败。
- MIG/VFIO/ComputeDomain mutation 部分完成或恢复。
- HAMi scheduler annotation 与 device-plugin allocation state 不一致。
- sharing overcommit、isolation library 注入失败和 device health 变化。

每项必须区分 API 重试、node-local recovery、operator reconcile 和人工修复边界。

## DRA 下钻页面

`kubernetes-dra-design-deep-dive.md` 更新：

- 基础 DRA stable 状态与扩展 feature stage。
- ResourceClaim allocation 与 scheduler extension path。
- device binding conditions 与 PreBind wait。
- kubelet NodePrepare/Unprepare 与 CDI。
- device status、checkpoint、restart/recovery。
- NVIDIA DRA Driver 当前 GPUCluster/DeviceClass/ComputeDomain 位置。
- 与 Device Plugin、GPU Operator、Karpenter 的边界。

## Concept 同步

### Device Plugin

强调 registration、ListAndWatch、extended resource、Allocate、health；说明与 DRA 的差异和 coexistence 风险。

### Kubernetes DRA

标注基础 DRA stable since v1.35；扩展能力逐项标 feature stage，不再笼统写“未来路线”。

### CDI

CDI 是设备注入描述/运行时接口，不负责 scheduling 或 allocation；Device Plugin、DRA、Operator/HAMi 都可能产生或消费 CDI device assignment。

### GPU Sharing

区分 scheduling/accounting、allocation、hardware partitioning、runtime isolation：time-slicing、MPS、MIG、HAMi-core 等不能只按“是否共享”归为同一机制。

## 证据与冲突规则

- 实施时重新解析六个仓库 HEAD，并记录完整 commit 链接。
- Analysis/Entity 当前证据与 6–7 月 Source 快照分开。
- 基础 DRA stable 与扩展 feature stage 分开。
- NVIDIA repo/path、GPU Operator CRD 和管理模式变化要标明 snapshot。
- Source 若含与当前事实相反的未限定结论，在 Source 与当前页面同时加 Conflict warning；仅缺少新能力不算冲突。
- 历史 ASCII 图不重画、不压缩。

## 完成标准

- L1 页面包含 D1/D2/D3/D4/D5 和 Sharing/Isolation overlay。
- DRA 页面包含 claim、scheduler、binding、kubelet、CDI 的端到端图。
- 四个 Concept 与五个 Entity 都链接 M5-C L1/DRA 页面。
- 当前页面明确 Device Plugin、DRA 和 HAMi 的 ownership/coexistence 边界。
- DRA stable/alpha/beta 状态有目标版本证据。
- 所有改动 frontmatter 有效，无新增断链。
- raw 和历史 Source 不变，或只有经批准的双向 Conflict warning。
- Index/Log/HTML/graph 同步；手工 HTML 不变。
- 两次构建幂等，`git diff --check` 通过。

## 风险与控制

- **把 GPU Operator 当 allocator**：D1 单列 node software lifecycle。
- **把 Device Plugin 与 DRA 叠加**：两条 allocation path 分叉，并标注管理模式/资源名冲突。
- **把 CDI 当调度器**：CDI 只出现在 runtime injection 阶段。
- **把 sharing 与 isolation 混为一谈**：HAMi overlay 分三层。
- **把 DRA 扩展全部视为 stable**：DRA 页面建立 feature-stage 表。
- **状态漂移**：所有 current claim 带日期、commit、release/cluster-version caveat。

## 验证策略

- 校验 L1/DRA headings、fences、图例和纯文本图内标签。
- YAML parser 校验 11 个内容页。
- baseline-aware wikilink 与 HTML href/fragment 检查。
- 全局扫描 Device Plugin/DRA/HAMi ownership 和过时 feature-stage 表述。
- Source/raw/ASCII 保护检查。
- graph 节点/边/双向关联校验。
- HTML 两次构建与 diff hash 幂等检查。
- `git diff --check`。
