---
title: AgentCube 架构与设计思路分析
tags: [architecture, ai-agent, code-interpreter, kubernetes, volcano, agent-sandbox, serverless]
date: 2026-06-01
sources: [agentcube-architecture-analysis.md]
related: ["[[agentcube]]", "[[agent-sandbox]]", "[[kubernetes]]", "[[declarative-agent-management]]", "[[agent-credential-isolation]]"]
---

# AgentCube 架构与设计思路分析

> 原文：`raw/agentcube-architecture-analysis.md` · 仓库：https://github.com/volcano-sh/agentcube · 分析版本 HEAD `208da32`（2026-06-01）

## 一句话定位

`volcano-sh/agentcube` 是 Volcano 社区面向 AI Agent / Code Interpreter 工作负载的 **serverless session orchestration layer**：上层用 `AgentRuntime` / `CodeInterpreter` 两个 CRD 表达"可被调用的 agent/runtime 模板"，中层用 Router + WorkloadManager + Redis/ValKey 管 session、路由、GC 和预热，下层直接复用 [[agent-sandbox]] 的 `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` 来真正创建隔离执行环境。

它和 [[agent-sandbox]] 不是竞争关系，而是更明确的上下层关系：[[agent-sandbox]] 提供"一个稳定、有状态、可预热/可领取的 Sandbox 原语"，AgentCube 把这个原语包装成"开发者能通过 HTTP/SDK 调用的 AgentRuntime / CodeInterpreter 会话服务"。

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

| 层 / 模块 | 职责 |
|----------|------|
| **AgentCube API 层** | 定义 `AgentRuntime` / `CodeInterpreter` 两个面向用户的 CRD。前者保留完整 `PodSpec`，后者收敛成 image/resources/runtimeClass/authMode/warmPoolSize。 |
| **数据面 Router** | 暴露 invocation API，按 `x-agentcube-session-id` 做 session affinity；没 session 时调用 WorkloadManager 创建；有 session 时查 Redis/ValKey；最后反向代理到 sandbox endpoint。 |
| **控制面 WorkloadManager** | 读 AgentCube CRD，构造 [[agent-sandbox]] CR，等待 Sandbox Ready，探测 entrypoint，写 session store，并周期性 GC。 |
| **Sandbox 内 runtime** | PicoD 用轻量 HTTP API 替换 SSH：执行命令、上传/下载/列文件、workspace path jail、JWT 验证、32MB body limit。 |
| **状态存储** | Redis / ValKey 抽象；`session:{id}` 保存 `SandboxInfo`，两个 sorted set 分别索引 `ExpiresAt` 和 `LastActivityAt`。 |
| **安全与身份** | Router→PicoD 用 RS256 JWT；Router→WorkloadManager 可用 SA token 或 SPIFFE/mTLS；mTLS 文件来源可来自 SPIRE / cert-manager / 静态 Secret。 |
| **SDK / 集成** | Python SDK、LangChain Deep Agents backend、Dify plugin、kubectl 风格 CLI，把底层 session API 包成开发者接口。 |
| **部署与 E2E** | Helm 安装 Router/WorkloadManager/CRDs/SPIRE；E2E 覆盖 CodeInterpreter、WarmPool、[[agent-sandbox]] 安装和 session 生命周期。 |

## 关键数据流

### 无 session 的首次调用

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

### CodeInterpreter WarmPool 路径

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

## 设计决策与哲学

- **把 [[agent-sandbox]] 当 substrate，不重新实现 Sandbox controller**：`go.mod` 直接依赖 `sigs.k8s.io/agent-sandbox v0.1.1`，WorkloadManager 构造 `agents.x-k8s.io/Sandbox` 和 `extensions.agents.x-k8s.io/SandboxClaim`。AgentCube 自己不碰 Pod reconcile 细节，专注 session API、路由、GC、SDK 和集成。

- **两个 CRD 对应两类 AI workload**：`AgentRuntime` 允许完整 `PodSpec`，适合长会话 agent、volume、credential、sidecar；`CodeInterpreter` 收敛成 image/resources/runtimeClass/authMode/warmPoolSize，适合执行不可信代码。也因此只有 CodeInterpreter 一等支持 `warmPoolSize`，因为 code interpreter 更需要低冷启动延迟。

