---
title: Agent Substrate 架构与设计思路分析
tags: [architecture, agent-runtime, sandbox, kubernetes, ai-infra]
date: 2026-06-12
sources: [substrate-architecture-analysis.md]
related: [[agent-runtime-sandbox-selection-map]], [[agent-runtime-sandbox-project-map]], [[agent-sandbox]], [[agentcube]], [[kubernetes]], [[agentgateway]], [[cloud-native-security]], [[declarative-agent-management]]
---

# Agent Substrate 架构与设计思路分析

> 原文：`raw/substrate-architecture-analysis.md` · 仓库：https://github.com/agent-substrate/substrate · 分析版本 HEAD `a3f4474`

## 一句话定位

Agent Substrate 是一个建立在 [[kubernetes]] 之上的高密度 [[agent-runtime-sandbox-selection-map|Agent Runtime / Sandbox]] substrate：Kubernetes 只负责声明式容量和基础设施，Actor 的高频生命周期、resume/suspend、worker 分配和路由唤醒由 Substrate 自己的 Redis/ValKey 控制面、Envoy ext_proc router、atelet node supervisor 和 gVisor ateom worker 承担。

它补的是 [[agent-sandbox]] 和 [[agentcube]] 之间更底层、更激进的一层：不是“创建一个有状态 sandbox”，而是把大量 idle actor multiplex 到较少 warm worker 上，通过 golden snapshot、runtime snapshot、DNS/router 唤醒和 gVisor restore 降低激活延迟。官方 architecture 文档也明确标注“Much of this architecture is aspirational”，所以要把愿景和当前代码实现分开看。

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

| 层 / 模块 | 职责 |
|----------|------|
| CRD / public API | 定义 `WorkerPool`、`ActorTemplate` 和 actor lifecycle gRPC API；K8s CRD 承载低频配置，gRPC 承载高频 actor 操作。 |
| K8s controller | 把 `WorkerPool` 物化为 privileged ateom Deployment；把 `ActorTemplate` 驱动成 golden actor → golden snapshot → Ready。 |
| Control plane / DB | 对外提供 Control / SessionIdentity gRPC；用 Redis/ValKey 存 actor/worker 状态和 lock；用 workflow step 实现 resume/suspend forward recovery。 |
| Node supervisor | 每节点/每 worker 管理 runsc、镜像拉取、OCI bundle、snapshot 上传下载，并转调 ateom。 |
| Sandbox herder | privileged worker pod 内的 gVisor 控制进程，串行调用 `runsc create/start/checkpoint/restore`，管理 actor netns/veth/nftables。 |
| Router / DNS | 用 CoreDNS stub domain + Envoy xDS + ext_proc，把 actor hostname 转成 ResumeActor 调用和 worker pod IP 转发。 |

关键边界：[[kubernetes]] API 不存每个高频 actor transition；`WorkerPool`/`ActorTemplate` 是声明式配置，`Actor`/`Worker` 的运行状态在 Redis/ValKey，真正 runsc 操作在 worker pod 本地完成。

## 关键数据流

### ActorTemplate 到 golden snapshot

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

### 请求唤醒和路由

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

### Resume / Suspend workflow

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

## 设计决策与哲学

- **K8s 管低频配置，Substrate 管高频 actor 状态**：`WorkerPool`/`ActorTemplate` 是 CRD，actor/worker 运行态进入 Redis/ValKey。Redis store 注释明确说明跨 slot 不能原子更新 actor 和 worker，所以系统必须接受 forward recovery。
- **Golden snapshot 是冷启动优化根**：`ActorTemplate` 会生成一个 golden actor，启动后暂停成 snapshot；后续 actor 可从 golden snapshot 恢复，而不是每次重新跑初始化。
- **Resume/suspend 采用 client-driven forward recovery**：每个 workflow step 都能判断是否已完成，失败后靠客户端重试继续推进；每个 actor 还有 `lock:actor:<id>` 防同 actor 并发操作。
- **worker 是 warm capacity，不是 actor 本体**：`WorkerPool` 控制 privileged ateom pods 的数量；Actor 只是逻辑记录，运行时才绑定某个 worker pod。
- **gVisor/runsc 是当前 snapshot 执行后端**：`atelet` 负责准备 runsc、OCI bundle 和 snapshot 文件；`ateom-gvisor` 串行调用 runsc 的 create/start/checkpoint/restore。
- **网络唤醒还是兼容桥阶段**：当前路由按 actor DNS 唤醒后把请求改写到 worker IP:80；ateom 用 veth + nftables 做 actor ingress/egress 兼容，后续仍需要更严格的 gateway/policy 层，和 [[agentgateway]] 一类项目会形成互补。

## 关键组件深入解读

### ateapi ActorWorkflow

`ActorWorkflow` 是当前源码里最能体现 Substrate 设计哲学的部分。它不是写一个大函数完成 resume/suspend，而是把流程拆成可跳过的步骤：resume 依次加载 actor、分配 worker、调用 atelet restore/run、最终置 running；suspend 依次加载 actor、标记 suspending、调用 atelet checkpoint、释放 worker 并提交 snapshot。

这个拆法服务于两个现实约束：actor 与 worker 状态跨 Redis Cluster key，不可能用一个强事务同时修改；调用 atelet/ateom/runsc 是外部副作用，失败可能发生在任意位置。因此 workflow 采用“状态已写入就能被下一次请求识别并继续”的模型。

### atelet + ateom-gvisor

`atelet` 和 `ateom` 的分工很清楚：atelet 是 node supervisor，接收 ateapi 的 Run/Checkpoint/Restore 请求；ateom 是 worker pod 内的 gVisor herder，真正执行 runsc。atelet 负责下载/校验 runsc、拉 OCI image、展开 rootfs、生成 OCI config、下载/上传 checkpoint zstd 文件。ateom 负责创建 interior network namespace、建立 veth、安装 nftables、执行 runsc create/start/checkpoint/restore。

当前实现假设一个 worker pod 同时只运行一个 active actor；ateom 的 mutex 和 nftables 表清理逻辑都体现了这一点。

## 相关页面

- [[agent-runtime-sandbox-selection-map]]
- [[agent-runtime-sandbox-project-map]]
- [[agent-sandbox]]
- [[agentcube]]
- [[kubernetes]]
- [[agentgateway]]
