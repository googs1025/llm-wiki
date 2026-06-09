---
title: Agent Runtime / Sandbox 项目地图
tags: [ai-agent, agent-runtime, sandbox, project-map, cloud-native]
date: 2026-06-09
sources: [src-agent-sandbox-architecture, src-agentcube-architecture, src-openshell-architecture, src-nemoclaw-architecture, src-hiclaw-architecture, src-agentscope-architecture, src-agentgateway-architecture]
related: [[agent-sandbox]], [[agentcube]], [[HiClaw]], [[agentgateway]], [[declarative-agent-management]], [[agent-credential-isolation]], [[cloud-native-security]], [[ai-agent-plugin-patterns]], [[mcp]]
---

# Agent Runtime / Sandbox 项目地图

这页把当前知识库里和 Agent runtime、sandbox、会话编排、安全控制面相关的项目放到同一张工程地图里。核心结论：这些项目都在解决“Agent 怎么安全、可恢复、可观测地长期运行”，但抽象层不一样。

```
Developer / user API
        ↓
Agent app framework / CLI / SDK
        ↓
session orchestration / agent control plane
        ↓
sandbox lifecycle primitive
        ↓
runtime enforcement: container / supervisor / proxy / policy
        ↓
network, credentials, storage, inference, tool access
```

这个方向不能只看“能不能启动一个容器”。Agent runtime 的特殊性在于：它是长寿命、有状态、会执行不可信输入、会持有工具能力、会访问模型和外部网络，并且经常需要人类中途介入。真正的系统边界包括生命周期、身份、凭据、网络、文件、推理路由、工具权限和恢复。

## 一句话分层

| 项目 | 一句话定位 | 抽象层 |
|------|------------|--------|
| [[agent-sandbox]] | K8s SIG Apps 的 Sandbox CRD，把单个有状态 Agent 容器建模成 K8s 一等资源 | Sandbox 基础设施原语 |
| [[agentcube]] | 基于 [[agent-sandbox]] 的 serverless session orchestration layer，给 Code Interpreter / AgentRuntime 提供 HTTP/SDK 调用入口 | 会话编排层 |
| [[src-openshell-architecture|OpenShell]] | NVIDIA 的安全私有 Agent runtime，Gateway 控制面 + sandbox Supervisor + OPA/Z3 policy proxy | 安全 runtime / enforcement |
| [[src-nemoclaw-architecture|NemoClaw]] | OpenShell sandbox 内 always-on Agent 的 host-side CLI 控制面，编排 onboarding、provider、policy 和 agent setup | Host-side 编排层 |
| [[HiClaw]] | K8s operator + Matrix IM + Higress 网关的多 Agent 协作平台 | 多 Agent 平台 / 协作层 |
| [[src-agentscope-architecture|AgentScope]] | Python 多 Agent 应用框架，事件流 ReAct loop + toolkit/MCP/skill + workspace/offload + FastAPI service | 应用框架 / 服务层 |
| [[agentgateway]] | 面向 LLM / MCP / A2A 的 Rust L7 数据面 + Gateway API 控制面 | Agent 网络 / 工具网关 |

## 横向对比

