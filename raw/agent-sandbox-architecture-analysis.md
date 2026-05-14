# agent-sandbox 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/agent-sandbox · 分析日期：2026-05-13 · 版本：v0.4.5+11 (HEAD `e1d8898`)

## 一句话定位

`kubernetes-sigs/agent-sandbox` 是 **K8s SIG Apps 官方孵化**的 Sandbox CRD 与 controller，把 AI Agent runtime 那种"长寿命、有状态、单实例、可暂停、有稳定身份"的容器形态建模成第一类 K8s 资源——比 Deployment（无状态副本）和 StatefulSet（编号 Pod）都更精准。核心手段：1 个 Sandbox CR = 1 个 Pod + 1 个 headless Service + 持久 PVC + 可选 Template/Claim/WarmPool 三件套，**隔离机制（gVisor/Kata/NetworkPolicy）完全委托给标准 K8s 原语**，controller 只做生命周期编排。

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

| 层 | 主要文件 / 目录 | 职责 |
|----|----------------|------|
| **CRD 定义层** | `api/v1alpha1/sandbox_types.go` · `extensions/api/v1alpha1/{sandboxclaim,sandboxtemplate,sandboxwarmpool}_types.go` | 4 个 CRD 的 Go 类型 + kubebuilder 标注 → `controller-gen` 生成 `helm/crds/*.yaml` 和 `k8s/crds/*.yaml`。**Spec/Status 即 API 契约**。 |
| **Reconciler 层** | `controllers/sandbox_controller.go`（核心 1000+ 行）· `extensions/controllers/sandbox{claim,template,warmpool}_controller.go` | controller-runtime 风格的 4 个 reconciler。watch + owns + 幂等 reconcile。Claim/WarmPool/Template 全部在 `--extensions=true` 时启用。 |
| **运行时支持** | `internal/lifecycle/expiry.go` · `internal/metrics/` · `extensions/controllers/queue/simple_sandbox_queue.go` | 通用工具：绝对时间 + TTL 过期计算、Prometheus 指标、per-template-hash 的 FIFO 领养队列（O(1) WarmPool adopt）。 |
| **入口二进制** | `cmd/agent-sandbox-controller/main.go` | 单二进制 `agent-sandbox-controller`。flags 控制 extensions 开关、leader election、concurrent workers、metrics/probes 端口、OTel tracing、pprof。 |
| **Client SDK** | `clients/go/sandbox/`（client/commands/files/gateway/tunnel/tracing）· `clients/python/`（codegen 生成）· `clients/k8s/`（kube-style clientset+informer+lister） | 给 AI Agent runtime 调用 Sandbox 的高层 SDK：远程 exec、文件传输、gateway 隧道、追踪注入。Python SDK 通过 `codegen.go` 自动生成。 |
| **打包** | `helm/{crds,templates}/` · `k8s/crds/` · `Dockerfile` | Helm chart（含 CRDs / RBAC / Deployment / metrics Service）。`helm/crds/` 与 `k8s/crds/` 内容一致，前者给 Helm 用，后者给手工 kubectl apply。 |
| **示例与集成** | `examples/`（17 个）· `extensions/examples/` | hello-world、kata-gke、openclaw、hermes、langchain、jupyter、vscode、chrome、HPA scaling、Kueue、Cilium policy 等真实场景。 |
| **文档与治理** | `docs/keps/` · `site/`（Hugo）· `OWNERS` · `SECURITY.md` · `RELEASE.md` · `roadmap.md` | KEP 风格的设计提案、官网内容、SIG Apps 治理样板。 |

**分层关键约束**：
- `api/` 与 `extensions/api/` 是被 K8s API server 直接读的契约——只能改不能删，废弃要走 v1alpha1 → v1beta1 → v1 的弃用流程（已经在 `examples/kueue-agent-sandbox` 用 v1beta2 看到征兆）。
- `internal/` 严格私有，外部项目不能 import；`clients/` 反过来是公开 SDK，签名稳定性高。
- `controllers/` **不允许 import `extensions/`**（核心不依赖扩展），但 `extensions/controllers/` 可以 import 核心 API 类型。这种"核心稳定、扩展演进"的边界是 SIG Apps 项目的标配。

