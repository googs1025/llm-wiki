# agentgateway 架构分析

> 源仓库：`agentgateway/agentgateway`（v1.2.0-alpha.2+24，HEAD `9ca3e04`）
> 本地副本：`/tmp/ingest-codebase-a0d758f5`（clone 不入库）
> 分析方式：`ingest-codebase` skill 调度 code-explorer deep 模式，三个 Explore subagent 并行扫描后综合

---

## 1. 一句话定位

agentgateway 是面向 **AI 流量** 的 L7 代理：把 **LLM API**（OpenAI / Anthropic / Gemini / Bedrock / Vertex / Azure / Copilot）、**MCP 工具调用**、**A2A Agent 间通信** 统一在一个 Rust 数据面里，用 **Gateway API CRD + xDS** 做声明式控制面分发。本质上是「Istio 的控制面骨架 + 为 AI 协议特化的 Rust 数据面」的组合，把 mesh 经过验证的反应式配置分发 / KRT 反应式表 / HBONE mTLS 隧道全套基础设施搬来做 AI Gateway。

---

## 2. 核心架构图

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

---

## 3. 模块分层

### 3.1 顶层 workspace 结构

| 路径 | 语言 | 角色 |
|------|------|------|
| `crates/agentgateway-app/` | Rust | 薄壳二进制：信号 / 日志 / panic hook |
| `crates/agentgateway/` | Rust | 数据面主库，所有协议网关都在这里 |
| `crates/xds/` | Rust | xDS 客户端 + proto 绑定 |
| `crates/hbone/` | Rust | Istio HBONE（mTLS over HTTP/2 CONNECT）传输库 |
| `crates/celx/` | Rust | CEL 扩展函数集（在 cel-fork 之上） |
| `crates/cel-fork/` | Rust | fork 的 cel-rust，加了 agentgateway 需要的语义 |
| `crates/core/` | Rust | 共享 trait / error / metric 基础 |
| `crates/pool/` | Rust | 连接池抽象 |
| `crates/protos/` | Rust | 主 proto 生成产物 |
| `controller/` | Go | Kubernetes controller + xDS server + deployer |
| `api/` | Go | resource.proto 的 Go 绑定（控制面与数据面共享 schema） |
| `architecture/` | Markdown | 官方架构文档 |
| `ui/` | TypeScript | Next.js 管理 UI |
| `examples/` | YAML / shell | 各种部署示例（kueue / cilium / openai / mcp） |
| `manifests/` | YAML | Helm chart 与 CRD 安装清单 |

### 3.2 数据面分层（`crates/agentgateway/src/`）

| 层 | 模块 | 职责 | 关键文件 |
|----|------|------|----------|
| L0 入口 | `app.rs` `lib.rs` | tokio runtime + 启动编排 | `app.rs` |
| L1 配置 | `config.rs` `control/` `client/` | 解析本地 yaml + xDS client + outbound client | `control/`, `config.rs` |
| L2 状态 | `state_manager.rs` `store/` | 反应式 Store 聚合 binds/discovery/ads | `state_manager.rs`, `store/discovery.rs` |
| L3 代理 | `proxy/` | TCP accept → TLS → route → upstream | `proxy/gateway.rs`, `proxy/httpproxy.rs`, `proxy/tcpproxy.rs` |
| L4 HTTP | `http/` `parse/` | filter chain / retry / timeout / transform | `http/policies/`, `http/filters/` |
| L5 协议 | `llm/` `mcp/` `a2a/` | 三个 AI 协议网关 | `llm/mod.rs`, `mcp/mod.rs`, `a2a/mod.rs` |
| L6 横切 | `cel/` `telemetry/` `transport/` | 策略求值 / 可观测 / HBONE | `cel/`, `telemetry/`, `transport/` |
| L7 管理 | `management/` `ui.rs` `agentcore.rs` | 管理 HTTP / 健康 / UI 静态资源 | `management/`, `ui.rs` |

### 3.3 控制面分层（`controller/pkg/`）

