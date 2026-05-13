---
title: agent-sandbox 架构与设计思路分析
tags: [architecture, k8s-operator, ai-infra, agent-sandbox, sig-apps]
date: 2026-05-13
sources: [agent-sandbox-architecture-analysis.md]
related: [[agent-sandbox]], [[HiClaw]], [[k8s-operator]], [[gvisor]], [[kata-containers]], [[declarative-agent-management]], [[agent-credential-isolation]]
---

# agent-sandbox 架构与设计思路分析

> 原文：`raw/agent-sandbox-architecture-analysis.md` · 仓库：[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox) · 分析版本 v0.4.5+11 (HEAD `e1d8898`)

## 一句话定位

`kubernetes-sigs/agent-sandbox` 是 **K8s SIG Apps 官方孵化**的 Sandbox [[k8s-crd|CRD]] 与 controller，把 AI Agent runtime 那种"长寿命、有状态、单实例、可暂停、有稳定身份"的容器形态建模成第一类 K8s 资源——比 [[kubernetes|Deployment]]（无状态副本）和 [[kubernetes|StatefulSet]]（编号 Pod）都更精准。核心手段：1 个 `Sandbox` CR = 1 个 Pod + 1 个 headless Service + 持久 PVC + 可选 `Template`/`Claim`/`WarmPool` 三件套，**隔离机制（[[gvisor|gVisor]]/[[kata-containers|Kata]]/[[network-policy|NetworkPolicy]]）完全委托给标准 K8s 原语**，controller 只做生命周期编排。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              用户 / AI Agent 进程                              │
│                                                                              │
│   kubectl YAML        ▼ Go SDK (clients/go)        ▼ Python SDK             │
│                                                                              │
└─────────────┬────────────────────────┬──────────────────────┬────────────────┘
              │                        │                      │
              ▼ (apply)                ▼ (RPC / kubectl exec) ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Kubernetes API Server                              │
│                                                                             │
│  Group: agents.x-k8s.io/v1alpha1            Group: extensions.agents...     │
│  ┌──────────────────┐                       ┌───────────────────────┐       │
│  │  Sandbox  (CR)   │ ◄───── owns ────────  │  SandboxClaim     (CR)│       │
│  │                  │                       │   (user-friendly)     │       │
│  │  Spec:           │ ◄── owns (pre-warm) ──┤                       │       │
│  │   PodTemplate    │                       └──────────┬────────────┘       │
│  │   VolumeClaim... │                                  │ references         │
│  │   ShutdownTime   │       ┌───────────────────┐      │                    │
│  │   ShutdownPolicy │       │ SandboxWarmPool   │      ▼                    │
│  │   Replicas (0|1) │       │  Spec:            │     ┌──────────────────┐  │
│  └────────┬─────────┘       │   Replicas: N     │     │ SandboxTemplate  │  │
│           │                 │   TemplateRef     │────►│  Spec:           │  │
│           │                 │   UpdateStrategy  │     │   PodTemplate    │  │
│           │                 └─────────┬─────────┘     │   VolumeClaim... │  │
│           │                           │ owns          │   NetworkPolicy  │  │
│           │                           │ N×Sandbox     │   EnvVarsPolicy  │  │
│           │                           ▼               └──────────────────┘  │
│           │              (pre-warmed Sandboxes 等候被 Claim 领养)            │
└───────────┼─────────────────────────────────────────────────────────────────┘
            │ watch + reconcile
            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│           agent-sandbox-controller (cmd/agent-sandbox-controller)            │
