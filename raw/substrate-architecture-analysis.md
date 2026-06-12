# Agent Substrate 架构与设计思路分析

> 仓库：https://github.com/agent-substrate/substrate · 分析日期：2026-06-12 · 版本：HEAD `a3f4474`（2026-06-11，Use link-local actor veth addresses）· 获取方式：GitHub codeload tarball（git clone 因 HTTP/2 / 443 连接失败，已用 GitHub API 校验 HEAD）

## 一句话定位

`agent-substrate/substrate` 是一个建立在 Kubernetes 之上的高密度 agent-like workload substrate：Kubernetes 只负责声明式容量和基础设施，Actor 的高频生命周期、resume/suspend、worker 分配和路由唤醒由 Substrate 自己的 Redis/ValKey 控制面、Envoy ext_proc router、atelet node supervisor 和 gVisor ateom worker 承担。

它和 `agent-sandbox` 的差异在于抽象层级：`agent-sandbox` 把一个有状态 sandbox 做成 K8s CRD 原语；Substrate 则试图把大量 idle actor multiplex 到较少 warm worker 上，通过 golden snapshot、runtime snapshot、DNS/router 唤醒和 gVisor restore 降低激活延迟。官方 architecture 文档也明确标注“Much of this architecture is aspirational”，所以本分析区分愿景和当前代码实现。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Users / higher-level agent frameworks                                        │
│                                                                              │
│  HTTP request to <actor-id>.actors.resources.substrate.ate.dev               │
│  kubectl ate create/resume/suspend/logs                                      │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ atenet router                                                                │
│                                                                              │
│  CoreDNS stub domain → Envoy → ext_proc                                      │
│  parse actor id from host → ResumeActor(actor_id) → rewrite :authority       │
│  to worker pod IP:80                                                         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ gRPC Control API
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ateapi control plane                                                         │
│                                                                              │
│  Control service: CreateActor / ResumeActor / SuspendActor / DeleteActor     │
│  SessionIdentity service: mint stable JWT / mTLS cert for migrating actor    │
│  Redis/ValKey: actor:<id>, worker:<ns>:<pool>:<pod>, lock:actor:<id>         │
│  ActorWorkflow: idempotent resume/suspend steps + forward recovery           │
└───────────────┬──────────────────────────────────────────────┬───────────────┘
                │ Kubernetes informers / CRD listers           │ gRPC AteomHerder
                ▼                                              ▼
┌──────────────────────────────────────┐        ┌──────────────────────────────┐
│ atecontroller                         │        │ atelet DaemonSet             │
│                                      │        │                              │
│ WorkerPool → privileged ateom pods   │        │ fetch verified runsc         │
│ ActorTemplate → golden actor         │        │ pull images / build OCI      │
│ golden actor resume → wait → suspend │        │ upload/download snapshots    │
│ status.goldenSnapshot = snapshot URI │        │ call ateom over Unix socket  │
└──────────────────────────────────────┘        └──────────────┬───────────────┘
                                                               │ gRPC Ateom
                                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ateom-gvisor worker pod                                                      │