| 模块 | 职责 |
|------|------|
| `controller/` | controller-runtime reconciler，watch Gateway API + 自家 CRD |
| `krt/` 引用 | Istio 的 KRT collections，把对象流转成反应式表 |
| `xds/server.go` | gRPC ADS server（DeltaAggregatedDiscoveryService），SotW + Delta 两种模式 |
| `translator/` | K8s 对象 → `resource.Resource` proto 的转换器 |
| `deployer/` | 内嵌 Helm chart，为每个 Gateway 部署一个 agentgateway Pod |
| `agctl/` | CLI 工具（`config` / `trace` 子命令） |

### 3.4 自家 CRD（`controller/api/v1alpha1/`）

| CRD | 短名 | 用途 |
|-----|------|------|
| `AgentgatewayPolicy` | `agpol` | CEL 表达式容器，挂在 Gateway / Listener / Route 上做授权 / 转换 / 速率限制 |
| `AgentgatewayBackend` | `agbe` | 后端配置：`AI{provider, model_aliases}` / `MCP{transport, auth}` / `A2A` / `Static` |
| `AgentgatewayParameters` | — | GatewayClass 级 Pod 模板参数（资源 / 节点选择 / 镜像） |

上游 Gateway API 资源直接复用：`Gateway` `HTTPRoute` `GRPCRoute` `TCPRoute` `TLSRoute` `GatewayClass` `ListenerSet`（experimental）`InferencePool`（experimental）。

---

## 4. 关键数据流

### 4.1 一次 LLM 请求的端到端数据流（必出图）

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

### 4.2 控制面 → 数据面 配置分发流

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

xDS 资源类型一共两类：
- `istio.workload.Address` —— 兼容 Istio ambient mesh 的 workload / service 发现
- `agentgateway.dev.resource.Resource` —— 主资源 oneof，9 个变体覆盖整个数据面状态

控制面 **只用 Delta ADS**（不用 SotW 增量），减少全量同步开销；数据面也只订阅这两个 type URL，**单连接复用**而不是每种资源一个 stream。

### 4.3 一次 MCP 工具调用的串联

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

亮点：
- **transport 多路复用**：一个 MCP client → gateway → 多种 transport 上游（stdio 子进程 / HTTP / SSE / 直接拿 OpenAPI 定义自动生成工具）
- **OpenAPI → MCP 适配**：用 `mcp/upstream/openapi.rs` 把任何 OpenAPI spec 自动暴露成一组 MCP tool，无需上游侧改造
- **session 状态机**：`mcp/session.rs` 维护 MCP 会话生命周期（initialize → operations → close）

### 4.4 A2A（Agent-to-Agent）数据流

```
Agent Client
  │ HTTP GET /.well-known/agent-card.json
  ▼
a2a/mod.rs  ── 拦截 Agent Card 发现请求
  │  ─ 透传上游，但 *重写响应里的 URL*
  │    把 upstream 真实地址换成 gateway 自身地址
  │  ─ 之后所有 Agent 调用都走回 gateway，自然拿到 policy/observability
```

A2A 是三协议里最轻的一个——核心就 *URL 重写*。这是 Google A2A 协议的天然 hook 点：协议把入口放在 Agent Card 的 well-known endpoint，gateway 控制了发现，就控制了所有后续调用。

---

## 5. 设计决策与哲学

### 5.1 把 Istio 的基建复用到 AI 流量上

agentgateway 的整个控制面是「Istio 的影子结构」：
- **Gateway API + 自家 CRD**：Gateway / HTTPRoute / Listener 完全沿用上游 API，扩展点用 `agpol` / `agbe` 这种 *引用型* CRD 而不是改 Gateway API 本体
- **KRT collections**：Istio 的反应式表模型直接用，每个 watched resource 变成一个 collection，translator 是 collection 之间的 transform
- **xDS 协议分发**：Delta ADS over gRPC，跟 Istio control plane → envoy 数据面完全同形
- **HBONE 隧道**：直接用 Istio 的 mTLS over HTTP/2 CONNECT，让 agentgateway 数据面可以作为 ambient mesh 的一份子，跟其他 ztunnel / waypoint 互通

