# OpenShell 架构与设计思路分析

> 仓库：https://github.com/NVIDIA/OpenShell · 分析日期：2026-06-05 · 版本：HEAD `97986d9`（GitHub API 校验；完整 clone 超时后使用 codeload archive）

## 一句话定位

OpenShell 是 NVIDIA 面向 autonomous AI agents 的安全私有运行时：它不是一个新的 Agent framework，而是把 Agent 放进可审计、可配置、可连接、可恢复的 sandbox 里运行。它的关键手段是把 Gateway 控制面、sandbox 内 Supervisor enforcement、OPA/Z3 policy pipeline、provider credential 管理和 `inference.local` 推理路由拆成清晰边界。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ User surfaces                                                                 │
│                                                                              │
│ openshell CLI          Python SDK / future SDKs          TUI                  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ gRPC / HTTP
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway control plane                                                        │
│ crates/openshell-server                                                      │
│                                                                              │
│ - authn/authz for users and sandbox callbacks                                 │
│ - object store: sandboxes, providers, policy, settings, inference, sessions   │
│ - compute orchestration: create/delete/watch/reconcile/resume                 │
│ - provider credential and inference bundle resolution                         │
│ - supervisor session registry and relay coordination                          │
│                                                                              │
│              ┌─────────────────────┐        ┌────────────────────────────┐   │
│              │ SQLite / Postgres   │        │ provider / policy objects  │   │
│              └─────────────────────┘        └────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────────────────────────┘
               │ compute driver contract
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Runtime integrations                                                          │
│                                                                              │
│ Docker driver     Podman driver     Kubernetes driver     VM / libkrun driver │
│                                                                              │
│ Each driver provisions workload identity, callback material, image/template,  │
│ supervisor binary, initial command, runtime env, and lifecycle events.        │
└──────────────┬───────────────────────────────────────────────────────────────┘
               │ starts sandbox workload
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sandbox data plane                                                            │
│ crates/openshell-sandbox                                                      │
│                                                                              │
│ ┌──────────────────────┐        ┌─────────────────────────────────────────┐  │
│ │ Supervisor            │        │ Restricted agent child                  │  │
│ │ - starts as root      │ spawn  │ - non-root user                         │  │
│ │ - loads policy/config ├───────▶│ - filesystem/process/network limits     │  │
│ │ - injects credentials │        │ - ordinary egress forced through proxy  │  │
│ │ - starts proxy + SSH  │        └──────────────────┬──────────────────────┘  │
│ │ - opens outbound      │                           │ CONNECT / HTTP          │
│ │   session to gateway  │◀──── relay/config/logs ───┘                         │
│ └──────────┬───────────┘                                                      │
│            │                                                                  │
│            ▼                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Policy proxy                                                             │ │
│ │ - bind process identity via /proc/net/tcp + binary hash                  │ │
│ │ - evaluate OPA network action                                            │ │
│ │ - reject SSRF/internal destinations unless explicitly allowed            │ │
│ │ - terminate TLS for L7 inspection and credential rewrite where enabled   │ │
│ │ - intercept https://inference.local and route via openshell-router       │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 用户入口 | `crates/openshell-cli`, `openshell` command surface, Python SDK | 解析 gateway context、sandbox name、auth token；把用户意图变成 Gateway API 调用。 |
| Gateway 控制面 | `crates/openshell-server` | API、认证、持久状态、policy/settings/provider/inference 配置、compute orchestration、relay 协调。架构文档明确 Gateway 不做 agent egress 的 per-request enforcement，相关决策在 sandbox 内完成（`architecture/gateway.md:19-21`）。 |
| 持久化 | `crates/openshell-server/src/persistence` | protobuf object store，SQLite/Postgres 后端，`resource_version` CAS；生产写路径必须显式使用 `WriteCondition` 或 `update_message_cas`（`architecture/gateway.md:158-184`）。 |
| Compute runtime | `crates/openshell-server/src/compute`, `crates/openshell-driver-*` | 抽象 Docker/Podman/Kubernetes/VM driver；负责创建、删除、watch、reconcile、startup resume。 |
| Sandbox supervisor | `crates/openshell-sandbox` | sandbox 内安全边界：加载 policy/settings、准备 filesystem/process/netns/TLS、启动 proxy/SSH、拉取 provider env、启动 agent child、热更新 policy。 |
| Policy proxy | `crates/openshell-sandbox/src/proxy.rs`, `crates/openshell-policy`, `crates/openshell-prover` | 用 OPA 做 L4/L7 网络决策，用 `/proc/net/tcp` 绑定调用进程身份，做 SSRF 防护、TLS/L7 inspection、凭证 rewrite、`inference.local` 路由；prover 用 Z3 检查 policy proposal 风险。 |
| Provider / inference | `crates/openshell-providers`, `crates/openshell-router` | provider discovery、credential 注入、OpenAI/Anthropic/NVIDIA 等模型路由；sandbox 内 `inference.local` 不走普通 OPA network policy。 |
| Runtime/package/support | `deploy/`, `helm/`, `docs/`, `e2e/`, `python/` | Kubernetes/Helm、文档、端到端测试、SDK 与开发辅助。 |