│                                                                              │
│  privileged pod, one active actor at a time                                  │
│  link-local veth: pod netns ateom0 ↔ actor netns eth0                        │
│  nftables DNAT/MASQ compatibility bridge                                     │
│  runsc create/start/checkpoint/restore pause + app containers                │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Object storage snapshots                                                     │
│                                                                              │
│  gs:// or s3:// prefix                                                        │
│  checkpoint.img.zstd / pages.img.zstd / pages_meta.img.zstd                  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| CRD / public API | `pkg/api/v1alpha1/{workerpool,actortemplate}_types.go` · `pkg/proto/ateapipb/ateapi.proto` | 定义 `WorkerPool`、`ActorTemplate` 和 actor lifecycle gRPC API。K8s CRD 承载低频配置，gRPC 承载高频 actor 操作。 |
| K8s controller | `cmd/atecontroller/main.go` · `internal/controllers/*_controller.go` | 把 `WorkerPool` 物化为 privileged ateom Deployment；把 `ActorTemplate` 驱动成 golden actor → golden snapshot → Ready。 |
| Control plane / DB | `cmd/ateapi/main.go` · `cmd/ateapi/internal/controlapi/*` · `cmd/ateapi/internal/store/ateredis/` | 对外提供 Control / SessionIdentity gRPC；用 Redis/ValKey 存 actor/worker 状态和 lock；用 workflow step 实现 resume/suspend forward recovery。 |
| Node supervisor | `cmd/atelet/main.go` · `cmd/atelet/oci.go` | 每节点/每 worker 管理 runsc、镜像拉取、OCI bundle、snapshot 上传下载，并转调 ateom。 |
| Sandbox herder | `cmd/ateom-gvisor/*` | privileged worker pod 内的 gVisor 控制进程，串行调用 `runsc create/start/checkpoint/restore`，管理 actor netns/veth/nftables。 |
| Router / DNS | `cmd/atenet/internal/app/router/*` · `internal/dns/*` | 用 CoreDNS stub domain + Envoy xDS + ext_proc，把 actor hostname 转成 ResumeActor 调用和 worker pod IP 转发。 |
| CLI / demos / benchmarking | `cmd/kubectl-ate` · `demos/` · `benchmarking/` | 用户入口、样例 workload 和性能测试工具。 |

关键边界：Kubernetes API 不存每个高频 actor transition；`WorkerPool`/`ActorTemplate` 是声明式配置，`Actor`/`Worker` 的运行状态在 Redis/ValKey，真正 runsc 操作在 worker pod 本地完成。

## 关键数据流

### 1. ActorTemplate 到 golden snapshot

```
ActorTemplate CR created
        │
        ▼
atecontroller ActorTemplateReconciler
        │  PhaseInitial
        ▼
ateapi.CreateActor(goldenActorID)
        │
        ▼
status.phase = ResumeGoldenActor
        │
        ▼
ateapi.ResumeActor(goldenActorID)
        │  no actor snapshot + no golden snapshot
        ▼
atelet.Run → ateom.RunWorkload → runsc create/start
        │
        ▼
wait 20s
        │
        ▼
ateapi.SuspendActor(goldenActorID)
        │
        ▼
atelet.Checkpoint → ateom.CheckpointWorkload → upload checkpoint files
        │
        ▼
ActorTemplate.status.goldenSnapshot = snapshot URI
ActorTemplate.status.phase = Ready
```

当前代码里 `ActorTemplateReconciler` 的状态机很直接：Initial 阶段创建 golden actor，ResumeGoldenActor 阶段调用 `ResumeActor`，WaitGoldenActor 阶段等待 20 秒后调用 `SuspendActor`，最后把返回 actor 的 `LastSnapshot` 写入 `status.goldenSnapshot` 并置 Ready（`internal/controllers/actortemplate_controller.go:70-150`）。代码里也有 TODO 指出如果 golden actor resume 时 ateom/atelet 未就绪，可能泄露一个认为自己已被分配的 worker（`internal/controllers/actortemplate_controller.go:93-96`）。

### 2. 请求唤醒和路由

```
HTTP request
Host: <actor-id>.actors.resources.substrate.ate.dev
        │
        ▼
CoreDNS stub domain routes to atenet-router
        │
        ▼
Envoy RequestHeaders ext_proc
        │
        ▼
parseActorID(host)
        │
        ▼
singleflight ResumeActor(actor-id)
        │
        ▼
ateapi resume workflow
        │
        ├─ LoadActorForResume
        ├─ AssignWorker
        ├─ CallAteletRestore / Run
        └─ FinalizeRunning
        │
        ▼
actor.ateom_pod_ip returned
        │
        ▼
mutate :authority to <worker-ip>:80
        │
        ▼
Envoy dynamic_forward_proxy forwards request
```