## 关键数据流

### 端到端数据流：从 `kubectl apply` 到 Agent runtime 跑起来

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

**错误传递与回退**：
- `reconcilePod` 找到一个被**别的 owner 占用**的同名 Pod → 直接报错回退，不强抢（`controllers/sandbox_controller.go` 的 ownership-aware adoption 逻辑）。
- `reconcilePVCs` 出错 → 整个 reconcile fail，requeue with exponential backoff（controller-runtime 默认 5ms→1000s）。
- expiry 检查必发生在 reconcile 入口：即便其它 step 出错，也保证过期清理路径优先走通。
- requeue 时间被 clamp 到 ≥2s（line 1017），避免热循环打爆 apiserver。

### Claim 快/慢路径

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

**关键不变量**：Claim 自定义 env vars → 强制走慢路径（warm pool 是"未 personalized"的，无法在不重启 Pod 的前提下注入用户 env）。这条规则同时也限制了 EnvVarsInjectionPolicy 的语义边界。

## 设计决策与哲学

- **为什么不复用 Deployment / StatefulSet**（`api/v1alpha1/sandbox_types.go:114-140`）：AI Agent runtime 既不像 Deployment 那样无状态可副本（Agent 有会话状态），也不像 StatefulSet 那样需要编号有序（每个 sandbox 是独立用户的实例）。需要的是 **"1 个 stable identity + 持久存储 + 可调度销毁 + 可暂停可恢复" 的单实例语义**——Pet 概念在云原生的回归，但这次明确为 AI Agent runtime 量身定做。`replicas: 0|1` 强制约束（CRD validation 不允许其它值）正是"暂停 = scale to 0，恢复 = scale to 1"语义的承载。

- **隔离机制全部委托给标准 K8s 原语**（参 `examples/kata-gke-sandbox/sandbox-kata-gke.yaml:11`）：controller 不强制任何隔离手段——`runtimeClassName: gvisor` / `kata-qemu`、`securityContext`、`serviceAccount`、`seccomp` 都在用户填写的 `PodTemplate.Spec` 里，原样透传给 Pod。controller 唯一**强势注入**的是：(1) headless Service（`controllers/sandbox_controller.go:398` ClusterIP=None）强制走 DNS，多 sandbox 才能各自有稳定身份；(2) Template 级的默认 NetworkPolicy（`extensions/controllers/utils.go:22-46` deny RFC1918 内网 + deny 云元数据服务，仅放行公网 egress）。这种"机制由 K8s 提供、策略由用户挑选"的分工，让它能兼容 GKE Kata、EKS Firecracker、本地 gVisor 任何隔离基座。

- **WarmPool + OwnerReference 转移实现 ~0 启动延迟**（`extensions/controllers/sandboxclaim_controller.go:719` 的 `completeAdoption` + `extensions/controllers/queue/simple_sandbox_queue.go`）：单纯 Sandbox 冷启动慢（镜像拉取 + Kata/gVisor 初始化数秒到数十秒）。WarmPool 维护 N 个 pre-warmed Sandbox，Claim 来了**不是新建 Pod，而是把 Ready 的 Pod 改归属者**。`SimpleSandboxQueue` 是 per-template-hash 的线程安全 FIFO，O(1) 找到候选——明显是在 hot path 上做过性能优化。`sandboxclaim_pod_exclusivity_test.go` 这个测试名直白地说明 handoff 历史上踩过"1 个 Sandbox 对 2 个 Pod / 幽灵 Pod"的坑。

