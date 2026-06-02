# AgentCube 架构与设计思路分析

> 仓库：https://github.com/volcano-sh/agentcube · 分析日期：2026-06-01 · 版本：HEAD `208da32`（2026-06-01，Merge PR #361 refactor/typed-informers）

## 一句话定位

`volcano-sh/agentcube` 是 Volcano 社区面向 AI Agent / Code Interpreter 工作负载的 **serverless session orchestration layer**：上层用 `AgentRuntime` / `CodeInterpreter` 两个 CRD 表达“可被调用的 agent/runtime 模板”，中层用 Router + WorkloadManager + Redis/ValKey 管 session、路由、GC 和预热，下层直接复用 `kubernetes-sigs/agent-sandbox` 的 `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` 来真正创建隔离执行环境。

它和 `agent-sandbox` 不是竞争关系，而是更明确的上下层关系：`agent-sandbox` 提供“一个稳定、有状态、可预热/可领取的 Sandbox 原语”，AgentCube 把这个原语包装成“开发者能通过 HTTP/SDK 调用的 AgentRuntime / CodeInterpreter 会话服务”。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Client / SDK / AI Framework                           │
│                                                                              │
│  Python SDK        LangChain DeepAgents        Dify Plugin        curl       │
│  CodeInterpreter   AgentcubeSandbox            Tool Provider      HTTP       │
└──────────────┬───────────────────────┬────────────────────────────┬─────────┘
               │                       │                            │
               │ invocation HTTP       │ x-agentcube-session-id      │
               ▼                       ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         AgentCube Router (data plane)                        │