OpenShell 的分层约束很强：Gateway owns desired state，Supervisor owns runtime enforcement。架构文档把 Gateway 定义为 API、durable state、policy/settings/provider/inference delivery、relay coordination 的控制面（`architecture/README.md:8-14`），同时把 Supervisor 定义为每个 sandbox workload 内的 local security boundary。这样的分工避免 Gateway 需要理解 Docker bridge、Pod IP、VM NAT 或 Kubernetes service mesh 的所有网络细节。

## 关键数据流

```
┌──────────────┐
│ openshell CLI │
└──────┬───────┘
       │ CreateSandbox(name/spec/policy/providers)
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway gRPC handler                                                         │
│ - validate spec/labels/providers                                             │
│ - fill default image                                                          │
│ - ensure sandbox process identity + validate policy safety                    │
│ - allocate UUID/name and set phase=Provisioning                               │
│ - optionally mint gateway sandbox JWT                                         │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ ComputeRuntime::create_sandbox
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway compute runtime                                                      │
│ - update in-memory sandbox index                                             │
│ - persist Sandbox with WriteCondition::MustCreate                             │
│ - call selected compute driver                                                │
│ - rollback store/index when driver creation fails                             │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ driver provisions workload
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Docker / Podman / Kubernetes / VM                                            │
│ - inject gateway callback, identity/token material, supervisor, env, command  │
│ - report lifecycle through watch stream / reconciliation                      │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ starts openshell-sandbox
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sandbox supervisor                                                           │
│ - load policy and settings                                                    │
│ - fetch provider env from gateway                                             │
│ - prepare filesystem, process limits, netns, seccomp, TLS CA                  │
│ - start policy proxy and SSH server                                           │
│ - open outbound ConnectSupervisor session                                     │
│ - spawn restricted agent child                                                │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ ordinary egress / exec / file sync / logs
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Policy proxy + supervisor relay                                              │
│ - CONNECT denied: OCSF log + DenialEvent → gateway policy proposal pipeline   │
│ - CONNECT allowed: SSRF check → optional TLS/L7 inspection → upstream         │
│ - inference.local: TLS terminate → parse inference API → openshell-router     │
│ - gateway connect/exec: GatewayMessage::RelayOpen → reverse RelayStream       │
└──────────────────────────────────────────────────────────────────────────────┘
```

创建路径在代码里比较直接：`handle_create_sandbox_inner` 会补默认镜像、确保 sandbox process identity、验证 policy safety、生成 metadata、把 phase 设置为 `Provisioning`，然后可选铸造 sandbox JWT 并调用 `state.compute.create_sandbox`（`crates/openshell-server/src/grpc/sandbox.rs:150-214`）。`ComputeRuntime::create_sandbox` 先用 `WriteCondition::MustCreate` 写 store，再调用 driver；如果 driver 报 AlreadyExists、FailedPrecondition 或其他错误，会删除 store 记录并移除 sandbox index（`crates/openshell-server/src/compute/mod.rs:437-520`）。

Supervisor 启动路径更像一条安全 pipeline：`run_sandbox` 先加载 policy/OPA、拉 provider env、准备 filesystem，生成 ephemeral CA，创建 network namespace，安装 bypass detection，启动 proxy，再启动 SSH server 和 outbound supervisor session，最后才 spawn restricted agent child（`crates/openshell-sandbox/src/lib.rs:348-665`, `crates/openshell-sandbox/src/lib.rs:801-888`）。policy poll loop 和 denial aggregator 都是后台任务，失败时保留 last-known-good 或把 denial summary 刷回 Gateway（`crates/openshell-sandbox/src/lib.rs:976-1043`）。

## 设计决策与哲学