`ExtProcServer.handleRequestHeaders` 从 `:authority` / `host` 解析 actor id，调用 `ActorResumer.ResumeActor`，拿到 `actor.AteomPodIp` 后把 target 固定为 `<workerIP>:80` 并改写 `:authority`（`cmd/atenet/internal/app/router/extproc.go:125-174`）。这意味着当前 router 的核心能力是 on-demand activation + 目标改写；端口仍硬编码 80，代码 TODO 明确还未支持多端口（`cmd/atenet/internal/app/router/extproc.go:161-162`）。

### 3. Resume / Suspend workflow

```
ResumeActor(actor-id)
        │
        ▼
Acquire lock: lock:actor:<id>
        │
        ▼
Load actor + ActorTemplate
        │
        ▼
Find existing assigned worker or random free worker
        │
        ▼
Update worker(actor_id=...) then actor(status=RESUMING, worker fields)
        │
        ▼
if actor.last_snapshot: atelet.Restore(last_snapshot)
else if template.goldenSnapshot and !boot: atelet.Restore(goldenSnapshot)
else: atelet.Run(template spec)
        │
        ▼
Update actor(status=RUNNING)

SuspendActor(actor-id)
        │
        ▼
Acquire lock: lock:actor:<id>
        │
        ▼
Load actor + ActorTemplate
        │
        ▼
Mark actor SUSPENDING + in_progress_snapshot
        │
        ▼
atelet.Checkpoint(snapshot URI)
        │
        ▼
Free worker, move in_progress_snapshot → last_snapshot,
clear worker fields, status=SUSPENDED
```

`RunWorkflow` 把 workflow 拆成 `IsComplete` / `Execute` / `RetryBackoff` 三段，失败后依赖客户端重试继续推进；`AssignWorkerStep` 在 Redis 里先更新 worker，再更新 actor，带版本检查和指数退避（`cmd/ateapi/internal/controlapi/workflow.go:35-112`，`cmd/ateapi/internal/controlapi/workflow_resume.go:79-141`）。这不是事务性 saga，而是针对 Redis Cluster 限制做的 forward recovery。

## 设计决策与哲学

- **K8s 管低频配置，Substrate 管高频 actor 状态**：官方文档把 Kubernetes API server 从 critical path 移出；代码也只把 `WorkerPool` 和 `ActorTemplate` 建成 CRD，actor/worker 运行状态进入 Redis/ValKey。Redis store 注释明确说明 `actor:<id>` 与 `worker:<ns>:<pool>:<pod>` 是状态真相，并解释 Redis Cluster 不能跨 slot 原子更新 actor 和 worker（`cmd/ateapi/internal/store/ateredis/ateredis.go:15-39`）。
- **Golden snapshot 是冷启动优化根**：`ActorTemplate` 不是简单模板，而会由 controller 创建一个 golden actor，启动后等待 20 秒再 suspend 成 golden snapshot，后续 actor 可从模板快照恢复，而不是每次重新拉镜像/跑初始化（`internal/controllers/actortemplate_controller.go:70-150`）。
- **Resume/suspend 采用 client-driven forward recovery**：`WorkflowStep` 明确要求每步可判断是否完成，执行失败后停止并依赖客户端重试；每个 actor 还有 `lock:actor:<id>` 防同 actor 并发操作（`cmd/ateapi/internal/controlapi/workflow.go:35-57`，`cmd/ateapi/internal/controlapi/workflow.go:135-184`）。
- **worker 是 warm capacity，不是 actor 本体**：`WorkerPoolReconciler` 只根据 `WorkerPool.spec.replicas` 创建 privileged `ateom` Deployment，worker pod 通过 `POD_UID` 和 hostPath `/run/ateom` 为 atelet/ateom 通信提供承载（`internal/controllers/workerpool_controller.go:119-167`）。
- **gVisor/runsc 是当前 snapshot 执行后端**：`atelet` 负责 runsc 下载、校验、OCI bundle 和 snapshot 文件传输；`ateom-gvisor` 串行调用 runsc `create/start/checkpoint/restore`。`ateom` 代码用 mutex 明确假设 runsc 子命令不能并发（`cmd/ateom-gvisor/main.go:155-180`）。
- **网络唤醒先做兼容桥，不是最终策略层**：当前 ateom 在 worker pod netns 与 actor netns 之间创建 link-local veth，nftables 做 actor egress masquerade 和 worker pod IP:80 DNAT；注释明确说后续 AgentGateway 阶段应替换为透明 TCP capture 和 default-deny 规则（`cmd/ateom-gvisor/main.go:59-67`，`cmd/ateom-gvisor/main.go:330-396`）。
- **稳定 session identity 还处于骨架阶段**：`SessionIdentity` 能签 session JWT / cert，但代码里多处 TODO 表示还未把 incoming K8s identity 与 session DB 做完整交叉校验（`cmd/ateapi/internal/sessionidentity/sessionidentity.go:59-118`，`cmd/ateapi/internal/sessionidentity/sessionidentity.go:124-142`）。

