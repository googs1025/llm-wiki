---
title: agentgateway
tags: [ai-gateway, llm, mcp, a2a, rust, kubernetes]
date: 2026-06-12
sources: [agentgateway-architecture-analysis.md]
related: [[mcp]], [[gateway-api]], [[xds]], [[hbone]], [[cel]], [[istio]], [[HiClaw]], [[agent-sandbox]]
---

# agentgateway

Solo.io / Istio 系出品的 **AI-native L7 网关**（Apache 2.0）。把三种 AI 流量统一在一个 Rust 数据面里：

- **LLM Gateway**：OpenAI / Anthropic / Gemini / Bedrock / Vertex / Azure / Copilot 七家 provider 统一为 OpenAI 兼容 API + guardrails
- **MCP Gateway**：stdio / HTTP Streamable / SSE 三种 transport + OpenAPI 自动转 MCP 工具 + 多 MCP server federation
- **A2A Gateway**：Google Agent-to-Agent 协议代理，通过重写 Agent Card 让所有调用走回 gateway

## 架构骨架

- **控制面**（Go）：[[gateway-api|Gateway API]] + 自家 CRD（`AgentgatewayPolicy` / `AgentgatewayBackend` / `AgentgatewayParameters`），KRT 反应式表，[[xds|xDS Delta ADS]] 分发
- **数据面**（Rust）：tokio + hyper + rustls，proxy/gateway → http/route → llm|mcp|a2a → upstream，[[cel|CEL]] 做策略 IR，[[hbone|HBONE]] 跟 [[istio|Istio]] mesh 互操作
- **UI**（TypeScript）：Next.js 管理界面

## 核心设计哲学

1. **沿用 Istio 基建做 AI Gateway**：Gateway API + KRT + xDS + HBONE 全套复用，只把数据面换成专为 AI 协议优化的 Rust 代理
2. **三协议共享同一条 pipeline**：Route / Policy / Backend / CEL 求值统一，差别只在 `Backend.kind` 决定走哪个 provider 适配器
3. **凭据托管**：LLM provider 真凭据放在 backend secret，Agent 只面对 gateway 自身认证，参见 [[agent-credential-isolation]]
4. **跟 [[agent-sandbox]] 互补**：前者出口流量治理，后者运行时隔离，并集 = AI 工作负载完整治理面

详见 [[src-agentgateway-architecture]]。

## LLM provider 适配器对照

| Provider | 请求侧职责 | 响应侧职责 | 典型差异 |
|----------|------------|------------|----------|
| OpenAI / OpenAI-compatible | 作为内部标准格式，基本透传 | 返回 OpenAI-compatible SSE / JSON | 其他 provider 多向它收敛 |
| Anthropic | OpenAI messages → Anthropic messages / tools | Anthropic event stream → OpenAI chunk | thinking/tool schema/stream event 名称不同 |
| Gemini / Vertex | OpenAI chat → generateContent / Vertex endpoint | Gemini candidates → OpenAI choices | project/location/auth 和多模态字段不同 |
| Bedrock | OpenAI chat → Bedrock invoke，叠加 AWS SigV4 | Bedrock body/stream → OpenAI-compatible | AWS auth、model id、区域化 endpoint |
| Azure OpenAI | OpenAI schema + Azure deployment endpoint | Azure OpenAI response → OpenAI-compatible | deployment 名称、api-version、endpoint path |
| Copilot | 适配 GitHub Copilot provider 入口 | 统一成 OpenAI-compatible | 认证和可用模型集合不同 |

agentgateway 的关键不是“支持更多 provider”本身，而是把 provider 差异压到 `AIProvider` / `Provider` trait 后面。上层 HTTPRoute、Policy、Backend、CEL、telemetry 不需要知道具体 provider 细节。

## MCP federation 与 CEL RBAC

MCP Gateway 把多个 MCP server 聚合到一个入口。设计重点是命名空间和授权：

- transport 层支持 stdio / HTTP Streamable / SSE，上游协议差异由 `mcp/upstream` 吸收；
- federation 时要避免工具名冲突，通常需要按 server 或 route 分命名空间；
- 权限不应散落在工具实现里，而应在 gateway route / policy 层用 [[cel]] 表达式做统一判定；
- agent 只拿 gateway 侧身份，后端 MCP server 的真实凭据仍由 gateway 管。

这和 [[HiClaw]] 的 worker consumer key 模式一致：Agent 能调用哪些工具，由网关侧 consumer、route 和 policy 决定，而不是由 prompt 里的自觉性决定。

## 和同类 AI Gateway 的边界

| 项目 | 主要定位 | agentgateway 的差异 |
|------|----------|---------------------|
| LiteLLM | Python LLM proxy / provider adapter | agentgateway 更偏 Rust 数据面 + Gateway API/xDS/mesh 集成 |
| OpenRouter | 托管模型路由服务 | agentgateway 是可自托管 infra 组件，控制面和策略在用户集群里 |
| Portkey | 托管/企业 LLM gateway | agentgateway 更云原生，强调 CRD、mesh、MCP/A2A |
| Envoy AI Gateway | Envoy Gateway 上的 GenAI gateway | agentgateway 不复用 Envoy 数据面，而是自写 Rust 数据面并同时覆盖 LLM/MCP/A2A |

## 部署 walkthrough 速记

1. 安装 Gateway API CRD 与 agentgateway 自家 CRD。
2. 部署 controller，它 watch `Gateway` / `HTTPRoute` / `AgentgatewayPolicy` / `AgentgatewayBackend`。
3. 创建 `GatewayClass` 与 `Gateway`，由 `AgentgatewayParameters` 控制 dataplane 部署参数。
4. 创建 `AgentgatewayBackend`，把 AI/MCP/A2A 后端和 secret 挂进去。
5. 用 `HTTPRoute.backendRef` 指向 backend，并用 `AgentgatewayPolicy` 加鉴权、限流、转换或 CEL RBAC。
6. dataplane 通过 xDS 增量接收配置，开始处理 LLM / MCP / A2A 流量。

如果需要运行时隔离，把 Agent 容器放在 [[agent-sandbox]] / [[agentcube]] 一类 substrate 上；如果需要 LLM serving endpoint picking，把入口和 [[gateway-api-inference-extension]] / [[llm-d]] 对齐。