为什么重要：开发团队（Solo.io / Istio 系）选择不重新发明轮子。Mesh 已经验证过的「反应式配置分发 / 反应式表建模 / mTLS 隧道」全套基础设施搬过来，**只把数据面替换成「专为 AI 协议优化的 Rust 代理」**。结果是 Day 1 就有完整的 Gateway API 兼容性、跟 Istio mesh 的互操作性、并且控制面与数据面可以独立替换。

### 5.2 三协议网关共享一条 pipeline

LLM / MCP / A2A 三个网关在数据面上 **共享同一个 Route / Policy / Backend / CEL pipeline**：

```
Listener → Route 匹配 → Policy 求值 → Backend 选择 → Provider 适配器
                                                       │
                                                       ▼ 协议特化
                                                  ┌──────────┐
                                                  │ llm/     │
                                                  │ mcp/     │
                                                  │ a2a/     │
                                                  └──────────┘
```

差别只在 **Backend.kind 决定走哪个 provider 适配器**，加上「协议特有的状态机」（MCP session / A2A agent card discovery / LLM streaming）。

这种统一带来三个好处：
- **单一策略语言**：用同一套 CEL 表达式给三种协议做授权 / 转换 / 速率限制
- **统一观测**：access log / OTLP span / metric 标签都是同形的，dashboard 不用为三种协议各写一遍
- **统一证书 / mTLS**：HBONE 隧道一接，三种协议的上游连接都受同一套 mesh 身份保护

### 5.3 CEL 作为策略 IR

所有授权 / 转换 / 速率限制最终都被编译成 **CEL 表达式** 存到 `Policy.spec.expression` 字段，运行时由 Rust 端解释执行。controller 不预编译（避免 Go / Rust CEL 实现差异），数据面拿到表达式字符串后用 `cel-fork + celx` 求值。

为什么用 fork：原生 cel-rust 缺一些 agentgateway 需要的语义（特别是与 HTTP 请求对象的深度集成，header 模糊匹配，JWT claims 访问）。fork 加了这些，并通过 `celx` crate 暴露成可重用的扩展函数集。

### 5.4 凭据与多租户隔离

LLM provider 的真凭据（OpenAI key / AWS IAM / GCP service account / Azure token）放在 backend secret 里，由 gateway 在请求时注入。Agent / 业务端只面对 gateway 自己的认证（JWT / API key / mTLS），看不到真凭据。

这跟 [[HiClaw]] 的 Higress 凭据托管哲学一致：**从源头堵 prompt injection 偷 key**。Agent 即使被注入，能拿到的也只是 gateway 给的 consumer 凭据，而不是 LLM provider 的真 key。

### 5.5 解耦控制面 / 数据面

通过 xDS 协议解耦：
- 控制面是 Go，依赖 controller-runtime + KRT，适合 K8s 生态
- 数据面是 Rust，适合高性能代理（async tokio + zero-copy bytes + hyper）
- 两端 *只通过 proto* 通信，可以独立演进

意味着：未来可以单独替换控制面（比如用 Crossplane / Argo CD 直接产 xDS），或者单独替换数据面（理论上可以让 envoy 当数据面，前提是 envoy 实现 agentgateway proto 扩展）。

### 5.6 配套的 agctl CLI

`agctl` 提供两个核心子命令：
- `agctl config` —— dump 数据面 live 配置（从 management 接口取）
- `agctl trace` —— 单条请求的全链路追踪（route 匹配 + policy 求值 + backend 选择详情）

这是 mesh 类项目的常见配套（istioctl / linkerd diag），用 CLI 把 *配置实际生效情况* 与 *请求实际走向* 暴露给运维。

---

## 6. 关键组件深入：LLM Provider 适配器

`crates/agentgateway/src/llm/` 是数据面里最厚的协议适配层。

### 6.1 抽象骨架

```rust
// llm/mod.rs (示意)
enum AIProvider {
    OpenAI(OpenAIProvider),
    Anthropic(AnthropicProvider),
    Gemini(GeminiProvider),
    Bedrock(BedrockProvider),
    Vertex(VertexProvider),
    Azure(AzureProvider),
    Copilot(CopilotProvider),
}

trait Provider {
    async fn transform_request(&self, req: OpenAIRequest) -> ProviderRequest;
    async fn transform_response(&self, resp: ProviderResponse) -> OpenAIResponse;
    async fn stream_chunk(&self, chunk: Bytes) -> OpenAIChunk;
}
```