| 维度 | [[agent-sandbox]] | [[agentcube]] | [[src-openshell-architecture|OpenShell]] | [[src-nemoclaw-architecture|NemoClaw]] | [[HiClaw]] | [[src-agentscope-architecture|AgentScope]] | [[agentgateway]] |
|------|------------------|---------------|---------------|--------------|------------|----------------|----------------|
| 主问题 | 安全运行一个有状态 Agent 容器 | 把 Sandbox 变成可调用 session | sandbox 内 runtime enforcement | OpenShell onboarding + agent setup | 多 Agent 运维与协作 | Agent app 构建与服务化 | AI 协议流量治理 |
| 用户入口 | K8s CRD / Go/Python SDK | HTTP invocation / Python SDK / Dify / LangChain | CLI / SDK / TUI | `nemoclaw` / `nemohermes` CLI | Matrix / CLI / CRD | Python SDK / FastAPI | Gateway API / xDS / UI |
| 控制面 | K8s controller-runtime | Router + WorkloadManager + Redis | Gateway object store + compute runtime | Host-side FSM + OpenShell adapters | K8s operator + embedded/in-cluster mode | FastAPI service + storage/session manager | Go controller + ADS server |
| 数据面 | Pod + headless Service + PVC | Sandbox Pod / PicoD / reverse proxy | Supervisor + restricted child + policy proxy | OpenShell sandbox + OpenClaw/Hermes | Worker/Manager containers + Matrix rooms | Agent event loop + workspace | Rust proxy for LLM/MCP/A2A |
| 生命周期 | `Sandbox` 0/1 replicas, shutdownTime, WarmPool | session create/route/GC, WarmPool claim | create/delete/watch/reconcile/resume | onboard resume/fresh, registry lock | CR reconcile worker/team/human/manager | session run serialization, continuation events | listener/route/backend config hot update |
| 隔离机制 | 委托 K8s runtimeClass/NetworkPolicy/securityContext | 继承 [[agent-sandbox]] + Router JWT | Supervisor/proxy/seccomp/netns/TLS/OPA | 继承 OpenShell policy/shields | 容器隔离 + Higress 凭据隔离 | Workspace Local/Docker/E2B | CEL RBAC, mTLS/HBONE, guardrails |
| 凭据模型 | 不直接托管凭据 | Router→PicoD JWT，WorkloadManager auth | Gateway 托管 provider credentials | Gateway 是凭据 system-of-record | Higress 托管真实凭据，Worker 只持 consumer key | Credential/session/workspace service | backend credentials + policy/filter |
| 状态 | K8s API + PVC | Redis/ValKey session registry + K8s | SQLite/Postgres object store | `~/.nemoclaw` JSON + Gateway state | etcd/kine + Matrix + MinIO + gateway | storage/session/workspace | xDS stores + control plane |
| 典型强项 | K8s-native、简单、WarmPool | 产品化 invocation API | 安全 enforcement 边界最细 | Onboarding 和 provider/policy 编排 | IM-first 协作和凭据零暴露 | Agent app 编程体验 | LLM/MCP/A2A 统一网关 |
| 典型代价 | 只提供底层原语 | 依赖 agent-sandbox API 演进 | 系统复杂度高 | host-side 状态机复杂 | 学习曲线和容器开销 | 不是强 sandbox 原语 | 不直接运行 Agent |

## 分层图谱

```
┌────────────────────────────────────────────────────────────────────────────┐
│ App / Agent framework layer                                                │
│ AgentScope: event stream ReAct, toolkit, MCP, workspace, FastAPI service    │
│ nanobot: lightweight personal agent loop, channels, providers, skills       │
└────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌────────────────────────────────────────────────────────────────────────────┐
│ Multi-agent / session product layer                                         │
│ HiClaw: Worker/Team/Human/Manager CRD + Matrix + Higress                    │
│ AgentCube: AgentRuntime/CodeInterpreter + Router + WorkloadManager          │
│ NemoClaw: OpenShell onboarding + OpenClaw/Hermes setup                      │
└────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌────────────────────────────────────────────────────────────────────────────┐
│ Sandbox / runtime primitive layer                                           │
│ agent-sandbox: Sandbox/Claim/Template/WarmPool → Pod/PVC/Service            │
│ OpenShell: Gateway desired state → driver → Supervisor/proxy enforcement    │
└────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌────────────────────────────────────────────────────────────────────────────┐
│ Network / credential / tool gateway layer                                   │
│ agentgateway: LLM/MCP/A2A proxy, Gateway API, CEL, HBONE, xDS               │
│ Higress/OpenShell gateway: provider credentials and inference routing        │
└────────────────────────────────────────────────────────────────────────────┘
```

关键关系：

- [[agentcube]] 明确站在 [[agent-sandbox]] 之上：前者做 session API，后者做 Sandbox 生命周期。
- [[src-nemoclaw-architecture|NemoClaw]] 明确站在 [[src-openshell-architecture|OpenShell]] 之上：前者做 onboarding 和 agent setup，后者做 sandbox runtime 和 enforcement。
- [[HiClaw]] 和 [[agent-sandbox]] 是互补关系：HiClaw 管多 Agent 协作，agent-sandbox 可以成为底层隔离原语。
- [[src-agentscope-architecture|AgentScope]] 和 [[agent-sandbox]] 处在相邻问题域：AgentScope 的 Workspace 能接 Local/Docker/E2B，agent-sandbox 是更云原生的执行环境原语。
- [[agentgateway]] 不运行 Agent，但控制 Agent 访问模型、MCP、A2A 的网络边界。

