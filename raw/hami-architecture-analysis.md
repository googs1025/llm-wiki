# HAMi 架构与设计思路分析

> 仓库：https://github.com/Project-HAMi/HAMi · 分析日期：2026-06-12 · 版本：HEAD `5dca58e`（2026-06-11）

## 一句话定位

Kubernetes 异构 GPU sharing / vGPU 项目，通过 mutating webhook、scheduler extender、device plugin 和设备厂商后端，把 GPU memory/core/count 等细粒度配额写入 Pod 注解并在 Allocate 阶段兑现。它更像“共享调度与隔离层”，不是 NVIDIA 官方基础 device plugin 的简单替代。

## 分析范围

仓库 433 个文件；分析覆盖 scheduler、webhook、device abstraction、NVIDIA plugin 和 monitor；多厂商后端只做分层级概览。 本次使用 GitHub API 元数据和默认分支 tarball 重新拉取源码，而不是只从既有文章或 star snapshot 推断。

## 核心架构图

```
┌──────────────────── Kubernetes API ───────────────────┐
│ Pod with nvidia.com/gpu/gpumem/gpucores requests        │
└──────────────┬─────────────────────────────────────────┘
               │ admission
               v
┌──────────────────────────┐
│ HAMi mutating webhook     │
│ defaults, schedulerName,  │
│ quota/resource validation │
└──────────────┬───────────┘
               │ scheduler extender callbacks
               v
┌──────────────────────────┐      ┌──────────────────────┐
│ HAMi Scheduler            │<────>│ node/pod/quota cache │
│ filter, score, bind       │      │ annotations + locks  │
└──────────────┬───────────┘      └──────────────────────┘
               │ assigned device annotations
               v
┌──────────────────────────┐
│ HAMi device plugin        │
│ Allocate, env/CDI/hooks   │
└──────────────┬───────────┘
               v
┌──────────────────────────┐
│ Container runtime + GPU    │
│ memory/core isolation      │
└──────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|------|------|------|
| Webhook | pkg/scheduler/webhook.go, cmd/scheduler/main.go | 拦截 Pod admission，注入 schedulerName、默认 GPU memory/core/count、quota 检查。 |
| Scheduler extender | pkg/scheduler/*, pkg/scheduler/policy/* | 维护 node/pod/quota cache，提供 /filter /bind /score 路由和 binpack/spread 策略。 |
| 设备抽象 | pkg/device/*, pkg/device/nvidia/*, pkg/device/<vendor>/* | 多厂商设备注册、资源名、quota、annotation 编解码和打分逻辑。 |
| Device plugin | cmd/device-plugin, pkg/device-plugin/nvidiadevice/* | 对接 kubelet device plugin API，读取 node config，注册虚拟化资源，生成 env/CDI/挂载。 |
| Monitor/metrics | cmd/vGPUmonitor, pkg/monitor, pkg/metrics | 反馈容器内 GPU 使用、Prometheus 指标和调度可观测性。 |

这套分层的关键是：入口层负责交互和配置，核心层负责稳定的领域模型或控制循环，适配层吸收外部系统差异。选型时优先看这个项目把复杂性放在哪里：CLI 插件类项目通常把复杂性放在状态/进程管理，Kubernetes/GPU 项目则把复杂性放在 reconcile、scheduler、kubelet/plugin 和硬件状态同步。

## 关键数据流

```
Pod requests partial GPU resources
  │
  ├─ webhook validates non-privileged pod and mutates resource defaults
  │
  ├─ scheduler extender filters nodes by device/quota/annotation cache
  │
  ├─ score policy chooses node/GPU and writes allocation annotations
  │
  ├─ device plugin Allocate reads pending pod and node config
  │
  └─ runtime receives visible device/env/CDI/hook configuration
```

错误与回退路径主要来自三个位置：外部依赖不可用、状态持久化与真实运行状态不一致、以及上游 API/平台能力变化。源码中通常通过 allowlist、checkpoint、health check、fallback manager、job state 或 controller condition 暴露这些异常，而不是把异常吞掉。

## 设计决策与哲学

- **使用 scheduler extender 而不是只靠 device plugin**：GPU memory/core 共享需要调度时全局决策，单纯 kubelet Allocate 已经太晚。
- **annotation 是调度到分配的契约**：Scheduler 选择设备后通过 Pod/Node annotation 传递给 device plugin，降低对 kube-scheduler 内部扩展的侵入。
- **多厂商后端共享同一 device abstraction**：`pkg/device` 提供 NVIDIA/AMD/Ascend/Cambricon 等扩展点，HAMi 定位异构设备共享而非单厂商工具。

## 关键组件深入解读

### 核心入口与状态层

HAMi 的入口层并不只是命令包装：它承担了“把用户意图变成内部状态机输入”的职责。对 coding-agent 工具来说，这通常意味着解析 slash command/CLI flag、定位 workspace、维护 job/session state；对 Kubernetes GPU 项目来说，这意味着读取 CRD/Pod/ResourceClaim、启动 informer/controller 或 kubelet plugin，然后把外部对象转成内部 reconcile/resource manager 状态。

### 适配层与边界

这个项目最值得关注的是适配边界：它既要保留上游系统的原生语义，又要把差异归一给自己的核心层。代码中的 adapter、resource manager、provider proxy、viewer/export、CDI handler、platform plugin 等目录就是这些边界的体现。边界做得越薄，项目越适合作为基础设施组件；边界做得越厚，项目通常提供更完整的产品体验，但也更容易绑定具体平台。

## 与同类对比

| 维度 | HAMi | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | vGPU/GPU sharing 调度与隔离 | k8s-device-plugin: 官方 GPU 暴露 | GPU Operator: 软件栈生命周期管理 |
| 调度参与 | 强，webhook + extender + bind | 弱，主要 kubelet plugin | 间接，部署组件 |
| 资源粒度 | memory/core/count/厂商自定义 | GPU/MIG/MPS/time-slicing | driver/runtime/plugin/DCGM 组件 |

## 性能 / 资源开销

本次未跑基准测试。可从源码结构推断：CLI/trace/analytics 项目主要开销在本地文件扫描、代理转发、SQLite 写入和 viewer 渲染；Kubernetes/GPU 项目主要开销在 informer cache、controller reconcile、device health check、NVML/CDI 查询和 DaemonSet/sidecar 常驻资源。

## 安全模型

安全边界取决于项目类型：coding-agent bridge/插件类项目直接连接本地工作区、agent 凭证和外部消息/插件入口，应重点审计 command execution、token/job state、trace 数据和聊天平台 allowlist；GPU/Kubernetes 项目则应重点审计 webhook 权限、CRD validation、RBAC、privileged DaemonSet、hostPath、device node 暴露和 checkpoint/annotation 篡改。