- **声明式 NetworkPolicy 而非隐式 firewalling**（`extensions/api/v1alpha1/sandboxtemplate_types.go` 的 NetworkPolicyManagement 字段）：Template 级别声明 `Managed`（controller 维护 NetworkPolicy）/ `Unmanaged`（用户用 Cilium 等接管）。Managed 默认就是严格 deny——明确把"AI Agent 跑用户输入的代码，必须默认禁掉内网访问 + 云元数据访问"作为 SDK 出厂安全姿态。这条决策是把"安全的 default"做成了系统约束，而不是文档里的最佳实践。

- **PVC 不被 Sandbox 标为 owned**（`controllers/sandbox_controller.go:853`）：故意的——Sandbox 删除时 PVC 不级联回收，保留用户数据。但孤儿 PVC 的清理需要外部策略（运维责任）。这是把"数据生命周期 ≠ 工作负载生命周期"做成了第一类设计。

- **绝对时间 ShutdownTime，无心跳续约**（`internal/lifecycle/expiry.go:47`）：expiry 是声明式的，客户端要长寿命就主动 patch `shutdownTime`。controller 只做 "现在 ≥ shutdownTime 就清理" 的判断。这避免了 server 端维护"上次心跳时间"的状态，但代价是客户端要负责续期。

- **CRD validation 而非 webhook**：没有 admission webhook，全靠 OpenAPI v3 schema validation（`replicas` 只能 0/1、`shutdownPolicy` 是 enum）+ controller 幂等 reconcile。少一个组件意味着少一个故障点，部署更简单——典型 SIG-style 的"简单优先"。

- **examples 即文档**：`examples/` 17 个目录覆盖 hello-world → kata-gke → openclaw → hermes → langchain → code-interpreter → jupyter → vscode → chrome → HPA scaling → Kueue 多租户 → Cilium policy。每个 example 都自带 README + YAML + 必要时 setup.sh，构成"读完 examples 就会用"的入门路径。

## 关键组件深入解读

### SandboxReconciler（`controllers/sandbox_controller.go`，~1100 行）

核心字段：`Client client.Client` · `Scheme *runtime.Scheme` · `Tracer trace.Tracer` · `ClusterDomain string`（默认 `cluster.local`）。

`Reconcile()` 主流程（line 148-228）：

1. **Fetch Sandbox**（line 151-158）：用 `client.IgnoreNotFound` 容忍删除事件——object 已不存在就是 noop。
2. **Expiry 优先**（line 197-208）：先调 `checkSandboxExpiry` (line 1003)。如果过期：(a) 立即把 `Ready=False, Reason=SandboxExpired` 写回，(b) 调 `handleSandboxExpiry` 清 Pod/Service，按 ShutdownPolicy 决定是否连 Sandbox CR 一起删。
3. **三阶段子资源 reconcile**（line 210）：`reconcilePVCs` → `reconcilePod` → `reconcileService`。每个阶段都是"Get → Create or Adopt or Validate ownership → Patch labels/annotations"的幂等三步。
4. **Pod 名解析**（line 558-561）：标准情况下 Pod 名 = Sandbox 名；如果 Sandbox annotation 里有 `SandboxPodNameAnnotation`（warm pool 领养场景），Pod 名 = annotation 值。这是 "warm pool 已经把 Pod 创好，Sandbox CR 后到" 的指针倒置。
5. **Service 一定是 headless**（line 398-508）：`ClusterIP: None`，selector 用 `agents.x-k8s.io/sandbox-name-hash=<hash>`（hash 防止 sandbox 名过长触碰 K8s label 63 字符上限）。这导致每个 Sandbox 自动有 DNS A record：`{sandbox}.{ns}.svc.{clusterDomain}`。
6. **Conditions** （line 269-355）：标准 metav1.Condition 列表，两种 type：`Ready`（Pod Running + Service 存在）、`Finished`（Pod Succeeded/Failed）。Reason 字段是机器可读的枚举（`DependenciesReady` / `PodSucceeded` / `SandboxExpired` 等）。
7. **Smart requeue**（line 211-215, 1017）：`requeueAfter = max(timeLeft, 2s)`。两个目的：(a) 避免热循环，(b) 即将过期的 Sandbox 准时被清理（不依赖 informer event）。
8. **OpenTelemetry 集成**（line 147-160, 1052-1057）：reconcile span 注入到 annotation，跨 reconcile 链路追踪——对调试"为什么这个 sandbox 第 4 次 reconcile 才 Ready" 极有价值。