## 工程剖面

### [[agent-sandbox]]：Sandbox 作为 K8s 原语

[[agent-sandbox]] 的核心贡献是把 Agent runtime 从普通 Deployment/StatefulSet 里抽出来。Agent sandbox 的语义是：

- 单实例，`replicas` 只能 0/1。
- 有稳定身份，自动创建 headless Service。
- 有持久存储，PVC 生命周期不随 Pod 自动删除。
- 可以暂停/恢复，scale to 0/1。
- 可以过期，`shutdownTime` 是声明式生命周期。
- 可以 WarmPool 预热，然后通过 Claim 领养。

它避免把安全机制做成私有实现，而是把隔离委托给 K8s 原语：runtimeClassName、gVisor/Kata、NetworkPolicy、securityContext、serviceAccount。这个设计的工程价值是可组合：任何上层平台都可以继承 K8s 生态能力。

风险也清楚：它只提供底层原语，不负责多 Agent 协作、工具协议、凭据网关、HTTP invocation 或 Agent app framework。这些必须由上层补齐。

### [[agentcube]]：把 Sandbox 包成可调用会话

[[agentcube]] 的定位比 [[agent-sandbox]] 高一层。它关心开发者如何通过 HTTP/SDK 调用一个 Code Interpreter 或 AgentRuntime，而不是让用户直接写 Sandbox CR。

关键路径：

```
Client invocation
        ↓
Router checks x-agentcube-session-id
        ↓
WorkloadManager creates Sandbox or SandboxClaim
        ↓
agent-sandbox starts/adopts Pod
        ↓
Router reverse-proxies to PodIP/entrypoint
        ↓
Redis/ValKey tracks session TTL and activity
```

它最重要的架构判断是 **不重写 Sandbox controller**。WorkloadManager 只把 AgentCube 的 `AgentRuntime` / `CodeInterpreter` 翻译成 [[agent-sandbox]] CRD，底层 lifecycle、WarmPool adoption、Pod/PVC/Service 都交给 agent-sandbox。

安全上，PicoD 用 Router-signed JWT 替代 SSH；这简化 SDK，但 Router 变成强信任边界，后续需要 auth、mTLS、RBAC、审计一起兜住。

### [[src-openshell-architecture|OpenShell]]：Gateway desired state，Supervisor runtime enforcement

[[src-openshell-architecture|OpenShell]] 的分层边界最安全工程化：

```
Gateway owns desired state
        ↓
compute driver provisions sandbox
        ↓
Supervisor owns runtime enforcement
        ↓
policy proxy controls process/network/inference egress
```

Gateway 保存 sandbox、provider、policy、settings、inference、sessions 等状态；sandbox 内 Supervisor 才真正执行网络、进程、文件、TLS、provider credential 注入和 proxy enforcement。这个边界成立，因为只有 sandbox 内能看见进程身份、socket、binary hash、TLS 流和运行时凭据。

OpenShell 的关键不是“有 sandbox”，而是把 Agent egress 变成可审计、可裁决、可提案的策略流。普通网络访问走 OPA；`inference.local` 是特殊本地能力，代理到 provider，但 Agent 不直接持有真实 key。

### [[src-nemoclaw-architecture|NemoClaw]]：OpenShell 上的 host-side Agent 编排

[[src-nemoclaw-architecture|NemoClaw]] 是 OpenShell 的产品化编排层，不是另一个推理或 sandbox 引擎。它把用户真正要完成的步骤串起来：

- preflight 检查 Docker/OpenShell/GPU/DNS。
- 启动或复用 named OpenShell gateway。
- 选择 provider/model/credential route。
- 创建或复用 sandbox。
- 安装/同步 OpenClaw 或 Hermes runtime config。
- 应用 baseline policy 和 presets。
- 编译 messaging channel manifest。

它的核心是可恢复 onboard FSM：host-side JSON registry、session state、全局 lock、resume/fresh/non-interactive。这个模式适合复杂本地开发工具，但也带来状态恢复、部分写入和版本迁移成本。

### [[HiClaw]]：Agent 是 CR，也是 IM 用户

[[HiClaw]] 的设计很鲜明：把 Agent 运维做成 K8s operator，同时把协作面放到 Matrix IM。