## 关键组件深入解读

### ateapi ActorWorkflow（`cmd/ateapi/internal/controlapi/workflow*.go`）

`ActorWorkflow` 是当前源码里最能体现 Substrate 设计哲学的部分。它不是写一个大函数完成 resume/suspend，而是把流程拆成可跳过的步骤：resume 依次加载 actor、分配 worker、调用 atelet restore/run、最终置 running；suspend 依次加载 actor、标记 suspending、调用 atelet checkpoint、释放 worker 并提交 snapshot。

这个拆法服务于两个现实约束。第一，actor 与 worker 状态跨 Redis Cluster key，不可能用一个强事务同时修改；第二，调用 atelet/ateom/runsc 是外部副作用，失败可能发生在任意位置。因此 workflow 采用“状态已写入就能被下一次请求识别并继续”的模型。`AssignWorkerStep` 会先查是否已有前次失败留下的 worker assignment，再随机挑空闲 worker；`CallAteletRestoreStep` 根据 actor snapshot、template golden snapshot、boot 参数三选一。它的代价是状态机复杂度上升，必须在每个步骤里认真写 `IsComplete` 和版本检查。

### atelet + ateom-gvisor（`cmd/atelet/main.go`，`cmd/ateom-gvisor/main.go`）

`atelet` 和 `ateom` 的分工很清楚：atelet 是 node supervisor，接收 ateapi 的 Run/Checkpoint/Restore 请求；ateom 是 worker pod 内的 gVisor herder，真正执行 runsc。atelet 负责“重 I/O 和准备工作”：下载/校验 runsc、拉 OCI image、展开 rootfs、生成 OCI config、下载/上传 checkpoint zstd 文件。ateom 负责“进程和 netns 现场”：创建 interior network namespace、建立 veth、安装 nftables、执行 runsc create/start/checkpoint/restore。

这个分层把慢速镜像/对象存储操作留在 atelet，把对 runsc 状态机敏感的操作留在 ateom，并且通过 `target_ateom_uid` 防止请求打到错误 worker。当前实现假设一个 worker pod 同时只运行一个 active actor；ateom 的 `lock sync.Mutex` 和 nftables 表清理逻辑都体现了这一点。

### atenet router（`cmd/atenet/internal/app/router/*`）

`atenet` 把 Envoy 作为可配置流量入口，但它没有实现一个完整 AI gateway；当前关键逻辑集中在 ext_proc request headers 阶段。请求 host 必须形如 `<actor-id>.actors.resources.substrate.ate.dev`，router 解析 actor id 后调用 ateapi `ResumeActor`，再根据返回的 worker pod IP 把 `:authority` 改写为 `<workerIP>:80`。`ActorResumer` 用 `singleflight` 合并同进程内的并发 resume 请求，并对 gRPC `Aborted` 做退避重试。

DNS controller 则把 actor suffix stub 到 Substrate 自己的 DNS/router，使用户和上层系统不需要知道 worker pod IP。这个路径是 Substrate “actor-aware routing” 的最小实现：先唤醒，再路由。