- **控制面和 enforcement 分离**：Gateway 存储和分发策略，但不在请求时裁决 agent 网络访问；这让策略 enforcement 能看到 sandbox 内的进程身份、binary hash、netns、TLS 流量和 runtime credentials（`architecture/security-policy.md:3-7`）。
- **Supervisor 主动连 Gateway**：sandbox 通过 outbound `ConnectSupervisor` 持有 live session，Gateway 的 connect/exec/file sync 通过 relay 协调，不要求每种 runtime 暴露可直连地址（`architecture/README.md:136-154`）。
- **driver 薄、语义厚**：compute driver 只翻译 Docker/Podman/Kubernetes/VM 的平台操作；sandbox lifecycle、phase、policy/settings/provider/inference 是 Gateway/Supervisor 的 OpenShell 语义（`architecture/README.md:102-125`）。
- **持久状态按对象存储 + CAS**：状态对象统一进 protobuf object store，生产写路径通过 CAS 或 MustCreate，减少并发 Gateway handler/reconciler 互相覆盖的风险（`architecture/gateway.md:102-184`）。
- **网络策略绑定进程身份而不是只看目标**：proxy 通过 `/proc/net/tcp` 解析 socket owner，再把 binary path/hash/ancestor/cmdline 放进 OPA input，避免一个 sandbox 内所有进程共享同一网络权限（`crates/openshell-sandbox/src/proxy.rs:1357-1452`）。
- **推理路由作为特殊本地能力**：`https://inference.local` 由 sandbox proxy TLS terminate 并转给 `openshell-router`，不让 agent 直接携带 provider credentials 访问模型端点（`architecture/sandbox.md:47-63`）。
- **policy proposal 默认人工审批**：denial 可以生成 draft policy chunk，但 Gateway 会用 prover 计算当前 policy 和 proposed policy 的 finding delta；只有显式 auto 模式且 prover delta 为空才自动批准（`architecture/security-policy.md:99-166`）。

## 关键组件深入解读

### Gateway compute runtime（`crates/openshell-server/src/compute/mod.rs`）

`ComputeRuntime` 是 Gateway 对 sandbox lifecycle 的核心封装。它持有 pluggable `ComputeDriver`、Store、SandboxIndex、watch bus、tracing bus、SupervisorSessionRegistry 和一个暂时的 `sync_lock`。构造函数把 Docker、Kubernetes、Podman、remote VM 都收敛成同一个 driver trait，Gateway 层只关心 create/delete/list/watch/validate。创建路径先持久化再调用 driver，失败回滚；删除路径先 CAS 设置 `Deleting`，清理 sandbox-owned records，再调用 driver delete。watch/reconcile 是长期后台任务：watch loop 应用 driver event，reconcile loop 定期比对 store 与 backend，发现 backend 缺失就走 orphan pruning。

近期 HEAD `97986d9` 正好改了 startup resume：legacy 或未初始化 sandbox row 会 decode 成 proto 默认 `Unspecified` phase，之前 resume sweep 会跳过它，导致 Gateway 重启后既不恢复也不报错；最新修复把 `Unspecified` 视为应当运行，backend 存在则 resume，不存在则 mark Error。这个修复说明 compute runtime 的难点不是创建容器本身，而是 Gateway store、driver backend 和用户可见 phase 在重启/失败后的收敛。

### Supervisor session / relay（`crates/openshell-server/src/supervisor_session.rs`）

OpenShell 的 connect/exec/file sync 不走 Gateway 直接拨 sandbox，而是由 Supervisor 先向 Gateway 建立 gRPC session。`SupervisorSessionRegistry` 维护 `sandbox_id -> LiveSession` 和 `channel_id -> PendingRelay` 两张表。Gateway 想打开 relay 时，先等待 session 出现，生成 channel_id，把 pending relay 插入 map，再向 Supervisor 发 `GatewayMessage::RelayOpen`。Supervisor 随后通过 `RelayStream` 回连并用首帧 `RelayInit` claim 这个 channel。这个“先登记 pending，再通知远端”的顺序是为了避免反向连接先到而 Gateway 还没有等待者的竞态（`crates/openshell-server/src/supervisor_session.rs:256-323`, `crates/openshell-server/src/supervisor_session.rs:467-567`）。

Registry 还处理 reconnect：同一个 sandbox 新 session 注册时会 supersede 旧 session，并 replay pending relays。每个 relay 有 10 秒 pending timeout，全局最多 256 个、单 sandbox 最多 32 个，避免恶意或异常客户端无限占用内存（`crates/openshell-server/src/supervisor_session.rs:23-38`, `crates/openshell-server/src/supervisor_session.rs:104-190`）。

### Sandbox proxy（`crates/openshell-sandbox/src/proxy.rs`）

Proxy 是 OpenShell 数据面的关键：它先解析 HTTP CONNECT，如果目标是 `inference.local:443`，直接进入 inference interception；否则用 `evaluate_opa_tcp` 做进程身份绑定和 OPA policy evaluation。allow 之后仍要做 SSRF 防护：默认拒绝内部地址，除非 policy 显式声明 `allowed_ips`、exact declared endpoint host，或命中特定 host-gateway alias 且通过专门检查（`crates/openshell-sandbox/src/proxy.rs:404-598`, `crates/openshell-sandbox/src/proxy.rs:616-888`）。