```
Worker CR
        ↓
controller reconcile
        ↓
Matrix user + room
        ↓
Higress consumer key
        ↓
Worker container
        ↓
Human / Manager / Workers collaborate in rooms
```

这解决两个常被 Agent framework 忽略的问题：

- 人类如何自然介入：直接进 Matrix 房间。
- Agent 凭据如何隔离：Worker 只拿 Higress consumer key，真实 provider/API key 在网关侧。

它的代价是平台复杂度高。每个 Worker 是容器、Matrix 用户、gateway consumer 三位一体；Provisioner 同时编排 Matrix/Higress/Credentials/Manager bootstrap，横向拆分压力已经出现。

### [[src-agentscope-architecture|AgentScope]]：应用框架里的 runtime 边界

[[src-agentscope-architecture|AgentScope]] 不提供强 sandbox 原语，但它定义了生产 Agent 应用的运行时边界：

- `AgentEvent` / `Msg` 是 SDK、SSE、存储和 UI 的统一协议。
- ReAct loop 把人类确认和外部执行建模成 continuation event。
- Tool execution 被拆成权限/上下文写入和 raw I/O。
- Workspace 承接 tools、MCP、skills 和 context/tool-result offload。
- FastAPI service 每轮从 storage/session/workspace 重新组装 Agent。

这类框架更适合应用服务，而不是底层隔离。它可以把 Docker/E2B/未来 agent-sandbox 作为 Workspace backend，把自身保持在 Agent 编排与事件流层。

### [[agentgateway]]：Agent 访问外界的网络控制点

[[agentgateway]] 解决的是 Agent 流量，而不是 Agent 生命周期。它把 LLM API、MCP tools、A2A 通信统一到一个 Rust L7 数据面，控制面复用 Gateway API/xDS。

对 runtime/sandbox 体系来说，它的价值是：

- LLM provider 统一协议和 guardrails。
- MCP tools federation + CEL RBAC。
- A2A Agent Card URL rewrite 和代理。
- HBONE/mTLS/telemetry/access log。
- 用声明式 CRD 管路由、策略和后端。

如果 [[agent-sandbox]] 是“Agent 跑在哪里”，[[agentgateway]] 就是“Agent 能访问什么、怎么访问、怎么审计”。

## 核心难点

### 1. 生命周期不是 Pod 生命周期

Agent sandbox 的生命周期包含：创建、恢复、暂停、续期、过期、热领养、GC、startup resume、长任务 offload。这比普通 Pod 的 Running/Terminated 更复杂。

- [[agent-sandbox]] 用 `shutdownTime` 和 0/1 replicas 表达暂停/过期。
- [[agentcube]] 用 Redis sorted set 管 session TTL 和 last activity。
- [[src-openshell-architecture|OpenShell]] 用 Gateway store + driver watch/reconcile/resume。
- [[src-nemoclaw-architecture|NemoClaw]] 用 host-side FSM 和 registry 做 onboarding resume。

结论：Agent runtime 必须显式建模“会话”和“工作负载”的差异。

### 2. 凭据不能进 Agent 进程

Agent 会执行模型生成的工具调用，也会读取用户输入。真实 API key、GitHub PAT、云 AK 如果进入 Agent 进程，就会被 prompt injection 放大。

成熟方向都是网关托管：

- [[HiClaw]]：真实 key 在 Higress，Worker 只持 consumer key。
- [[src-openshell-architecture|OpenShell]] / [[src-nemoclaw-architecture|NemoClaw]]：Gateway 是 provider credential system-of-record，sandbox 通过 `inference.local` 使用模型。
- [[agentgateway]]：后端 credentials 与 policy/filter 在网关侧。

这和 [[agent-credential-isolation]] 是同一条设计线。

### 3. 网络策略需要进程级语义

K8s NetworkPolicy 只能管 Pod 维度，Agent sandbox 内可能有多个进程：agent、tool、shell、browser、package manager。[[src-openshell-architecture|OpenShell]] 通过 proxy + `/proc/net/tcp` + binary identity 把网络裁决细化到进程/二进制身份，这是更细粒度的 runtime enforcement。

对于大多数平台，第一阶段可以用 NetworkPolicy + egress proxy；高风险场景才需要 OpenShell 这种 Supervisor/proxy 模型。

### 4. WarmPool 是性能优化，也是所有权协议