`SetupWithManager()` 注册 watch：`For(&Sandbox)` · `Owns(&Pod{})` · `Owns(&Service{})`（filter by `sandbox-name-hash` label）。**故意不 own PVC**——理由见上文设计决策。

### SandboxClaimReconciler 的 adoption 协议（`extensions/controllers/sandboxclaim_controller.go:719` `completeAdoption`）

这是整个 extensions 子系统最有意思的代码，约 60 行实现了"WarmPool → Claim 的所有权热迁移"：

1. 从 `SimpleSandboxQueue` 拿到候选 Sandbox 名（已 Ready 的）。
2. **乐观锁 patch**：用 `OptimisticLockErrorMsg` resourceVersion 保护，避免两个并发 Claim 抢同一个 Sandbox。
3. **清掉 WarmPool 标识**：删除 `WarmPoolSandboxLabel`、`PodTemplateHashLabel`、`TemplateRefHashLabel`。
4. **OwnerReferences 置换**：移除 WarmPool 的 controller ref，加 Claim 的 controller ref。这一步走标准 K8s GC 语义——OwnerReference 改了之后，删 WarmPool 不会再删这个 Sandbox。
5. **Claim status 更新**：记录 `AdoptedSandboxName`，下次 reconcile 走 short-circuit 不重复领养。

关键不变量是 4 + 5 必须原子（同一个 patch 请求里），否则可能出现"WarmPool 以为没了 / Claim 以为还没领养"的双失态。这就是 `sandboxclaim_pod_exclusivity_test.go` 守护的不变量。

## 与同类对比

| 维度 | agent-sandbox | [[HiClaw]] | 普通 K8s Deployment | Anthropic Sandbox API (CodeExec) |
|------|--------------|------------|---------------------|----------------------------------|
| 抽象层级 | **基础设施**（Sandbox 原语） | **应用层**（Manager + Workers 协作） | 基础设施（无状态副本） | SaaS（黑盒 REST） |
| 单实例 + 稳定身份 | ✅（核心设计目标） | ⚠️（Worker 之间通过 Matrix 房间） | ❌（pod 名随机） | ✅（隐式） |
| 持久存储 | ✅（PVC + 跨重启） | ✅（MinIO + PVC） | ❌（用户自己 mount） | ⚠️（session 内） |
| 多 Agent 编排 | ❌（单 sandbox，多 sandbox 靠上层） | ✅（Team/Manager CRD） | ❌ | ❌ |
| WarmPool 预热 | ✅（OwnerRef 转移，~0 延迟） | ❌ | ❌ | ✅（实现细节不公开） |
| 隔离机制 | **委托** K8s（gVisor/Kata 任选） | 通过 Higress 网关 + 凭据隔离 | 取决于 runtimeClass | gVisor（hardcoded） |
| 治理 | K8s SIG Apps 官方孵化 | 阿里 Higress 团队开源 | K8s core | 闭源 |
| 部署方式 | Helm chart + CRD | Helm chart + k3s/kine 嵌入式 | kubectl | 不部署 |

**定位结论**：agent-sandbox 和 HiClaw 互补不竞争。agent-sandbox 提供"安全运行 1 个有状态 Agent 容器"的基础设施；HiClaw 提供"管 N 个 Agent 协作 + IM 平面 + 凭据网关"的应用层。理论上 HiClaw 的 Worker runtime 完全可以跑在 agent-sandbox 之上——一个用 Sandbox 做隔离底座，一个用 Worker CRD 做协作上层。

## 性能 / 资源开销

