# DRA Driver for NVIDIA GPUs 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/dra-driver-nvidia-gpu · 分析日期：2026-06-12 · 版本：HEAD `749a743`（2026-06-11）

## 一句话定位

NVIDIA GPU 的 Kubernetes Dynamic Resource Allocation driver，围绕 ResourceClaim/ResourceSlice、NodePrepareResources、ComputeDomain/Multi-Node NVLink 和动态 MIG/VFIO 配置展开。它代表 K8s 新一代设备分配模型，而不是传统 device plugin API 的增量补丁。

## 分析范围

仓库 5849 文件/74MB，超过 5000 文件；分析收敛到 cmd/api/pkg 核心，未阅读 vendor/site 全量内容。 本次使用 GitHub API 元数据和默认分支 tarball 重新拉取源码，而不是只从既有文章或 star snapshot 推断。

## 核心架构图

```
┌──────────────── Kubernetes DRA API ────────────────┐
│ ResourceClaim / ResourceSlice / ClaimParameters     │
└───────────────┬───────────────────────┬─────────────┘
                │ validate              │ scheduler assigns claim
                v                       v
┌────────────────────────┐   ┌────────────────────────┐
│ validating webhook      │   │ gpu-kubelet-plugin      │
│ strict config decoder   │   │ NodePrepare/Unprepare   │
└────────────────────────┘   └──────────────┬─────────┘
                                             │ checkpoint + resource slices
                                             v
┌────────────────────────┐   ┌────────────────────────┐
│ DeviceState             │<─>│ NVML/MIG/VFIO/CDI      │
│ prepared full/mig/vfio  │   │ concrete device config │
└────────────────────────┘   └────────────────────────┘
                │
                │ ComputeDomain path
                v
┌────────────────────────┐   ┌────────────────────────┐
│ compute-domain-controller│→ │ daemon / IMEX / clique │
└────────────────────────┘   └────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|------|------|------|
| DRA kubelet plugins | cmd/gpu-kubelet-plugin, cmd/compute-domain-kubelet-plugin | 实现 kubelet DRA plugin，发布 ResourceSlice，执行 Prepare/Unprepare 和 checkpoint 清理。 |
| GPU state/config | cmd/gpu-kubelet-plugin/device_state.go, prepared.go, mig.go, vfio-device.go | 抽象 full GPU、MIG、VFIO、sharing、checkpoint 与资源 slice。 |
| ComputeDomain 控制面 | cmd/compute-domain-controller, cmd/compute-domain-daemon | 管理 ComputeDomain/Clique 生命周期，动态渲染 daemonset 与 IMEX primitives。 |
| API 与 webhook | api/nvidia.com/resource/v1beta1, cmd/webhook | 定义 GpuConfig/MigDeviceConfig/ComputeDomain 等配置，并验证 ResourceClaim 参数。 |
| 部署与站点 | deployments/helm, site/content, demo/specs | Helm/demo/docs 展示 K8s 1.32+ DRA 使用方式。 |

这套分层的关键是：入口层负责交互和配置，核心层负责稳定的领域模型或控制循环，适配层吸收外部系统差异。选型时优先看这个项目把复杂性放在哪里：CLI 插件类项目通常把复杂性放在状态/进程管理，Kubernetes/GPU 项目则把复杂性放在 reconcile、scheduler、kubelet/plugin 和硬件状态同步。

## 关键数据流

```
Workload consumes ResourceClaim
  │
  ├─ webhook validates strict nvidia.com resource config payload
  │
  ├─ DRA scheduler selects ResourceSlice/device allocation
  │
  ├─ kubelet calls NodePrepareResources on gpu-kubelet-plugin
  │
  ├─ driver locks prepare/unprepare, creates MIG/VFIO/CDI/checkpoint state
  │
  └─ NodeUnprepare cleans checkpoint and dynamic device incarnation
```

错误与回退路径主要来自三个位置：外部依赖不可用、状态持久化与真实运行状态不一致、以及上游 API/平台能力变化。源码中通常通过 allowlist、checkpoint、health check、fallback manager、job state 或 controller condition 暴露这些异常，而不是把异常吞掉。

## 设计决策与哲学

- **接受 DRA 的声明式 claim 模型**：资源配置进入 ResourceClaim，而不是 Pod annotation；这把厂商调度逻辑接到 Kubernetes 1.32+ DRA 语义上。
- **checkpoint 是动态设备生命周期的事实来源**：`NewDriver` 在 DynamicMIG 下会清理未知 MIG devices，避免重启后静态/动态状态混乱。
- **GPU 和 ComputeDomain 分成两个插件/控制面**：ComputeDomain 面向 Multi-Node NVLink/IMEX，GPU 面向本机 device allocation，生命周期和风险边界不同。

## 关键组件深入解读

### 核心入口与状态层

DRA Driver for NVIDIA GPUs 的入口层并不只是命令包装：它承担了“把用户意图变成内部状态机输入”的职责。对 coding-agent 工具来说，这通常意味着解析 slash command/CLI flag、定位 workspace、维护 job/session state；对 Kubernetes GPU 项目来说，这意味着读取 CRD/Pod/ResourceClaim、启动 informer/controller 或 kubelet plugin，然后把外部对象转成内部 reconcile/resource manager 状态。

### 适配层与边界

这个项目最值得关注的是适配边界：它既要保留上游系统的原生语义，又要把差异归一给自己的核心层。代码中的 adapter、resource manager、provider proxy、viewer/export、CDI handler、platform plugin 等目录就是这些边界的体现。边界做得越薄，项目越适合作为基础设施组件；边界做得越厚，项目通常提供更完整的产品体验，但也更容易绑定具体平台。

## 与同类对比

| 维度 | DRA Driver for NVIDIA GPUs | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | K8s DRA NVIDIA driver | k8s-device-plugin: beta device plugin API | HAMi: scheduler extender vGPU sharing |
| 资源 API | ResourceClaim/ResourceSlice | extended resource + kubelet plugin | Pod annotation + extender |
| 高级能力 | dynamic MIG/VFIO/ComputeDomain | MIG/MPS/time-slicing/CDI | memory/core sharing + heterogeneous vendors |

## 性能 / 资源开销

本次未跑基准测试。可从源码结构推断：CLI/trace/analytics 项目主要开销在本地文件扫描、代理转发、SQLite 写入和 viewer 渲染；Kubernetes/GPU 项目主要开销在 informer cache、controller reconcile、device health check、NVML/CDI 查询和 DaemonSet/sidecar 常驻资源。

## 安全模型

安全边界取决于项目类型：coding-agent bridge/插件类项目直接连接本地工作区、agent 凭证和外部消息/插件入口，应重点审计 command execution、token/job state、trace 数据和聊天平台 allowlist；GPU/Kubernetes 项目则应重点审计 webhook 权限、CRD validation、RBAC、privileged DaemonSet、hostPath、device node 暴露和 checkpoint/annotation 篡改。