预热不是“提前启动 Pod”这么简单。关键难点是 ready sandbox 被 claim 领养时，ownerReference、labels、status、Pod exclusivity 必须一致。

[[agent-sandbox]] 的 `SandboxClaim` adoption 协议是底层实现；[[agentcube]] 只在 CodeInterpreter `warmPoolSize` 上暴露能力。这是合理分工：底层保证所有权不变量，上层只表达“我需要低冷启动”。

### 5. 人在回路不是 UI 附加项

多 Agent 系统需要人类在任务中途介入、批准、观察和接管。

- [[HiClaw]] 用 Matrix 房间把人类和 Agent 放在同一个协作平面。
- [[src-agentscope-architecture|AgentScope]] 用 `RequireUserConfirmEvent` 和 continuation event 把人类确认放进事件流。
- [[src-openshell-architecture|OpenShell]] 的 policy proposal 默认人工审批。

人在回路应该是协议和状态机能力，不应该只是一个前端按钮。

### 6. App framework 和 sandbox runtime 要分层

AgentScope、nanobot 这类应用框架解决“如何思考、调用工具、持久化上下文”；agent-sandbox/OpenShell 解决“如何安全运行”。把两层混在一起会导致框架既要懂 ReAct，又要懂容器、网络、凭据、恢复，复杂度失控。

比较稳的组合是：

```
Agent framework
        ↓ workspace/runtime adapter
Sandbox/session layer
        ↓ lifecycle primitive
K8s/OpenShell/container runtime
```

## 设计分型

| 分型 | 代表项目 | 设计重心 | 适合场景 |
|------|----------|----------|----------|
| Sandbox 原语型 | [[agent-sandbox]] | CRD、Pod/PVC/Service、WarmPool、K8s 原语 | 云原生 Agent 执行环境底座 |
| Session 编排型 | [[agentcube]] | HTTP invocation、session registry、Router/WorkloadManager | Code interpreter / serverless agent runtime |
| 安全 runtime 型 | [[src-openshell-architecture|OpenShell]] | Gateway desired state、Supervisor、policy proxy | 高风险 autonomous agent、凭据隔离、网络审计 |
| Host-side 编排型 | [[src-nemoclaw-architecture|NemoClaw]] | onboarding FSM、provider/policy/agent setup | 把安全 runtime 包成可用产品 |
| 多 Agent 平台型 | [[HiClaw]] | CRD + IM + 网关凭据 + Worker/Team | 企业多 Agent 协作和运维 |
| 应用框架型 | [[src-agentscope-architecture|AgentScope]], [[nanobot]] | ReAct loop、event stream、tools、workspace | 构建 Agent 应用或个人 Agent |
| 网络网关型 | [[agentgateway]] | LLM/MCP/A2A 流量、policy、telemetry | Agent 外部访问治理 |

## 选型建议

| 目标 | 优先看 | 工程关注点 |
|------|--------|------------|
| 想把 Agent 容器建模成 K8s 原语 | [[agent-sandbox]] | Sandbox/Claim/WarmPool、PVC 生命周期、NetworkPolicy |
| 想做 Code Interpreter / AgentRuntime 会话服务 | [[agentcube]] | Router/WorkloadManager、session registry、WarmPool adoption |
| 想研究最细的安全 sandbox runtime | [[src-openshell-architecture|OpenShell]] | Gateway/Supervisor 分界、policy proxy、inference.local |
| 想把 OpenShell 包成用户可用 CLI 工作流 | [[src-nemoclaw-architecture|NemoClaw]] | onboard FSM、provider/policy/messaging manifest |
| 想做多 Agent 协作平台 | [[HiClaw]] | CRD、Matrix、Higress、credential isolation |
| 想做 Agent 应用服务 | [[src-agentscope-architecture|AgentScope]] | AgentEvent、tool permission、workspace/offload、FastAPI |
| 想治理 Agent 的 LLM/MCP/A2A 流量 | [[agentgateway]] | Gateway API、xDS、CEL、MCP federation、guardrails |

## 相关页面

- [[agent-sandbox]]
- [[agentcube]]
- [[HiClaw]]
- [[agentgateway]]
- [[declarative-agent-management]]
- [[agent-credential-isolation]]
- [[cloud-native-security]]
- [[ai-agent-plugin-patterns]]
- [[mcp]]