│           ┌──────────────────────────────────────────────────────┐           │
│           │  SandboxReconciler (always)                          │           │
│           │  + SandboxClaimReconciler   (--extensions=true)      │           │
│           │  + SandboxTemplateReconciler  ↑                      │           │
│           │  + SandboxWarmPoolReconciler  ↑                      │           │
│           │  + SimpleSandboxQueue (per-template FIFO O(1) adopt) │           │
│           └────────────────────────┬─────────────────────────────┘           │
└────────────────────────────────────┼─────────────────────────────────────────┘
                                     │ creates / owns
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  Kubelet 节点                                                                 │
│  ┌─────────────────────────┐    ┌────────────────────────────────────┐      │
│  │  Pod  (1:1 per Sandbox) │ ←─►│  Service (ClusterIP=None, headless) │      │
│  │  ┌───────────────────┐  │    │   ⇒ {sandbox}.{ns}.svc.cluster.local│      │
│  │  │ container         │  │    └────────────────────────────────────┘      │
│  │  │ runtimeClassName: │  │    ┌────────────────────────────────────┐      │
│  │  │   gvisor / kata   │◄─┤    │ PVC: {tplname}-{sandboxname}        │      │
│  │  │   / runc          │  │    │   (持久存储，Sandbox 重启不丢)        │      │
│  │  └───────────────────┘  │    └────────────────────────────────────┘      │
│  └─────────────────────────┘    ┌────────────────────────────────────┐      │
│                                 │ NetworkPolicy (Template-shared)     │      │
│                                 │  默认 deny + 仅放行公网 egress       │      │
│                                 │  (deny RFC1918 + metadata server)   │      │
│                                 └────────────────────────────────────┘      │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 | 职责 |
|----|------|
| **CRD 定义层** | 4 个 CRD 的 Go 类型 + kubebuilder 标注 → `controller-gen` 自动生成 YAML。Spec/Status 即 API 契约。 |
| **Reconciler 层** | controller-runtime 风格的 4 个 reconciler。watch + owns + 幂等 reconcile。Claim/WarmPool/Template 通过 `--extensions=true` 开关启用。 |
| **运行时支持** | 绝对时间 + TTL 过期计算、Prometheus 指标、per-template-hash 的 FIFO 领养队列（O(1) WarmPool adopt）。 |
| **入口二进制** | 单二进制 `agent-sandbox-controller`，flags 控制 extensions 开关、leader election、并发度、OTel tracing、pprof。 |
| **Client SDK** | Go / Python / 标准 K8s clientset。Go SDK 提供远程 exec、文件传输、gateway 隧道、追踪注入——给 AI Agent runtime 调用 Sandbox 用。 |
| **打包** | Helm chart（CRDs / RBAC / Deployment / metrics Service）+ 单独的 `k8s/crds/` 给手工 kubectl apply。 |
| **示例与集成** | 17 个 `examples/`：hello-world / kata-gke / openclaw / hermes / langchain / jupyter / vscode / chrome / HPA / Kueue / Cilium。"读完 examples 就会用"。 |

**分层关键约束**：`api/` 与 `extensions/api/` 是被 K8s API server 直接读的契约，只能改不能删；`internal/` 严格私有；`controllers/` 不允许 import `extensions/`（核心稳定、扩展演进的边界）。

## 关键数据流

```
   t=0       用户 kubectl apply Sandbox 或 SandboxClaim
              │
              ▼
   ┌─────────────────────────┐
   │ apiserver 收到 CR       │
   └────────────┬────────────┘
                │ watch event
                ▼
   ┌────────────────────────────────────────────────────────┐
   │ Reconcile(sandbox) — controllers/sandbox_controller.go │
   │  ├─ checkSandboxExpiry      (line 1003)                │
   │  ├─ reconcilePVCs           (line 853)  ──► 创建 PVC    │
   │  ├─ reconcilePod            (line 531)                 │
   │  │    ├─ 如果有 SandboxPodNameAnnotation：              │
   │  │    │    └─ 走"warm pool 领养"分支，复用现有 Pod      │
   │  │    └─ 否则 Create Pod {sandbox.Name}                │
   │  ├─ reconcileService        (line 398)  ──► 创建        │
   │  │    └─ headless Service (ClusterIP=None)             │
   │  ├─ 算 Conditions (Ready/Finished)                     │
   │  └─ Update Status + requeueAfter(min(timeLeft, 2s))    │
   └────────────────────────────┬───────────────────────────┘
                                │
                                ▼
   ┌─────────────────────────────────────────────────────┐
   │ Pod 起来 → 容器内 Agent runtime (OpenClaw/Hermes/…) │
   │                                                     │
   │ AI Agent 进程 ←── SDK (gateway/tunnel/exec) ─────── │ ← 外部 caller
   │ (在 gVisor / Kata 内运行，宿主机内核被隔离)          │
   └─────────────────────────────────────────────────────┘
                                │
                                │ t = ShutdownTime（绝对时间）
                                ▼
   ┌─────────────────────────────────────────────────────┐
   │ handleSandboxExpiry (line 922)                      │
   │   ├─ ShutdownPolicy=Retain (default): 删 Pod+Svc，   │
   │   │    保留 Sandbox CR (status 显示 expired)         │
   │   └─ ShutdownPolicy=Delete: 整个 Sandbox 也删掉      │
   └─────────────────────────────────────────────────────┘
```