│                                                                              │
│  Gin + ReverseProxy + h2c                                                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ /v1/namespaces/{ns}/agent-runtimes/{name}/invocations/*path            │  │
│  │ /v1/namespaces/{ns}/code-interpreters/{name}/invocations/*path         │  │
│  └──────────────┬───────────────────────────────┬─────────────────────────┘  │
│                 │                               │                            │
│      session exists?                    no session header                    │
│                 │                               │                            │
│                 ▼                               ▼                            │
│        Redis / ValKey  ◄──────────  SessionManager calls WorkloadManager     │
│        session:{id}                 POST /v1/{agent-runtime|code-interpreter}│
└─────────────────┬───────────────────────────────────────────────┬────────────┘
                  │                                               │
                  │ reverse proxy + Router-signed JWT              │ create/delete
                  ▼                                               ▼
┌──────────────────────────────────────┐        ┌────────────────────────────────┐
│          Running Sandbox Pod          │        │  WorkloadManager (control plane)│
│                                      │        │                                │
│  Agent container or PicoD daemon      │        │  informer cache                │
│  ┌────────────────────────────────┐  │        │  typed listers                 │
│  │ PicoD: /api/execute /api/files │  │        │  sandbox ready watchers        │
│  │ verifies PICOD_AUTH_PUBLIC_KEY │  │        │  Redis placeholder/update      │
│  └────────────────────────────────┘  │        │  idle + max TTL GC             │
└──────────────────────────────────────┘        └──────────────┬─────────────────┘
                                                               │
                                                               │ creates / claims
                                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         agent-sandbox substrate                              │
│                                                                              │
│  AgentRuntime path:                                                           │
│    AgentCube AgentRuntime ──► agents.x-k8s.io/Sandbox ──► Pod                │
│                                                                              │
│  CodeInterpreter cold path:                                                   │
│    CodeInterpreter ──► agents.x-k8s.io/Sandbox ──► PicoD Pod                 │
│                                                                              │
│  CodeInterpreter warm path:                                                   │
│    CodeInterpreter ──► SandboxTemplate + SandboxWarmPool                      │
│                    └─► SandboxClaim ──► pre-warmed Sandbox adoption           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| **AgentCube API 层** | `pkg/apis/runtime/v1alpha1/agent_type.go` · `codeinterpreter_types.go` · `manifests/charts/base/crds/` | 定义 `AgentRuntime` / `CodeInterpreter` 两个面向用户的 CRD。前者保留完整 `PodSpec`，后者收敛成 image/resources/runtimeClass/authMode/warmPoolSize。 |
| **数据面 Router** | `cmd/router/main.go` · `pkg/router/{server,handlers,session_manager,jwt}.go` | 暴露 invocation API，按 `x-agentcube-session-id` 做 session affinity；没 session 时调用 WorkloadManager 创建；有 session 时查 Redis/ValKey；最后反向代理到 sandbox endpoint。 |
| **控制面 WorkloadManager** | `cmd/workload-manager/main.go` · `pkg/workloadmanager/` | 读 AgentCube CRD，构造 `agent-sandbox` CR，等待 Sandbox Ready，探测 entrypoint，写 session store，并周期性 GC。 |
| **Sandbox 内 runtime** | `cmd/picod/main.go` · `pkg/picod/` · `docker/Dockerfile.picod` | PicoD 用轻量 HTTP API 替换 SSH：执行命令、上传/下载/列文件、workspace path jail、JWT 验证、32MB body limit。 |
| **状态存储** | `pkg/store/` | Redis / ValKey 抽象；`session:{id}` 保存 `SandboxInfo`，两个 sorted set 分别索引 `ExpiresAt` 和 `LastActivityAt`。 |
| **安全与身份** | `pkg/mtls/` · `pkg/router/jwt.go` · `pkg/workloadmanager/auth.go` · Helm `spire.*` 模板 | Router→PicoD 用 RS256 JWT；Router→WorkloadManager 可用 SA token 或 SPIFFE/mTLS；mTLS 文件来源可来自 SPIRE / cert-manager / 静态 Secret。 |
| **SDK / 集成** | `sdk-python/agentcube/` · `integrations/langchain-agentcube/` · `integrations/dify-plugin/` · `cmd/cli/` | Python SDK、LangChain Deep Agents backend、Dify plugin、kubectl 风格 CLI，把底层 session API 包成开发者接口。 |
| **部署与 E2E** | `manifests/charts/base/` · `test/e2e/` · `docs/getting-started.md` | Helm 安装 Router/WorkloadManager/CRDs/SPIRE；E2E 覆盖 CodeInterpreter、WarmPool、agent-sandbox 安装和 session 生命周期。 |

## 关键数据流

### 1. 无 session 的首次调用

```
Client / SDK
    │
    │ POST /v1/namespaces/default/code-interpreters/my-interpreter/invocations/api/execute
    │ (no x-agentcube-session-id)
    ▼
AgentCube Router
    │
    ├─ SessionManager.GetSandboxBySession(sessionID="")
    │      │
    │      ▼
    │   WorkloadManager POST /v1/code-interpreter
    │      │
    │      ├─ informer lister 读取 CodeInterpreter CR
    │      ├─ 生成 sessionID + sandboxName
    │      ├─ 如果 warmPoolSize > 0:
    │      │     create extensions.agents.x-k8s.io/SandboxClaim
    │      └─ 否则:
    │            create agents.x-k8s.io/Sandbox
    │
    ▼
WorkloadManager 等待 Sandbox Ready
    │
    ├─ WatchSandboxOnce(namespace, sandboxName)
    ├─ agent-sandbox controller 创建/领养 Pod
    ├─ WorkloadManager 取 PodIP
    ├─ TCP probe sandbox entrypoints
    └─ Redis/ValKey UpdateSandbox(sessionID -> SandboxInfo)
    │
    ▼
Router reverse proxy
    │
    ├─ 选择匹配 pathPrefix 的 entrypoint
    ├─ 生成 5 分钟 RS256 JWT: {"session_id": "..."}
    ├─ Authorization: Bearer <router-signed-jwt>
    └─ 转发到 PicoD / agent runtime
```

### 2. CodeInterpreter WarmPool 路径

```
kubectl apply CodeInterpreter(warmPoolSize: 2)
      │
      ▼
CodeInterpreterReconciler
      │
      ├─ ensure SandboxTemplate(name = CodeInterpreter.name)
      │     └─ convert CodeInterpreterSandboxTemplate -> agent-sandbox PodTemplate
      │
      └─ ensure SandboxWarmPool(name = CodeInterpreter.name, replicas = 2)
            │
            ▼
agent-sandbox extension controllers
      │
      └─ keep N ready Sandboxes waiting for adoption

first invocation
      │
      ▼
WorkloadManager buildSandboxByCodeInterpreter
      │
      ├─ create SandboxClaim(templateRef = CodeInterpreter.name)
      ├─ entry.Kind = SandboxClaim
      └─ store session placeholder
            │
            ▼
agent-sandbox SandboxClaimReconciler
      │
      ├─ pick ready Sandbox from WarmPool
      ├─ transfer ownerReference to Claim
      └─ annotate SandboxPodName
            │
            ▼
WorkloadManager sees Sandbox Ready -> PodIP -> entrypoints -> session store
```

### 3. Session 回收

```
Router 每次请求
    │
    └─ UpdateSessionLastActivity(sessionID, now)
          │
          ▼
Redis / ValKey
    ├─ session:{id} -> SandboxInfo JSON
    ├─ session:expiry sorted set
    └─ session:last_activity sorted set

WorkloadManager GC every 15s
    │
    ├─ ListInactiveSandboxes(before = now - 1m)
    ├─ 对每个 sandbox 套自己的 IdleTimeout
    ├─ ListExpiredSandboxes(before = now)
    ├─ deduplicate by SessionID
    ├─ delete Sandbox 或 SandboxClaim
    └─ DeleteSandboxBySessionID
```

## 设计决策与哲学

- **把 `agent-sandbox` 当 substrate，不重新实现 Sandbox controller**：`go.mod` 直接依赖 `sigs.k8s.io/agent-sandbox v0.1.1`，WorkloadManager 构造 `agents.x-k8s.io/Sandbox` 和 `extensions.agents.x-k8s.io/SandboxClaim`。AgentCube 自己不碰 Pod reconcile 细节，专注 session API、路由、GC、SDK 和集成。这是和 `agent-sandbox` 结合的核心。

- **两个 CRD 对应两类 AI workload**：`AgentRuntime` 允许完整 `PodSpec`，适合长会话 agent、volume、credential、sidecar；`CodeInterpreter` 收敛成 image/resources/runtimeClass/authMode/warmPoolSize，适合执行不可信代码。也因此只有 CodeInterpreter 一等支持 `warmPoolSize`，因为 code interpreter 更需要低冷启动延迟。

- **Router / WorkloadManager 分平面**：Router 是高频数据面，负责 session header、反向代理、路径匹配和并发限制；WorkloadManager 是低频控制面，负责 K8s API、informer、Sandbox 创建和 GC。这样 Router 可以水平扩展，状态放进 Redis/ValKey，而不是把请求路径绑死在 controller 进程内。

- **创建先写 placeholder，再等 Ready，再 update store**：WorkloadManager 在真正创建 K8s 资源前先 `StoreSandbox` placeholder，失败时 rollback K8s 资源和 store。成功路径必须等 `SandboxReconciler` 收到 Ready、拿到 PodIP、并 TCP probe entrypoint 后才把 store 更新为可路由信息。这减少了“session 已返回但 Pod 还不可用”的竞态。

- **WarmPool 交给 agent-sandbox 做 ownerReference adoption**：AgentCube 只创建 `SandboxTemplate` / `SandboxWarmPool` / `SandboxClaim`，真正的 pre-warmed Pod 选择和领养仍由 agent-sandbox extension controller 完成。这样 AgentCube 获得近 0 冷启动，但不用维护自己的 Pod 池和并发抢占协议。

- **PicoD 用 HTTP + JWT 替代 SSH**：PicoD 是 sandbox 内最薄的执行面，`POST /api/execute` 执行命令，`/api/files` 做文件操作。当前代码已经从早期“客户端私钥签名”演进到“Router 持有 RSA 私钥、PicoD 校验 Router 公钥”的模型：Router 创建 `picod-router-identity` Secret，WorkloadManager 从 Secret 缓存 public key，再注入 `PICOD_AUTH_PUBLIC_KEY`。这降低 SDK 复杂度，但也让 Router 成为更强的信任边界。

- **mTLS 是可选增强，不阻断低延迟路径**：`pkg/mtls` 支持文件热加载证书和 SPIFFE ID 校验，Helm 可以通过 SPIRE sidecar 给 Router / WorkloadManager 注入 SVID。Router→WorkloadManager 可 mTLS，Router→PicoD 当前仍主要走 JWT，以避免每个短会话 sandbox 的 TLS 握手成本。

- **文档和代码处在快速收敛期**：README 仍标注 Proposal / Early Design Phase；`docs/agentcube/docs/architecture/security.md` 还描述“客户端私钥不离开本机”的旧模型，而 `docs/agentcube/blog/release-v0.1.0/index.md` 与代码已经变成 Router→PicoD JWT security chain。分析时应以 HEAD 代码为准。

## 与 agent-sandbox 的结合方式

| 维度 | agent-sandbox | AgentCube |
|------|---------------|-----------|
| 抽象层 | 基础设施原语：`Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` | 产品化会话层：`AgentRuntime` / `CodeInterpreter` + Router + SDK |
| 用户入口 | `kubectl apply Sandbox/SandboxClaim` 或 SDK 直接管 Sandbox | HTTP invocation API、Python SDK、LangChain/Dify/CLI |
| 生命周期语义 | 1 个 Sandbox = 1 个有状态隔离 Pod，可暂停/恢复/过期 | 1 个 session = 1 个 Sandbox，附加 session header、activity、TTL、GC |
| WarmPool | 提供 WarmPool 和 Claim adoption 机制 | `CodeInterpreter.spec.warmPoolSize` 驱动创建 Template/WarmPool，首次调用时创建 Claim |
| 路由 | headless Service / Pod 访问由上层决定 | Router 根据 `SandboxInfo.EntryPoints` 反向代理到 PodIP:port |
| 状态存储 | K8s API / Status | Redis/ValKey session registry，跨 Router 副本共享 |
| 隔离策略 | 委托 K8s `runtimeClassName` / NetworkPolicy / securityContext | 在 CRD 模板中暴露 `runtimeClassName` / resources，默认 image 可跑 PicoD |
| 安全边界 | 运行时隔离与 K8s 原语 | Router JWT、可选 WorkloadManager auth、可选 SPIFFE/mTLS |

结合后的层次可以概括成：

```
Developer API / SDK
      │
      ▼
AgentCube CRD + Router session API
      │
      ▼
WorkloadManager translates AgentCube intent
      │
      ▼
agent-sandbox CRDs own lifecycle mechanics
      │
      ▼
Kubernetes Pod / RuntimeClass / NetworkPolicy / Service
```

最重要的设计收益是：AgentCube 没有把“AI Agent 平台”做成另一个私有调度器，而是把 AI Agent 的会话和工具调用语义加在 `agent-sandbox` 上。底层依然能继承 `agent-sandbox` 的 gVisor/Kata/NetworkPolicy/WarmPool 能力，上层则补齐了 HTTP/API/SDK/Redis session registry 这些 agent 应用真正需要的东西。

## 关键组件深入解读

### WorkloadManager：从 AgentCube CRD 到 agent-sandbox CRD

核心转换在 `pkg/workloadmanager/workload_builder.go`。`buildSandboxByAgentRuntime` 读取 `AgentRuntime`，复制 `spec.podTemplate.spec`，归一化空 `runtimeClassName`，生成 sessionID 和随机后缀 sandboxName，然后构造 `agent-sandbox` 的 `Sandbox`。这条路径完全保留用户的 PodSpec，适合通用 agent runtime。

`buildSandboxByCodeInterpreter` 更专门：先检查 `authMode=picod` 时 public key 是否已缓存，然后为没有 ports 的 CodeInterpreter 默认补 `/` + `8080/HTTP`。如果 `warmPoolSize > 0`，它不直接创建完整 Sandbox，而是创建 `SandboxClaim(templateRef = codeInterpreterName)`，并返回一个简化 Sandbox 只用于等待/记录；如果没有 WarmPool，则构造带 PicoD image/env/resources 的直接 Sandbox。这个分叉把“冷启动路径”和“热领取路径”压在同一个创建 API 后面。

### Router：session header 驱动的数据面

Router 的主逻辑在 `pkg/router/handlers.go`。`handleInvoke` 读取 `x-agentcube-session-id`：没有就让 `SessionManager` 调 WorkloadManager 创建，有就从 store 查 `SandboxInfo`。随后按请求 path 匹配 `SandboxInfo.EntryPoints`，用 `httputil.NewSingleHostReverseProxy` 转发，响应里始终写回 `x-agentcube-session-id`。

值得注意的是 JWT 签名发生在 Router，而不是 SDK。`generateSandboxJWT` 给 `Sandbox` / `SandboxClaim` 类型的后端请求加 `Authorization: Bearer <token>`，claim 只包含 `session_id` 加标准 `exp/iat/iss`。PicoD 因此只信 Router 的私钥，不需要自己访问 Redis 或 K8s API。

### PicoD：sandbox 内的最小执行面

PicoD 在 `pkg/picod/`：启动时必须从 `PICOD_AUTH_PUBLIC_KEY` 读取 PEM 公钥；`/api` 组全部挂 JWT middleware；`/api/execute` 用 `exec.CommandContext` 执行命令并返回 stdout/stderr/exit_code；文件 API 先调用 path sanitizer，把读写限制在 workspace 下。它明确“不做生命周期管理”，生命周期全部留给 WorkloadManager + agent-sandbox。

### Redis / ValKey：session registry 而非任务队列

`pkg/store` 的模型很薄：`session:{id}` 保存 `SandboxInfo` JSON；`session:expiry` 按 `ExpiresAt` 排序；`session:last_activity` 按最近请求时间排序。Router 更新 last activity，WorkloadManager GC 查询两个 sorted set 后删除 K8s 资源和 store 记录。这里没有复杂任务队列，只有 session registry，这使 Router 副本天然无状态。

## 风险与演进信号

- **项目仍在 alpha / proposal 到 release 的过渡期**：README 还写 Early Design，release 文档写 v0.1.0。字段命名也有历史痕迹，比如 `AgentRuntime.spec.targetPort` vs `CodeInterpreter.spec.ports`，`podTemplate` vs `template`。
- **Router 是强信任边界**：当前 Router 持有 PicoD 私钥并能为任何 session 签执行请求。相比“客户端私钥不出本机”，这更容易用，但要靠 Router auth、mTLS、RBAC、审计来补强。
- **WorkloadManager 目前承担两种职责**：既是 HTTP control plane，又跑 controller-runtime manager 和 GC。规模变大后可能会拆成 API server / reconciler / GC 三个部署单元。
- **agent-sandbox 版本偏早**：依赖 `v0.1.1`，而本 wiki 之前分析的是 `v0.4.5+11`。AgentCube 当前锁定的 API 可能需要跟随 agent-sandbox 后续 v1alpha1 演进。
- **文档安全模型有滞后**：应优先看 `docs/agentcube/blog/release-v0.1.0/index.md` 和代码，而不是旧的 `docs/agentcube/docs/architecture/security.md`。

## 代码统计与测试信号

- 仓库规模：326 个非 `.git` 文件，约 16 MB。
- 主要语言：Go 1.24.4 + Python 3.10+；根模块 `github.com/volcano-sh/agentcube`。
- Go 单元测试文件：33 个，覆盖 router / workloadmanager / picod / mtls / store / api。
- 最近 30 天活跃文件集中在 `pkg/workloadmanager/workload_builder.go`、`pkg/store/store_redis.go`、`pkg/picod/server.go`、LangChain 集成和 E2E 脚本。
- 最近提交显示主线在收敛可靠性与安全：typed informers/listers、LangChain mTLS E2E、Redis EXISTS 优化、SPIFFE mTLS、entrypoint readiness race 修复。