外部统一以 **OpenAI 兼容 API** 暴露（`/v1/chat/completions` / `/v1/embeddings` / ...），内部 dispatch 到 provider 适配器双向翻译。

### 6.2 Provider 子目录布局

- `llm/openai.rs` —— passthrough（请求几乎不变，加 retry 与 metric）
- `llm/anthropic.rs` —— OpenAI ↔ Anthropic messages（role 映射、tool call schema 差异、system prompt 处理）
- `llm/gemini.rs` —— OpenAI ↔ Gemini generateContent（content parts 数组 vs OpenAI string、safety settings）
- `llm/bedrock.rs` —— AWS SigV4 签名 + Bedrock runtime invoke
- `llm/vertex.rs` —— GCP `gcp_auth` 取 token + Vertex `:streamGenerateContent`
- `llm/azure.rs` —— Azure OpenAI deployment 路径 + API version 头
- `llm/copilot.rs` —— GitHub Copilot 接入

- `llm/conversion/` —— 共享转换工具（chunked SSE 解析 / JSON Schema 互转）
- `llm/policy/` —— guardrails policy 实现
- `llm/types/` —— 共享类型定义（OpenAI 完整 schema）

### 6.3 Guardrails

LLM 流量特有的内容审查层，pre-flight（请求侧）与 post-flight（响应侧）双向：
- 正则规则（敏感词 / PII 模式）
- OpenAI Moderation API
- AWS Bedrock Guardrails
- Google Model Armor
- Azure Content Safety
- Webhook（自定义外部审核）

每个 backend 可以挂任意组合，按声明顺序串成 chain。

### 6.4 负载均衡

跨 backend 副本走 **two-random-choice 算法**（mesh 经典选择，比纯 round-robin 在 tail-latency 上更稳）；跨 model alias 走 weighted random（按 `Backend.spec.ai.modelAliases[].weight`）。

---

## 7. 关键组件深入：MCP Gateway

`crates/agentgateway/src/mcp/` 把 Model Context Protocol 当作 *一等公民* 的协议网关。

### 7.1 核心三件套

| 文件 | 角色 |
|------|------|
| `mcp/router.rs` | 路由：session id → 上游 MCPInfo |
| `mcp/handler.rs` | 协议处理：tools/list / tools/call / resources / prompts |
| `mcp/session.rs` | 会话状态机：initialize / operations / shutdown |

### 7.2 Transport 多路复用

下游（client → gateway）：
- HTTP Streamable（MCP 最新 transport）
- SSE（旧版 MCP transport）
- stdio（子进程嵌入式）

上游（gateway → MCP server）：`mcp/upstream/` 下
- `stdio.rs` —— 起子进程 + JSON-RPC over pipes
- `streamablehttp.rs` —— HTTP Streamable
- `sse.rs` —— SSE
- `openapi.rs` —— 把任何 OpenAPI spec 自动桥接成 MCP tools

### 7.3 工具 Federation

`mcp/handler.rs::merge_tools()` 把多个上游 MCP server 的 `tools/list` 合并成一个 client 看到的虚拟工具集：
- 命名空间避冲突（`upstream_a__tool` / `upstream_b__tool`）
- CEL RBAC 过滤（按 client identity 决定哪些工具可见）
- 调用时根据 prefix 路由回正确上游

### 7.4 RBAC

`mcp/rbac.rs` 用 CEL 表达式定义 tool 访问规则：

```yaml
# agpol 示例（伪示意）
spec:
  expression: |
    request.tool.name in user.allowed_tools &&
    !request.tool.name.startsWith("destructive:")
```

---

## 8. 与同类项目对比