### SandboxClaim 快/慢路径

```
   user kubectl apply SandboxClaim
        │
        ▼
   SandboxClaimReconciler.getOrCreateSandbox  (sandboxclaim_controller.go:320)
        │
        ├─►【快路径】adoptSandboxFromCandidates (line 719)
        │     query SimpleSandboxQueue[templateHash]
        │     找到 1 个 WarmPool 已就绪的 Sandbox
        │     ├─ patch: 清掉 WarmPool 的 OwnerReference
        │     └─ patch: 把 Claim 设为新 owner   ≈ 0 启动延迟
        │
        └─►【慢路径】createSandbox (line 385)
              没找到 / WarmPoolPolicy=none / 自定义 env (跟 warmpool 不兼容)
              ├─ 读 SandboxTemplate
              ├─ 复制 PodTemplate + VolumeClaimTemplates
              ├─ 注入 claim 的额外 env / labels
              ├─ SetControllerReference(claim, sandbox)
              └─ Create Sandbox CR  ≈ Pod 冷启动延迟（秒级）
```

## 设计决策与哲学

- **为什么不复用 Deployment / StatefulSet**：AI Agent runtime 既不像 Deployment 那样无状态可副本（Agent 有会话状态），也不像 StatefulSet 那样需要编号有序（每个 sandbox 是独立用户实例）。需要的是 **"1 个 stable identity + 持久存储 + 可调度销毁 + 可暂停可恢复"的单实例语义**——Pet 概念在云原生的回归，但这次明确为 AI Agent runtime 量身定做。`replicas: 0|1` 强制约束就是"暂停 = scale to 0、恢复 = scale to 1"语义的承载。

- **隔离机制全部委托标准 K8s 原语**：controller 不强制任何隔离手段——[[gvisor|gVisor]] / [[kata-containers|Kata]] / `securityContext` / `serviceAccount` / `seccomp` 都在用户填写的 `PodTemplate.Spec` 里，原样透传。controller 唯一**强势注入**的是 (1) headless Service 强制走 DNS（多 sandbox 才能各自有稳定身份），(2) Template 级的默认 [[network-policy|NetworkPolicy]]（deny RFC1918 内网 + deny 云元数据服务）。这种"机制由 K8s 提供、策略由用户挑选"的分工，让它能兼容 GKE Kata、EKS Firecracker、本地 gVisor 任何隔离基座。这条与 [[ai-agent-plugin-patterns|AI Agent 外挂设计原则]]里"隔离用现成机制、不重新发明"完全吻合。

- **WarmPool + OwnerReference 转移实现 ~0 启动延迟**：单纯 Sandbox 冷启动慢（镜像拉取 + Kata/gVisor 初始化数秒到数十秒）。WarmPool 维护 N 个 pre-warmed Sandbox，Claim 来了**不是新建 Pod，而是把 Ready 的 Pod 改归属者**。`SimpleSandboxQueue` 是 per-template-hash 的线程安全 FIFO，O(1) 找候选。`sandboxclaim_pod_exclusivity_test.go` 这个测试名直白地说明 handoff 历史上踩过"1 个 Sandbox 对 2 个 Pod / 幽灵 Pod"的坑。

- **声明式 NetworkPolicy 而非隐式 firewalling**：Template 级别声明 `Managed`/`Unmanaged`。Managed 默认就是严格 deny——明确把"AI Agent 跑用户输入的代码必须默认禁掉内网访问 + 云元数据访问"做成系统约束，而不是文档里的最佳实践。

- **PVC 不被 Sandbox 标为 owned**：Sandbox 删除时 PVC 不级联回收，保留用户数据——"数据生命周期 ≠ 工作负载生命周期"做成了第一类设计。代价是孤儿 PVC 需要外部清理策略。

- **绝对时间 ShutdownTime，无心跳续约**：expiry 是声明式的，客户端要长寿命就主动 patch `shutdownTime`。controller 只做"现在 ≥ shutdownTime 就清理"的判断。避免 server 端维护"上次心跳时间"的状态，但代价是客户端要负责续期。

