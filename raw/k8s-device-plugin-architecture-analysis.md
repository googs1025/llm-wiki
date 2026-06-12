# NVIDIA k8s-device-plugin 架构与设计思路分析

> 仓库：https://github.com/NVIDIA/k8s-device-plugin · 分析日期：2026-06-12 · 版本：HEAD `8688949`（2026-06-10）

## 一句话定位

NVIDIA 官方 Kubernetes device plugin，把节点上的 GPU/MIG/vGPU 发现为 kubelet extended resources，并在 Allocate 阶段通过 env、volume-mounts 或 CDI annotations 把设备传给容器。它是 GPU 暴露的基础层，上层 GPU Operator/HAMi/DRA 都会和它形成互补或替代关系。

## 分析范围

仓库 11238 文件/162MB，超过 5000 文件；分析聚焦 cmd/internal/api 核心，未阅读 vendor/tests 全量内容。 本次使用 GitHub API 元数据和默认分支 tarball 重新拉取源码，而不是只从既有文章或 star snapshot 推断。

## 核心架构图

```
┌────────────────── NVIDIA GPU Node ──────────────────┐
│ NVML / CUDA / Tegra / VFIO / MIG / IMEX / MPS         │
└──────────────┬───────────────────────────────────────┘
               │ discovery strategy
               v
┌────────────────────────────┐
│ resource manager            │
│ devices, health, allocation │
└──────────────┬─────────────┘
               │ per resource
               v
┌────────────────────────────┐      ┌───────────────────┐
│ device plugin gRPC server   │<────>│ kubelet            │
│ Register/List/Allocate      │      │ DevicePlugin API   │
└──────────────┬─────────────┘      └───────────────────┘
               │ device list strategy
               v
┌───────────────────────────────────────────────────────┐
│ container envvar / volume-mounts / CDI annotations     │
└───────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|------|------|------|
| CLI/config | cmd/nvidia-device-plugin/main.go, api/config/v1 | 解析 MIG strategy、device-list strategy、CDI/MPS/IMEX/driver root 等配置。 |
| Plugin manager | cmd/nvidia-device-plugin/plugin-manager.go | 解析 discovery strategy，创建 CDI handler、resource manager 和 per-resource plugin。 |
| Resource manager | internal/resource, internal/rm | 基于 NVML/CUDA/Tegra/VFIO 发现设备，处理 MIG/resource mapping、preferred allocation、health。 |
| Device plugin server | internal/plugin/server.go | 实现 kubelet device plugin gRPC：Serve/Register/ListAndWatch/Allocate/PreStart。 |
| Feature discovery/MPS | cmd/gpu-feature-discovery, cmd/mps-control-daemon, internal/lm | 提供 GPU label、MPS daemon 和 node feature discovery 集成。 |

这套分层的关键是：入口层负责交互和配置，核心层负责稳定的领域模型或控制循环，适配层吸收外部系统差异。选型时优先看这个项目把复杂性放在哪里：CLI 插件类项目通常把复杂性放在状态/进程管理，Kubernetes/GPU 项目则把复杂性放在 reconcile、scheduler、kubelet/plugin 和硬件状态同步。

## 关键数据流

```
Node starts nvidia-device-plugin DaemonSet
  │
  ├─ main parses config/env flags and selected discovery strategy
  │
  ├─ plugin-manager creates CDI spec and resource managers
  │
  ├─ per-resource plugin registers Unix socket with kubelet
  │
  ├─ ListAndWatch reports healthy GPU/MIG resources
  │
  └─ Allocate validates request and returns env/mount/CDI device edits
```

错误与回退路径主要来自三个位置：外部依赖不可用、状态持久化与真实运行状态不一致、以及上游 API/平台能力变化。源码中通常通过 allowlist、checkpoint、health check、fallback manager、job state 或 controller condition 暴露这些异常，而不是把异常吞掉。

## 设计决策与哲学

- **保持 kubelet device plugin API 的基础语义**：项目核心是发现、健康检查和 Allocate，不承担全局调度或多租户策略。
- **多种 device list strategy 兼容不同 runtime**：envvar、volume-mounts、CDI annotations 并存，让老 runtime 和新 CDI 工作流都能接入。
- **resource manager 隔离硬件发现差异**：`internal/resource/factory.go` 按 NVML/Tegra/VFIO 选择 manager，plugin server 不直接关心硬件细节。

## 关键组件深入解读

### 核心入口与状态层

NVIDIA k8s-device-plugin 的入口层并不只是命令包装：它承担了“把用户意图变成内部状态机输入”的职责。对 coding-agent 工具来说，这通常意味着解析 slash command/CLI flag、定位 workspace、维护 job/session state；对 Kubernetes GPU 项目来说，这意味着读取 CRD/Pod/ResourceClaim、启动 informer/controller 或 kubelet plugin，然后把外部对象转成内部 reconcile/resource manager 状态。

### 适配层与边界

这个项目最值得关注的是适配边界：它既要保留上游系统的原生语义，又要把差异归一给自己的核心层。代码中的 adapter、resource manager、provider proxy、viewer/export、CDI handler、platform plugin 等目录就是这些边界的体现。边界做得越薄，项目越适合作为基础设施组件；边界做得越厚，项目通常提供更完整的产品体验，但也更容易绑定具体平台。

## 与同类对比

| 维度 | NVIDIA k8s-device-plugin | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | 官方 GPU device plugin 基础层 | GPU Operator: 部署管理它 | HAMi: 共享调度/虚拟化扩展 |
| API | Kubelet DevicePlugin v1beta1 | Operator CRD | scheduler extender + annotations |
| 粒度 | GPU/MIG/MPS/time-slicing/CDI | 软件组件栈 | memory/core/count 共享 |

## 性能 / 资源开销

本次未跑基准测试。可从源码结构推断：CLI/trace/analytics 项目主要开销在本地文件扫描、代理转发、SQLite 写入和 viewer 渲染；Kubernetes/GPU 项目主要开销在 informer cache、controller reconcile、device health check、NVML/CDI 查询和 DaemonSet/sidecar 常驻资源。

## 安全模型

安全边界取决于项目类型：coding-agent bridge/插件类项目直接连接本地工作区、agent 凭证和外部消息/插件入口，应重点审计 command execution、token/job state、trace 数据和聊天平台 allowlist；GPU/Kubernetes 项目则应重点审计 webhook 权限、CRD validation、RBAC、privileged DaemonSet、hostPath、device node 暴露和 checkpoint/annotation 篡改。