- **Router / WorkloadManager 分平面**：Router 是高频数据面，负责 session header、反向代理、路径匹配和并发限制；WorkloadManager 是低频控制面，负责 [[kubernetes]] API、informer、Sandbox 创建和 GC。这样 Router 可以水平扩展，状态放进 Redis/ValKey，而不是把请求路径绑死在 controller 进程内。

- **创建先写 placeholder，再等 Ready，再 update store**：WorkloadManager 在真正创建 K8s 资源前先 `StoreSandbox` placeholder，失败时 rollback K8s 资源和 store。成功路径必须等 Ready、拿到 PodIP、并 TCP probe entrypoint 后才把 store 更新为可路由信息。

- **PicoD 用 HTTP + JWT 替代 SSH**：PicoD 是 sandbox 内最薄的执行面，`POST /api/execute` 执行命令，`/api/files` 做文件操作。当前代码已经从早期"客户端私钥签名"演进到"Router 持有 RSA 私钥、PicoD 校验 Router 公钥"的模型：Router 创建 `picod-router-identity` Secret，WorkloadManager 从 Secret 缓存 public key，再注入 `PICOD_AUTH_PUBLIC_KEY`。这降低 SDK 复杂度，但也让 Router 成为更强的信任边界。

- **mTLS 是可选增强，不阻断低延迟路径**：`pkg/mtls` 支持文件热加载证书和 SPIFFE ID 校验，Helm 可以通过 SPIRE sidecar 给 Router / WorkloadManager 注入 SVID。Router→WorkloadManager 可 mTLS，Router→PicoD 当前仍主要走 JWT，以避免每个短会话 sandbox 的 TLS 握手成本。

## 与 agent-sandbox 的结合方式

| 维度 | [[agent-sandbox]] | AgentCube |
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

最重要的设计收益是：AgentCube 没有把"AI Agent 平台"做成另一个私有调度器，而是把 AI Agent 的会话和工具调用语义加在 [[agent-sandbox]] 上。底层依然能继承 [[agent-sandbox]] 的 gVisor/Kata/NetworkPolicy/WarmPool 能力，上层则补齐了 HTTP/API/SDK/Redis session registry 这些 agent 应用真正需要的东西。

## 关键组件深入解读

### WorkloadManager：从 AgentCube CRD 到 agent-sandbox CRD

核心转换在 `pkg/workloadmanager/workload_builder.go`。`buildSandboxByAgentRuntime` 读取 `AgentRuntime`，复制 `spec.podTemplate.spec`，归一化空 `runtimeClassName`，生成 sessionID 和随机后缀 sandboxName，然后构造 [[agent-sandbox]] 的 `Sandbox`。这条路径完全保留用户的 PodSpec，适合通用 agent runtime。

`buildSandboxByCodeInterpreter` 更专门：先检查 `authMode=picod` 时 public key 是否已缓存，然后为没有 ports 的 CodeInterpreter 默认补 `/` + `8080/HTTP`。如果 `warmPoolSize > 0`，它不直接创建完整 Sandbox，而是创建 `SandboxClaim(templateRef = codeInterpreterName)`；如果没有 WarmPool，则构造带 PicoD image/env/resources 的直接 Sandbox。

## 风险与演进信号

- **项目仍在 alpha / proposal 到 release 的过渡期**：README 还写 Early Design，release 文档写 v0.1.0。字段命名也有历史痕迹，比如 `AgentRuntime.spec.targetPort` vs `CodeInterpreter.spec.ports`，`podTemplate` vs `template`。
- **Router 是强信任边界**：当前 Router 持有 PicoD 私钥并能为任何 session 签执行请求。相比"客户端私钥不出本机"，这更容易用，但要靠 Router auth、mTLS、RBAC、审计来补强。
- **WorkloadManager 目前承担两种职责**：既是 HTTP control plane，又跑 controller-runtime manager 和 GC。规模变大后可能会拆成 API server / reconciler / GC 三个部署单元。
- **agent-sandbox 版本偏早**：依赖 `v0.1.1`，而本 wiki 之前分析的是 `v0.4.5+11`。AgentCube 当前锁定的 API 可能需要跟随 [[agent-sandbox]] 后续 v1alpha1 演进。

## 相关页面

- [[agent-sandbox]]
- [[kubernetes]]
- [[declarative-agent-management]]
- [[agent-credential-isolation]]