- **CRD validation 而非 webhook**：没有 admission webhook，全靠 OpenAPI v3 schema validation + controller 幂等 reconcile。少一个组件 = 少一个故障点——典型 SIG-style 的"简单优先"。

## 关键组件深入解读

### SandboxReconciler 的三阶段子资源 reconcile

`Reconcile()` 主流程的工程亮点不在于复杂，而在于**幂等三步永远按同一顺序**：`reconcilePVCs` → `reconcilePod` → `reconcileService`。每一步内部都是 "Get → Create or Adopt or Validate ownership → Patch labels/annotations" 的三步式幂等。Service **一定是 headless**（`ClusterIP: None`），selector 用 `agents.x-k8s.io/sandbox-name-hash=<hash>`（hash 防止 sandbox 名过长触碰 K8s label 63 字符上限）。这导致每个 Sandbox 自动有 DNS A record：`{sandbox}.{ns}.svc.{clusterDomain}`——成为 Sandbox "稳定身份"承诺的实现基础。

`requeueAfter = max(timeLeft, 2s)` 是个被反复琢磨的小细节：既避免热循环打爆 apiserver，又保证即将过期的 Sandbox 准时被清理，不依赖 informer event。

### SandboxClaimReconciler 的 adoption 协议

这是 extensions 子系统最有意思的代码，~60 行实现了 "WarmPool → Claim 的所有权热迁移"：

1. 从 `SimpleSandboxQueue` 拿到候选 Sandbox 名（已 Ready 的）；
2. **乐观锁 patch**：用 `OptimisticLockErrorMsg` resourceVersion 保护，避免两个并发 Claim 抢同一个 Sandbox；
3. 清掉 WarmPool 标识标签；
4. **OwnerReferences 置换**：移除 WarmPool 的 controller ref，加 Claim 的 controller ref——后续删 WarmPool 不会再级联删这个 Sandbox；
5. Claim status 记录 `AdoptedSandboxName`，下次 reconcile 走 short-circuit。

关键不变量是 4 + 5 必须原子（同一个 patch 请求里）。这就是 `sandboxclaim_pod_exclusivity_test.go` 守护的不变量。

## 与同类对比

| 维度 | agent-sandbox | [[HiClaw]] | 普通 K8s Deployment |
|------|--------------|------------|---------------------|
| 抽象层级 | **基础设施**（Sandbox 原语） | **应用层**（Manager + Workers 协作） | 基础设施（无状态副本） |
| 单实例 + 稳定身份 | ✅（核心设计目标） | ⚠️（Worker 之间通过 Matrix 房间） | ❌ |
| 持久存储 | ✅ | ✅（MinIO + PVC） | ❌ |
| 多 Agent 编排 | ❌（单 sandbox，多 sandbox 靠上层） | ✅（Team/Manager CRD） | ❌ |
| WarmPool 预热 | ✅ | ❌ | ❌ |
| 隔离机制 | **委托** K8s（gVisor/Kata 任选） | Higress 网关 + [[agent-credential-isolation\|凭据隔离]] | 取决于 runtimeClass |
| 治理 | K8s SIG Apps 官方孵化 | 阿里 Higress 团队开源 | K8s core |

**定位结论**：agent-sandbox 与 [[HiClaw]] **互补不竞争**。前者提供"安全运行 1 个有状态 Agent 容器"的基础设施；后者提供"管 N 个 Agent 协作 + IM 平面 + 凭据网关"的应用层。理论上 HiClaw 的 Worker runtime 完全可以跑在 agent-sandbox 之上——一个用 Sandbox 做隔离底座，一个用 Worker CRD 做协作上层。这种分层正是云原生生态的健康样态。

## 相关页面

- [[HiClaw]] — 应用层多 Agent 协作平台（与本项目互补）
- [[k8s-operator]] — 本项目所遵循的 controller pattern
- [[declarative-agent-management]] — 用 K8s CRD 声明式管理 AI Agent 的方法论
- [[agent-credential-isolation]] — 凭据零暴露设计模式（HiClaw 用，本项目不直接处理）
- [[ai-agent-plugin-patterns]] — AI Agent 外挂的 9 条设计原则