L7 逻辑在 L4 allow 之后才发生：如果 policy endpoint 启用 L7 inspection，proxy 会 TLS terminate 或处理明文 HTTP，调用 `relay_with_inspection`/`relay_with_route_selection`；没有 L7 config 时也可以做 credential passthrough rewrite。`tls: skip` 则显式退回 raw tunnel。`inference.local` 走另一条路径：TLS terminate、解析 OpenAI/Anthropic/兼容请求、走 `openshell-router`，响应以 chunked/SSE 形式流回，并设置 32MiB streaming cap 与 120s chunk idle timeout（`crates/openshell-sandbox/src/proxy.rs:895-1120`, `crates/openshell-sandbox/src/proxy.rs:1482-1760`）。

## 与同类对比

| 维度 | OpenShell | agent-sandbox | agentgateway / AI gateway |
|------|-----------|---------------|---------------------------|
| 主问题 | 在本地/集群/VM 中安全运行 autonomous agent | 在 Kubernetes 中把 agent sandbox 建成 CRD 生命周期原语 | 统一 LLM/MCP/A2A/API 出口流量治理 |
| 控制面 | Gateway + object store + compute driver | Kubernetes API + controller | Gateway/controller + proxy data plane |
| enforcement 位置 | sandbox 内 Supervisor/proxy/kernel controls | 主要委托 PodTemplate/runtimeClass/NetworkPolicy | 网关/proxy 侧 |
| 凭证模型 | Gateway 托管 provider credential，Supervisor runtime 注入或 proxy rewrite | 不规定 provider credential 语义 | 网关托管后端凭证 |
| 推理路径 | `inference.local` → sandbox router → provider backend | 不涉及推理协议 | LLM provider route/policy/observability |

## 性能 / 资源开销

本次未做基准测试。可从代码推断的开销主要来自四类：sandbox 启动时 driver provisioning、Supervisor 初始化 Landlock/netns/seccomp/TLS/proxy/SSH、每条 CONNECT 的 `/proc/net/tcp` + binary identity 解析、TLS/L7 inspection 与 inference streaming。proxy 对重 I/O 的身份解析使用 `spawn_blocking`，并有 binary identity cache；inference streaming 设置 32MiB body cap 与 120s chunk idle timeout，偏向控制资源上界而不是极限吞吐。

## 安全模型

OpenShell 的信任边界是“Gateway 管状态和凭证，Supervisor 管本地 enforcement，Agent child 永远不应拥有完整控制面权限”。Gateway 持久层存 provider API keys、SSH session tokens 和 sandbox metadata，因此 SQLite backend 会把 db、WAL、SHM 文件权限收紧到 `0600`（`architecture/gateway.md:145-149`）。Sandbox supervisor 以 root 启动是为了准备 isolation，但 agent child 以非 root 用户运行，并受 Landlock、seccomp、network namespace、proxy 和 OPA policy 约束（`architecture/sandbox.md:7-45`）。

策略风险不只靠 LLM 判断：`openshell-prover` 把 sandbox policy、binary capabilities、credential scopes 编码为 Z3 SMT constraints，检查 link-local reach、credentialed L7 bypass、credential reach expansion、capability expansion 四类 finding（`crates/openshell-prover/src/lib.rs:4-8`, `architecture/security-policy.md:133-166`）。这使 policy advisor 可以接受 agent-authored proposal，但默认仍落入 manual review。

## 近期演进

- `97986d9`（2026-06-05）：修复 startup resume 跳过 `Unspecified` sandbox phase 的问题，避免 Gateway 重启后遗留 sandbox 既不恢复也不报错。
- `e26a1b1`（2026-06-05）：Kubernetes sandbox 配置 AppArmor profile。
- `884d4ed`（2026-06-04）：bootstrap Docker build 显式设置平台参数，减少 daemon 默认平台带来的不可复现行为。
- `586c385`（2026-06-04）：CI/e2e 改用 upstream `agent-sandbox` manifest，说明 OpenShell 和 Kubernetes SIG Apps sandbox runtime 正在靠近。
- `eea9751`（2026-06-04）：CLI 支持 `sandbox create` 多个 `--upload` flag。

整体看，项目还处在 alpha/快速迭代阶段：基础抽象已经很清楚，但最近提交集中在 lifecycle 恢复、Kubernetes hardening、bootstrap 可复现性和 CLI 体验，说明生产边界仍在持续补齐。
