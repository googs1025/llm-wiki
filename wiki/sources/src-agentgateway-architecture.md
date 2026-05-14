---
title: agentgateway 架构与设计思路分析
tags: [architecture, ai-infra, cloud-native, gateway, llm, mcp]
date: 2026-05-13
sources: [agentgateway-architecture-analysis.md]
related: [[agentgateway]], [[mcp]], [[gateway-api]], [[cel]], [[xds]], [[hbone]], [[HiClaw]], [[agent-sandbox]]
---

# agentgateway 架构与设计思路分析

> 原文：`raw/agentgateway-architecture-analysis.md` · 仓库：[agentgateway/agentgateway](https://github.com/agentgateway/agentgateway) · 分析版本 v1.2.0-alpha.2+24（HEAD `9ca3e04`）

## 一句话定位

[[agentgateway]] 是面向 AI 流量的 L7 代理：把 **LLM API**（OpenAI / Anthropic / Gemini / Bedrock / Vertex / Azure / Copilot）、**MCP 工具调用**、**A2A Agent 间通信** 统一在一个 Rust 数据面里，用 [[gateway-api|Gateway API]] CRD + [[xds|xDS]] 做声明式控制面分发。本质上是「[[istio|Istio]] 的控制面骨架 + 为 AI 协议特化的 Rust 数据面」的组合——把 mesh 经过验证的反应式配置分发、KRT 反应式表、[[hbone|HBONE]] mTLS 隧道全套基建搬来做 AI Gateway。

## 核心架构图

```
                  ┌──────────────────────────────────────────────┐
                  │  CONTROL PLANE  (Go, controller/)            │
                  │                                              │
   K8s API ──▶  ┌─┴────────┐   KRT collections (Istio reactive) │
                │ Watch     │   ┌─────────────┐                  │
                │ Gateway   │──▶│ Translator  │                  │
                │ HTTPRoute │   │ K8s → xDS   │                  │
                │ CRDs:     │   └──────┬──────┘                  │
                │  AGPol    │          │                         │
                │  AGBe     │   ┌──────▼──────┐    ┌──────────┐  │
                │  AGParams │   │ ADS Server  │◄──▶│ Deployer │  │
                └───────────┘   │ SotW+Delta  │    │ Helm/Pod │  │
                  ▲             └──────┬──────┘    └──────────┘  │
                  │                    │ gRPC                    │
                  │ kubectl/CRD        │ DeltaAggregatedResources│
                  └──────┐             │                         │
                         │             ▼                         │
   ┌────────────────────────────────────────────────────────────┘
   │                     │ resource.Resource (oneof 9):
   │                     │ Bind/Listener/Route/TCPRoute/Backend/
   │                     │ Policy/Workload/Service/RouteGroup
   │                     │
   │  ┌──────────────────▼────────────────────────────────────┐
   │  │ DATA PLANE (Rust, crates/agentgateway*)               │
   │  │                                                       │
   │  │  agentgateway-app/   ← thin binary, signal/tracing    │
   │  │       │                                               │
   │  │       └─▶ agentgateway/lib                            │
   │  │             ├─ control/   xds AdsClient (delta)       │
   │  │             ├─ state_manager + store/                 │
   │  │             │     Stores { binds, discovery, ads }    │
   │  │             ├─ proxy/                                 │
   │  │             │    ├─ gateway.rs  (TCP accept loop)     │
   │  │             │    ├─ httpproxy.rs (route + policy)     │
   │  │             │    ├─ tcpproxy.rs                       │
   │  │             │    └─ pool (connection)                 │
   │  │             ├─ http/      (filters, retry, transform) │
   │  │             ├─ transport/ (HBONE = mTLS HTTP/2)       │
   │  │             ├─ llm/       7 providers behind          │
   │  │             │             AIProvider enum + Provider  │
   │  │             │             trait, OpenAI-compat unify  │
   │  │             ├─ mcp/       App/Relay + upstream/       │
   │  │             │             stdio|HTTP|SSE|Streamable   │
   │  │             │             federation, CEL RBAC        │
   │  │             ├─ a2a/       classifier + URL rewriter   │
   │  │             ├─ cel/       crates/cel-fork + celx      │
   │  │             ├─ telemetry/ OTLP + access log           │
   │  │             └─ management/ admin + debug + ui         │
   │  │                                                       │
   │  └───────────────────────────────────────────────────────┘
   │
   │  ┌──────────────────────────────────────────────────────┐
   │  │ UI (TypeScript, ui/, Next.js)                        │
   │  │   /ui/ HTTP → management → live config view          │
   │  └──────────────────────────────────────────────────────┘
```

## 模块分层

### Workspace 顶层

| 模块 | 语言 | 角色 |
|------|------|------|
| `crates/agentgateway-app/` | Rust | 薄壳二进制（信号 / 日志 / panic hook） |
| `crates/agentgateway/` | Rust | 数据面主库，三协议网关都在此 |
| `crates/xds/` | Rust | xDS 客户端 + proto 绑定 |
| `crates/hbone/` | Rust | Istio HBONE（mTLS over HTTP/2 CONNECT）传输 |
| `crates/celx/` + `crates/cel-fork/` | Rust | CEL 策略求值（fork 加 HTTP 集成） |
| `controller/` | Go | controller-runtime + ADS server + Helm deployer |
| `api/` | Go | resource.proto 的 Go 绑定 |
| `ui/` | TypeScript | Next.js 管理 UI |

### 数据面分层（`crates/agentgateway/src/`）

| 层 | 模块 | 职责 |
|----|------|------|
| L1 配置 | `control/` `config.rs` | 本地 yaml + xDS client + outbound client |
| L2 状态 | `state_manager.rs` `store/` | 反应式 Store 聚合 binds/discovery/ads |
| L3 代理 | `proxy/gateway.rs` `proxy/httpproxy.rs` | TCP accept → TLS → route → upstream |
| L4 HTTP | `http/` | filter chain / retry / timeout / transform |
| L5 协议 | `llm/` `mcp/` `a2a/` | 三个 AI 协议网关 |
| L6 横切 | `cel/` `telemetry/` `transport/` | 策略求值 / 可观测 / HBONE 隧道 |
| L7 管理 | `management/` `ui.rs` | 管理 HTTP / 健康 / UI 静态资源 |

### 自家 CRD

| CRD | 短名 | 用途 |
|-----|------|------|
| `AgentgatewayPolicy` | `agpol` | CEL 策略容器，挂在 Gateway / Listener / Route 上 |
| `AgentgatewayBackend` | `agbe` | 后端配置：`AI` / `MCP` / `A2A` / `Static` |
| `AgentgatewayParameters` | — | GatewayClass 级 Pod 模板参数 |

上游 [[gateway-api|Gateway API]] 直接复用：`Gateway` `HTTPRoute` `GRPCRoute` `TCPRoute` `TLSRoute` `GatewayClass` `ListenerSet` `InferencePool`。

## 关键数据流

### 一次 LLM 请求的端到端数据流

```
Client (curl / OpenAI SDK)
  │  POST /v1/chat/completions   (model: "gpt-4")
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ proxy/gateway.rs::run()                                         │
│    TCP accept (multi-thread tokio runtime)                      │
│       │                                                         │
│       ▼ LazyConfigAcceptor                                      │
│    Peek SNI → 查 binds 找到匹配的 Listener TLS 配置             │
│       │                                                         │
│       ▼                                                         │
│    rustls TLS termination                                       │
│       │                                                         │
│       ▼                                                         │
│    hyper HTTP/1.1 or H2 framing                                 │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ proxy/httpproxy.rs::proxy()                                     │
│  1. select_route_chain()  ← 按 path / header / method 匹配      │
│  2. 拿到 Route + Policy[] + Backend[]                           │
│  3. http/filters 执行：header 修改 / retry / timeout / transform│
│  4. CEL 授权（cel/ + agpol 引用的策略 IR）                      │
│     ─ 取请求 header/body/JWT claims → 求值 → allow|deny         │
│  5. weighted_random_choice 选 Backend                           │
│       │                                                         │
│       ▼                                                         │
│  6. 识别 Backend.kind = AI{provider: OpenAI|...}                │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ llm/mod.rs → dispatch by AIProvider enum                        │
│   provider.transform_request()                                  │
│     ├─ openai.rs   passthrough（已是 OpenAI 格式）              │
│     ├─ anthropic.rs OpenAI → Anthropic messages                 │
│     ├─ gemini.rs   OpenAI → Gemini generateContent              │
│     ├─ bedrock.rs  OpenAI → AWS SigV4 + Bedrock invoke          │
│     ├─ vertex.rs   gcp_auth + OpenAI → Vertex                   │
│     ├─ azure.rs    OpenAI → Azure OpenAI endpoint               │
│     └─ copilot.rs  GitHub Copilot                               │
│   guardrails (pre-flight)                                       │
│     regex / moderation / model-armor / content-safety / webhook │
│   token-bucket / cost limit                                     │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│ client/  →  reqwest+hyper                                       │
│   ─ 走 connection pool (crates/pool)                            │
│   ─ 走 HBONE tunnel  ?  (若 backend 是 mesh workload，          │
│       transport/hbone：mTLS+H2 CONNECT 隧道)                    │
│   ─ 否则普通 TLS / plaintext                                    │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
   Upstream LLM provider (api.openai.com / api.anthropic.com / ...)
       │
       ▼ 响应（流式 SSE / chunked）
┌─────────────────────────────────────────────────────────────────┐
│ provider.transform_response()                                   │
│   ─ 反向 schema 转换 → 统一 OpenAI 格式                         │
│   ─ guardrails (post-flight)                                    │
│   ─ telemetry: tokens_in / tokens_out / cost / latency          │
│   ─ access log + OTLP span                                      │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
   Client receives OpenAI-compatible SSE stream
```

### 控制面 → 数据面 配置分发

```
kubectl apply Gateway/HTTPRoute/agpol/agbe.yaml
      │
      ▼
controller-runtime watch → KRT collection mutate
      │
      ▼
Translator: K8s objs → resource.Resource oneof
   ├─ Bind          (TCP listen addr)
   ├─ Listener      (TLS / SNI / protocol)
   ├─ Route         (HTTP route + filters)
   ├─ TCPRoute
   ├─ Backend       (AI / MCP / A2A / Service / Static)
   ├─ Policy        (CEL IR + transform + retry + ratelimit)
   ├─ RouteGroup
   └─ Workload/Service (Istio Address 兼容)
      │
      ▼
ADS Server (gRPC, controller/pkg/xds/server.go)
   DeltaAggregatedDiscoveryService
      │
      ▼ Delta xDS（增量）
agentgateway/control/AdsClient
      │
      ▼ apply
state_manager + Stores { binds, discovery }
      │
      ▼ 触发
proxy/gateway 重建 Listener / Route 索引
```

xDS 资源类型只有两种：
- `istio.workload.Address` —— 兼容 [[istio|Istio]] ambient mesh 的 workload/service 发现
- `agentgateway.dev.resource.Resource` —— 主资源 oneof（9 个变体覆盖整个数据面状态）

**只用 Delta ADS**，单连接复用，不每种资源一个 stream。

### 一次 MCP 工具调用

```
MCP Client (Cursor / Claude Desktop / OpenAI Responses API)
  │ JSON-RPC over stdio | HTTP Streamable | SSE
  ▼
mcp/router.rs  ── 路由层根据 session id 找到对应的上游
  │
  ▼
mcp/handler.rs  ── 工具列表 federation（merge_tools）
  │     │
  │     └─ 多个 upstream MCP server 的 tools/list 合并
  │        + CEL RBAC 过滤（mcp/rbac.rs）
  │
  ▼ tools/call
mcp/upstream/{stdio.rs | streamablehttp.rs | sse.rs | openapi.rs}
  │
  ▼
Upstream MCP server / OpenAPI endpoint
```

下游 transport：HTTP Streamable / SSE / stdio。上游 transport：同三种 + `openapi.rs` 把任何 OpenAPI spec 自动桥接成 MCP tools（无需上游侧改造）。federation 通过 `handler.rs::merge_tools()` 合并多个 MCP server 的工具集，命名空间用 `__` 前缀避冲突，CEL RBAC 按 client identity 过滤可见性。

### A2A（Agent-to-Agent）

```
Agent Client
  │ HTTP GET /.well-known/agent-card.json
  ▼
a2a/mod.rs  ── 拦截 Agent Card 发现请求
  │  ─ 透传上游，但 *重写响应里的 URL*
  │    把 upstream 真实地址换成 gateway 自身地址
  │  ─ 之后所有 Agent 调用都走回 gateway，自然拿到 policy/observability
```

A2A 是三协议里最轻的——核心就 URL 重写。Google A2A 协议把入口放在 Agent Card well-known endpoint，gateway 控制了发现，就控制了所有后续调用。

## 设计决策与哲学

- **沿用 [[istio|Istio]] 的基建做 AI Gateway**：Gateway API + KRT collections + xDS + HBONE 全套复用，控制面是 Istio 的影子结构。开发团队（Solo.io / Istio 系）选择不重新发明轮子，把 mesh 经过验证的反应式配置分发 + 反应式表建模 + mTLS 隧道搬来，**只把数据面替换成「专为 AI 协议优化的 Rust 代理」**。Day 1 即获得完整 mesh 兼容性 + 控制面/数据面可独立替换的解耦能力。
- **三协议共享同一条 pipeline**：LLM / MCP / A2A 在数据面共享 Route / Policy / Backend / CEL 求值的同一条管道，差别只在 `Backend.kind` 决定走哪个 provider 适配器。带来单一策略语言 + 统一观测 + 统一 mTLS。
- **CEL 作为策略 IR**：所有授权 / 转换 / 速率限制都被编译成 [[cel|CEL]] 表达式存到 `Policy.spec.expression`，运行时由 Rust 数据面解释执行。controller 不预编译，避免 Go/Rust CEL 实现差异。用 `cel-fork + celx` 是因为原生 cel-rust 缺与 HTTP 请求对象的深度集成。
- **凭据托管堵 prompt injection**：与 [[HiClaw]] 的 Higress 凭据托管哲学一致——LLM provider 真凭据（OpenAI key / AWS IAM / GCP service account）放在 backend secret，gateway 在请求时注入，Agent / 业务端只面对 gateway 自己的认证（JWT / API key / mTLS）。Agent 即使被注入也偷不到真凭据。详见 [[agent-credential-isolation]]。
- **控制面 / 数据面通过 proto 解耦**：Go controller + Rust 数据面只用 `resource.Resource` proto 通信，可独立演进。未来能换掉任一端（Crossplane 直产 xDS / envoy 实现 agentgateway proto 扩展）。
- **两个 tokio runtime 拆分热路径**：main runtime 跑控制面（admin HTTP / xDS / reload），worker runtime 跑数据面 accept，避免控制面任务抢占 worker 影响 P99。
- **OpenAI 兼容 API 做统一前门**：客户端代码零改造接 7 个 LLM provider；非 OpenAI 特性（Gemini 多模态、Bedrock 私有模型）通过扩展字段暴露。

## 关键组件深入：LLM Provider 适配器

`crates/agentgateway/src/llm/` 是数据面最厚的协议适配层。统一抽象骨架：

```rust
enum AIProvider {
    OpenAI, Anthropic, Gemini, Bedrock, Vertex, Azure, Copilot,
}

trait Provider {
    async fn transform_request(&self, req: OpenAIRequest) -> ProviderRequest;
    async fn transform_response(&self, resp: ProviderResponse) -> OpenAIResponse;
    async fn stream_chunk(&self, chunk: Bytes) -> OpenAIChunk;
}
```

外部统一暴露 **OpenAI 兼容 API**（`/v1/chat/completions` / `/v1/embeddings`），内部 dispatch 到 provider 双向翻译。

**Guardrails** —— LLM 流量特有的内容审查，pre-flight / post-flight 双向，支持 regex / OpenAI Moderation / AWS Bedrock Guardrails / Google Model Armor / Azure Content Safety / 自定义 webhook，每 backend 按声明顺序串成 chain。

**负载均衡** —— 跨副本走 **two-random-choice**（tail-latency 比 round-robin 稳）；跨 model alias 走 weighted random。

## 与 [[HiClaw]] / [[agent-sandbox]] 的关系

- **跟 [[HiClaw]] 是不同层次互补**：HiClaw 在应用层做 Agent 协作（Matrix IM + Worker CRD），agentgateway 在基础设施层做 AI 流量代理。HiClaw 的 Worker 跑用户代码访问 LLM / MCP 时，理论上可以让 agentgateway 当出口代理，由 agentgateway 接管凭据 / 审计 / guardrails。
- **跟 [[agent-sandbox]] 拼成 AI 平台底盘**：agent-sandbox 做 Agent **运行时隔离**（Pod + gVisor / Kata + NetworkPolicy），agentgateway 做 Agent **出口流量治理**（LLM / MCP / A2A）。两者并集 = AI 工作负载完整的"运行 + 通信"治理面。NetworkPolicy 限制 Sandbox Pod 出口只能走 agentgateway，强制所有 AI 流量过 policy + guardrails + 审计。

```
┌──────────────────────────────────────────────────────┐
│  AI Platform Day 0                                   │
│                                                      │
│  ┌─────────────────────┐    ┌──────────────────────┐ │
│  │ Sandbox             │    │ agentgateway         │ │
│  │ (gVisor pod)        │───▶│ (route LLM/MCP/A2A)  │ │
│  │  Agent code runs    │    │  ─ CEL policy        │ │
│  │  here, NetworkPolicy│    │  ─ Guardrails        │ │
│  │  denies直连云元数据 │    │  ─ Credential inject │ │
│  └─────────────────────┘    └──────────┬───────────┘ │
│                                        │             │
└────────────────────────────────────────┼─────────────┘
                                         ▼
                            api.openai.com / api.anthropic.com / ...
```

## 相关页面

- [[agentgateway]] —— 项目主页
- [[mcp]] —— MCP 协议（agentgateway MCP gateway 的协议基础）
- [[gateway-api]] —— K8s Gateway API（agentgateway 控制面 API 基础）
- [[xds]] —— xDS 协议（控制面 → 数据面分发）
- [[hbone]] —— Istio HBONE 隧道（agentgateway 跟 mesh 互操作）
- [[cel]] —— Common Expression Language（agentgateway 策略 IR）
- [[istio]] —— Istio（agentgateway 控制面骨架来源）
- [[HiClaw]] —— 应用层 Agent 协作平台（互补关系）
- [[agent-sandbox]] —— K8s SIG 的 AI Agent 运行时隔离（互补关系）
- [[ai-agent-plugin-patterns]] —— Agent 外挂设计原则
- [[agent-credential-isolation]] —— Agent 凭据零暴露模式