## 与同类对比

| 维度 | Agent Substrate | agent-sandbox | AgentCube | OpenShell |
|------|-----------------|---------------|-----------|-----------|
| 核心抽象 | Actor / WorkerPool / ActorTemplate | Sandbox / SandboxClaim / WarmPool | AgentRuntime / CodeInterpreter session | 私有安全 runtime / gateway desired state |
| 高频状态 | Redis/ValKey actor/worker keys | K8s CRD + Pod/PVC 状态 | Redis/ValKey session registry + K8s sandbox | Gateway/object store/sandbox supervisor |
| 激活方式 | Resume snapshot 到 warm worker | Claim/warm pool 领取 sandbox | Router 创建/复用 agent-sandbox | Gateway/CLI 编排 sandbox |
| 隔离后端 | 当前 gVisor runsc | 用户通过 PodTemplate 选择 gVisor/Kata 等 | 复用 agent-sandbox | OpenShell supervisor/policy proxy |
| 路由 | Envoy ext_proc 唤醒 + worker IP 改写 | 上层自建 | AgentCube Router session affinity | inference.local / gateway proxy |

Substrate 更激进：它试图把“许多 idle actor”从 K8s 对象层拿出来，靠 snapshot 和 warm worker 做密度/延迟优化；代价是要自建控制面、状态一致性、网络、快照和身份体系。

## 性能 / 资源开销

官方 architecture 文档给出的 north star metrics 是 activation latency p95 100ms、单集群 1B actor、1000 wakeup/s，但当前源码没有完整 benchmark 结果证明这些指标已达成。仓库包含 `benchmarking/locust` 和 workload 模板，说明性能测试基础已存在；`docs/observability.md` 列出 `atenet.router.route.duration`、`rpc.server.call.duration`、`atelet.snapshot.size` 等核心指标。

当前实现的主要性能优化点：

- WorkerPool 预先运行 privileged ateom pods，避免每次走 K8s scheduler。
- ActorTemplate golden snapshot 捕获初始化后状态，避免重复冷启动。
- atelet 并行准备 pause/app OCI bundles，并并行下载 snapshot side files。
- atenet 用 singleflight 合并同 actor 并发 resume。

主要成本/瓶颈：

- 每个 worker 当前一次只跑一个 active actor。
- Snapshot 读写依赖对象存储和 zstd 文件传输。
- Redis/ValKey 是 actor/worker 状态中心，需要处理 cluster slot 和拓扑变化。
- Router 当前按 worker IP:80 转发，多端口和更复杂流量策略尚未实现。

## 安全模型

安全边界目前分成四层：

1. **K8s / privileged worker 边界**：WorkerPool controller 创建 privileged root ateom pod，并挂载 hostPath `/run/ateom`。这是强能力组件，必须作为基础设施可信组件对待。
2. **gVisor sandbox 边界**：实际 workload 在 runsc 管理的 pause + app containers 中运行，checkpoint/restore 依赖 gVisor 能保存/恢复状态。
3. **Control API / DB 边界**：ateapi gRPC、Redis/ValKey 和 actor lock 是生命周期一致性的核心；Redis store 注释已经明确跨 key 原子性不足是设计约束。
4. **Session identity 边界**：SessionIdentity 目标是给会迁移的 actor 发稳定 JWT / mTLS cert，但当前代码仍有 TODO：尚未从 incoming JWT 抽取 K8s identity，也尚未把请求 session 与 session DB 完整校验。

当前显著风险：

- `atecontroller` 连接 ateapi 的 TLS config 仍使用 `InsecureSkipVerify: true` 并有 TODO（`cmd/atecontroller/main.go`）。
- `atenet` 到 ateapi 也使用跳过校验的 TLS config。
- `ateom` 当前 nftables 规则是兼容桥，注释明确还不是最终 default-deny egress policy。
- Golden actor 状态机里存在已标注的 worker leak TODO。