| 维度 | agentgateway | [[HiClaw]] | [[claude-context]] | OpenAI Realtime / LiteLLM |
|------|--------------|------------|--------------------|---------------------------|
| 层次 | 基础设施层（L7 代理） | 应用层（Agent 协作平台） | 应用层（MCP 工具） | 应用层（LLM 路由 SDK） |
| K8s 原生 | ✅ Gateway API + CRD | ✅ 自家 CRD | ❌ | ❌ |
| 三协议统一 | ✅ LLM + MCP + A2A | ⚠️ Agent 协作走 Matrix IM | ❌ 单 MCP | ❌ 单 LLM |
| 数据面性能 | Rust（async tokio） | Java（Higress / Envoy） | TypeScript | Python / TypeScript |
| 配置分发 | xDS Delta ADS | Higress 控制面 | 配置文件 | 进程内 |
| 与 mesh 互操作 | ✅ HBONE | ⚠️ Higress 自己的 mesh | ❌ | ❌ |
| 凭据托管 | Backend secret | Higress consumer key | ❌ | 进程内环境变量 |

跟 [[HiClaw]] 的关系最有意思：**两者其实是不同层次互补**——HiClaw 在应用层做 Agent 协作（Matrix IM + Worker CRD），agentgateway 在基础设施层做 AI 流量代理。HiClaw 的 Worker 跑用户代码访问 LLM / MCP 时，理论上完全可以让 agentgateway 当出口代理，由 agentgateway 接管凭据 / 审计 / guardrails。

---

## 9. 与 [[agent-sandbox]] 的互补关系

agent-sandbox 给 AI Agent 做 **运行时隔离**（Pod + gVisor / Kata + NetworkPolicy），agentgateway 给 AI Agent 做 **出口流量治理**（LLM / MCP / A2A 三向）。两个 K8s SIG 项目可以拼在一起做 AI 平台底盘：

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

NetworkPolicy 限制出口只能走 agentgateway → 强制所有 AI 流量经过 policy / guardrails / 审计。两者并集 = 完整的 AI 工作负载 *运行 + 通信* 治理面。

---

## 10. 性能模型

### 10.1 Tokio runtime 拆分

`crates/agentgateway-app/src/main.rs` 起两个独立 tokio runtime：
- **main runtime**：信号 / 控制面（admin HTTP / xDS client / 配置 reload）
- **worker runtime**：multi-thread，处理数据面 TCP accept + request handling

拆分动机：避免控制面任务（重 IO / 偶发计算）抢占数据面 worker，保证 P99 稳定。

### 10.2 Hot path 优化

- `bytes::Bytes` zero-copy 处理请求 / 响应体
- `crates/pool` 连接复用，避免每次重建 TLS
- HBONE H2 multiplex，多个上游连接共享 TCP / TLS 握手成本
- proto 序列化用 `prost` + `bytes` 零拷贝

### 10.3 状态更新策略

数据面状态走 `state_manager` 双缓冲：
- xDS 推来的更新先写到 "next" snapshot
- 应用完成后原子切换指针，避免 hot path 看到中间状态

---

## 11. 设计权衡与开放问题

| 选择 | 收益 | 代价 / 风险 |
|------|------|-------------|
| 沿用 Istio xDS / KRT / HBONE | Day 1 完整 mesh 兼容性 | 学习曲线陡（KRT 心智模型不直观） |
| 三协议共享 pipeline | 单一策略语言 + 统一观测 | LLM 与 MCP 状态机差别巨大，pipeline 上面有大量 if-let-protocol 分支 |
| CEL 而非自定义 DSL | 复用 Google CEL 生态 | 需要 fork（cel-fork）才能满足 HTTP 集成需求 |
| Rust 数据面 + Go 控制面 | 各取所长 | 双语言 maintainer 池，proto 演进要双端同步 |
| 内嵌 Helm chart 做 deployer | 用户不用单独 install proxy | 升级 chart 需要重发布 controller |
| Delta ADS only | 增量同步省带宽 | 不支持 SotW 的工具（如某些 envoy 旧版本）无法对接 |
| OpenAI 兼容 API 做统一前门 | 客户端零改造 | 非 OpenAI provider 的特性（如 Gemini 多模态、Bedrock 私有模型）暴露要靠扩展字段 |

开放问题：
- A2A 模块目前是「URL 重写 + 透传」，没有协议级状态管理，未来 Google A2A 协议演进可能需要重写
- MCP federation 的 tool 命名空间策略硬编码用 `__` 分隔，需要可配置
- Guardrails chain 串行执行，没有 short-circuit / parallel 优化