- **冷启动**：纯 Pod 模式 ~3-10s（镜像缓存 + runc）；gVisor 模式 +1-2s；Kata 模式 +3-5s（额外的 microVM 初始化）。这是为什么需要 WarmPool。
- **WarmPool 领养延迟**：从 Claim apply 到 status.Ready，本地 envtest 实测 < 200ms（主要是 reconcile 进队 + patch 一次的 RTT）。`test/benchmarks/` 目录已经在做 CSV 输出（PR #725），说明开始关注 SLO。
- **controller 内存**：单二进制 controller-runtime 进程，默认 informer cache 所有 Sandbox/Pod/Service。线上规模 10k Sandbox/cluster 时预估 ~500MB-1GB（典型 controller-runtime）。
- **API qps**：默认 `--kube-api-burst=10`，`--kube-api-qps` 不限（line 91, `main.go`）。大规模建议显式限流。
- **存储**：PVC 持久化策略由 StorageClass 决定，agent-sandbox 不强制——通常用 SSD CSI driver。

## 安全模型

**信任边界**：

```
   [外部 caller] ──tunnel/gateway──► [agent-sandbox SDK]
                                          │
                                          ▼ kube apiserver (RBAC)
                                          │
                                    [Sandbox CR] ─── owned by ───► [Pod]
                                                                    │
                                          NetworkPolicy ◄───────────┤
                                          (deny RFC1918, deny metadata)
                                                                    │
                                          runtimeClassName ◄────────┤
                                          (gVisor / Kata 隔离 host kernel)
                                                                    │
                                          ServiceAccount ◄──────────┤
                                          (limited RBAC, no token mount by default)
```

**已知风险与缓解**：

1. **untrusted code execution**（AI Agent 跑用户输入的代码）→ 建议组合 `runtimeClassName: gvisor` + 默认 NetworkPolicy。
2. **凭据泄漏**：默认 `AutomountServiceAccountToken: false`（`extensions/controllers/utils.go`），避免 Pod 内能调 K8s API。
3. **云元数据 SSRF**（典型 AWS IMDS / GCP metadata.google.internal 169.254.169.254）→ 默认 NetworkPolicy 已经 deny。
4. **PVC 残留**：Sandbox 删除不级联删 PVC，可能保留敏感数据——需要外部回收策略。
5. **WarmPool 串扰**：pre-warmed Sandbox 在被 Claim 领养前可能被 K8s exec 进去——RBAC 必须限制 exec 权限到"已领养的 Claim 拥有者"。
6. **缺少 admission webhook**：意味着 CRD validation 之外的策略（比如"禁止 hostNetwork"）需要用 Gatekeeper/Kyverno 外挂。

**这个项目不解决的安全问题**：身份认证（谁能 apply Sandbox 是 K8s RBAC 的事）、密钥管理（用 K8s Secret + CSI / Vault）、网络入口（用 Gateway API / Ingress）。一致的态度是"复用 K8s 生态既有方案，不重新发明"。

## 代码统计与演进信号

- Go 文件 ~140 个，主要在 `controllers/`、`extensions/controllers/`、`clients/go/sandbox/`。
- 测试覆盖：每个 controller 都有对应 `*_test.go` + `testmain_test.go` 用 envtest 跑真实 apiserver。`sandboxclaim_pod_exclusivity_test.go` 显示对竞争场景的回归测试。
- 近期 commit 主题（HEAD 20 commits）：
  - **生态集成**：Hermes Agent 持久化例子 (#774)、Kueue v1beta2 升级 (#737)、Cilium policy 例子。
  - **运维**：Release 自动化 (#741, #748)、Vertex AI 改 Gemini Notes (#783)。
  - **文档**：API doc (#247)、Golang quickstart (#730)、volumes guide (#731)、NetworkPolicy 管理文档 (#743)。
  - **基础**：PR template (#748)、Copilot instructions (#768)、benchmarks CSV 输出 (#725)。
- 整体信号：**alpha API 但工程化、文档化、社区治理在同步推进**——是 SIG 孵化项目典型的"进 beta 前最后冲刺"状态。
