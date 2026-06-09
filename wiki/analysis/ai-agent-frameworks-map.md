---
title: AI Agent Frameworks 项目地图
tags: [ai-agent, agent-framework, project-map, llm-infra]
date: 2026-06-09
sources: [src-ai-agent-frameworks-stars, src-agentscope-architecture, src-nanobot-architecture, src-hiclaw-architecture, src-agentgateway-architecture, src-agent-sandbox-architecture, src-agentcube-architecture, src-claude-context-architecture]
related: [[claude-code]], [[mcp]], [[agent-memory]], [[agent-memory-project-map]], [[agent-runtime-sandbox-project-map]], [[ai-agent-plugin-patterns]], [[agent-sandbox]], [[agentcube]], [[agentgateway]], [[HiClaw]], [[nanobot]]
---

# AI Agent Frameworks 项目地图

这页把当前知识库里 AI Agent framework / coding agent / Agent OS / MCP / skills / memory / runtime 相关材料整理成一张工程地图。核心结论：Agent 生态已经明显分层，不再是“哪个框架能调工具”这么简单。

```
End-user agents / coding agents
        ↓
Agent framework / workflow runtime
        ↓
Tool protocol / gateway / SDK
        ↓
Skills / memory / context / observability
        ↓
Runtime / sandbox / cloud-native substrate
```

如果说 [[agent-memory-project-map]] 关注“Agent 如何记住”，[[agent-runtime-sandbox-project-map]] 关注“Agent 如何安全运行”，这页关注的是“Agent 工程生态如何分层组合”。

## 分层地图

| 层 | 代表项目 / 页面 | 解决的问题 |
|----|-----------------|------------|
| End-user agents / coding agents | [[claude-code]], OpenClaw, Hermes, OpenCode, OpenClaude, NemoClaw, [[nanobot]] | 用户直接使用的 Agent、terminal coding agent、个人 assistant |
| Agent framework / workflow runtime | [[src-agentscope-architecture|AgentScope]], LangGraph, LangChain, Dify, Eino, ADK, Dapr, YoMo | 构建 Agent 应用、workflow、状态图、多 Agent 协作 |
| Tool protocol / gateway / SDK | [[mcp]], FastMCP, GitHub MCP, Playwright MCP, [[agentgateway]], Claude Agent SDK | 工具/资源接入、协议统一、流量治理 |
| Skills / prompt pack | Anthropic Skills, agent-skills, code review skills, architecture diagram skills | 把能力做成 Markdown + scripts + workflow 的可迁移包 |
| Memory / context / observability / eval | [[agent-memory-project-map]], [[claude-context]], Langfuse, AgentOps, OpenJudge | 长期记忆、代码语义上下文、trace、cost、eval |
| Runtime / sandbox / cloud-native | [[agent-runtime-sandbox-project-map]], [[agent-sandbox]], [[agentcube]], OpenShell, [[src-skypilot-architecture|SkyPilot]] | 隔离、会话编排、K8s、多云算力 |

## 横向对比

| 维度 | End-user Agent | Framework / Workflow | MCP / Gateway | Skills | Memory / Context | Runtime / Sandbox |
|------|----------------|----------------------|---------------|--------|------------------|-------------------|
| 面向用户 | 终端用户 / 开发者 | 应用开发者 | 平台/工具开发者 | Agent 使用者和作者 | Agent / 平台 | 平台/运维 |
| 核心对象 | Agent session / task | Agent / graph / event loop | tool/resource/API route | skill directory / prompt pack | memory item / context chunk | sandbox / session / pod |
| 主要接口 | CLI / chat / IDE | Python/Go SDK / HTTP service | MCP / Gateway API / xDS | Markdown + scripts | search / recall / inject | CRD / CLI / SDK |
| 状态模型 | 会话历史和任务状态 | AgentState / workflow state | route/session/policy state | 文件系统 | DB/Markdown/vector index | K8s/Gateway/session store |
| 工程难点 | 体验、恢复、工具安全 | 可组合、并发、权限、人类确认 | 鉴权、RBAC、federation、observability | 可迁移性、边界、依赖 | 写入质量、检索、注入预算 | 隔离、凭据、网络、恢复 |

## 生态信号

来自 [[src-ai-agent-frameworks-stars]] 的 109 个项目可以归纳出几条趋势：

- **Claude Code 形成事实生态**：router、templates、skills、memory、trace viewer、token tracker、IM bridge、Codex plugin、code graph 都围绕 terminal coding agent 扩展。
- **OpenClaw / Hermes / OpenClaude / Claw 系信号强**：个人 Agent + 多平台入口 + sandbox + memory + messaging 正在产品化。
- **MCP 从协议变成基础设施层**：FastMCP、GitHub MCP、Playwright MCP、Kubernetes MCP、[[agentgateway]] / Plano 都在 tool/resource 接入面竞争。
- **Skills 成为可迁移能力包**：Agent 能力从硬编码插件迁移到 Markdown + scripts + workflow。
- **Memory/context/observability 正在产品化**：[[claude-mem]]、mem0、[[agentmemory]]、[[powermem]]、[[claude-context]]、Langfuse、AgentOps 分别占不同基础设施位置。
- **cloud-native runtime 进入 Agent 主线**：[[agent-sandbox]]、[[agentcube]]、OpenShell、Docker Agent、SkyPilot、KAgent、kubewizard 都说明 Agent 需要隔离、调度和可观测。

## 关键项目剖面

### [[src-agentscope-architecture|AgentScope]]：生产 Agent 应用框架

[[src-agentscope-architecture|AgentScope]] 的核心不是固定 DSL，而是事件流：

```
User Msg
        ↓
Agent.reply_stream()
        ↓
reasoning event / tool call event / confirm event / tool result event
        ↓
AgentState + storage + SSE
```

它把模型 provider、toolkit、MCP、skills、workspace、权限、人类确认、长任务 offload 和 FastAPI service 拆成可组合层。它适合做生产 Agent app，而不是底层安全 sandbox。

值得借鉴：

- `AgentEvent` / `Msg` 统一 SDK、SSE、存储和 UI。
- 人类确认和外部执行是 continuation event。
- 工具执行拆成 permission/context lifecycle 与 raw I/O。
- Workspace 承接 tools/MCP/skills/context offload。

### [[nanobot]]：小内核个人 Agent

[[nanobot]] 的价值是“小内核 + 可插拔层”：

- 17 个 channel 通过 pkgutil + entry_points 自动发现。
- 两条 `asyncio.Queue` 解耦 channel 和 agent。
- 8 态 `AgentLoop` 状态机处理 RESTORE/COMPACT/COMMAND/BUILD/RUN/SAVE/RESPOND。
- Provider 级 fallback 对 Agent 透明。
- Skills/Memory/Dream/Heartbeat 都是上下文层，而不是硬编码编排层。

它适合研究个人 Agent 如何保持可读、可改、可恢复。与 AgentScope 相比，nanobot 更轻、更端侧、更偏个人运行；AgentScope 更服务化、更面向生产多租户。

### [[HiClaw]]：Agent 平台化和声明式运维

[[HiClaw]] 代表“Agent 是 K8s 资源”的路线。它用 Worker/Team/Human/Manager CRD 表达多 Agent 系统，用 Matrix 作为协作平面，用 Higress 托管真实凭据。

它和 Python framework 的差异很大：

| 维度 | [[HiClaw]] | 普通 Agent framework |
|------|------------|----------------------|
| Agent 表达 | CRD | Python class / graph node |
| 部署单元 | 容器 / Pod | 进程内对象 |
| 协作面 | Matrix room | in-process bus / state graph |
| 人在回路 | 默认房间成员 | 需要自建 UI |
| 凭据 | 网关托管 | 常见是 Agent 持 key |
| 运维 | reconcile / RBAC / Helm | 应用自己补 |

它说明企业级 Agent 平台不会停留在 SDK 层，最终会进入 controller、网关、IM、对象存储和权限系统。

### [[agentgateway]]：Agent 流量基础设施

[[agentgateway]] 说明 Agent 生态需要独立的数据面。它统一 LLM API、MCP tools 和 A2A 通信，复用 Gateway API / xDS / CEL / HBONE 等云原生治理模式。

在 frameworks 地图里，它的位置是 tool/gateway layer：

- Agent framework 通过 MCP/HTTP 访问工具。
- Gateway 负责路由、认证、RBAC、federation、observability。
- 上游可以是 LLM provider、MCP server、OpenAPI endpoint 或 A2A agent。

这和 [[agent-runtime-sandbox-project-map]] 里的安全 runtime 形成互补：sandbox 控制 Agent 进程，gateway 控制 Agent 流量。

### [[agent-sandbox]] / [[agentcube]]：Agent 执行基座

framework 能构建 Agent，但安全运行需要 substrate：

- [[agent-sandbox]] 把单个有状态 Agent 容器建模成 Sandbox CRD。
- [[agentcube]] 把 Sandbox 包成 HTTP invocation session。

这两者说明 Agent framework 生态正在从“库”扩展到“运行时平台”。LangGraph/AgentScope/nanobot 这类框架可以把 sandbox/session layer 作为 backend，而不是自己处理 Pod、PVC、NetworkPolicy、WarmPool。

### Memory / context layer：独立产品层

[[agent-memory-project-map]] 已经显示：Agent memory 不是框架内部一个 list，而是完整管线。代码语义上下文也类似，[[claude-context]] / [[milvus]] / [[hybrid-search-rrf]] / [[code-semantic-search]] 组成独立层。

Agent framework 越轻，越需要外部 memory/context；Agent product 越重，越倾向把 memory/context 内置成用户体验的一部分。

## 设计轴

### 1. Library、runtime、product 是三种不同形态

Agent 生态常被混称为“框架”，但至少有三种形态：

- **Library/framework**：AgentScope、LangGraph、Eino。重点是编程模型。
- **Runtime/platform**：HiClaw、agent-sandbox、AgentCube、OpenShell。重点是运行、隔离、会话和运维。
- **Product/agent**：Claude Code、OpenClaw、Hermes、nanobot。重点是用户可直接完成任务。

三者可以组合，但不要混为一谈。一个库不应该承担全部 sandbox 安全；一个 sandbox 原语也不应该决定 Agent 的 reasoning loop。

### 2. MCP 是协议层，不是 Agent 框架

[[mcp]] 解决 tool/resource 接入，但它不定义：

- Agent 如何循环推理。
- 工具结果如何写入上下文。
- 人类确认如何暂停/恢复。
- 多 Agent 如何协作。
- sandbox 如何隔离。
- memory 如何写入和检索。

所以 MCP 更像 TCP/HTTP 之于 Web 应用：它是必要基础，但不是完整应用框架。

### 3. Skills 正在替代一部分插件代码

Skills 的关键价值是把能力封装成：

```
description
        ↓
instructions / workflow
        ↓
scripts / assets / templates
        ↓
LLM decides when to invoke
```

这比硬编码插件更容易迁移到 Claude Code、Codex、OpenCode、OpenClaw 等不同 Agent。缺点是权限、依赖、版本和测试要单独治理。

### 4. Observability 和 eval 会成为框架边界

Agent 框架如果只返回最终文本，就很难调试。生产 Agent 需要：

- event stream。
- tool call trace。
- token/cost。
- model/provider fallback。
- memory recall evidence。
- eval/benchmark。
- human approval logs。

[[src-agentscope-architecture|AgentScope]] 的事件流、[[nanobot]] 的 checkpoint、Langfuse/AgentOps/OpenJudge 这类项目说明观测和评测会从周边工具变成基础层。

### 5. Cloud-native runtime 会吞掉“本地 demo”边界

Agent 一旦进入生产，就会需要：

- sandbox。
- credential isolation。
- network policy。
- storage/session。
- queue/offload。
- autoscaling。
- GPU/resource scheduling。

这解释了为什么 [[agent-sandbox]]、[[agentcube]]、OpenShell、HiClaw、SkyPilot 都出现在 Agent frameworks 的生态列表里。它们不是偏题，而是 Agent 工程从 demo 到 production 的必经层。

## 核心难点

### 1. Agent loop 和工具权限必须解耦

模型是否要调用工具是一回事，工具是否允许执行是另一回事。[[src-agentscope-architecture|AgentScope]] 把 tool execution 拆成验证/权限/上下文写入与 raw I/O，[[agentgateway]] 用 CEL 做工具/流量 RBAC，[[src-openshell-architecture|OpenShell]] 在 sandbox proxy 做网络裁决。这个边界越清楚，系统越安全。

### 2. 人类确认要进入状态机

Agent 工作流经常需要审批、外部执行、人工介入。把它做成 blocking input 会破坏服务化。更稳的是 AgentScope continuation event、HiClaw Matrix room、OpenShell policy proposal 这种状态机/协作平面设计。

### 3. 多 Agent 协作不能只靠 in-process bus

Python 框架里的多 Agent 通常是进程内对象互调。企业场景需要身份、房间、审计、凭据隔离、文件共享和跨进程恢复。[[HiClaw]] 用 Matrix + MinIO + Higress + CRD 给出了平台化答案。

### 4. 跨 Agent 可迁移能力需要文件协议

Skills、memory Markdown、AGENTS.md、MCP server config 都说明：Agent 能力包更适合用文件/目录作为接口，而不是只靠 Python import。文件协议利于审计、迁移、版本控制和 LLM 读取。

### 5. 上下文层会越来越独立

Agent framework 内置短期 context 不够。代码语义检索、长期记忆、tool result offload、workspace artifacts 都会成为独立层。框架需要定义清楚 context provider 接口，而不是把所有上下文都塞进一个 prompt builder。

### 6. 产品入口和工程底座经常错位

用户看到的是 Claude Code/OpenClaw/nanobot；工程底座却是 MCP、skills、memory、sandbox、gateway、observability。项目地图的价值就是把这些层分开，避免拿“最终产品”和“底层原语”直接比较。

## 设计分型

| 分型 | 代表 | 架构重心 |
|------|------|----------|
| Terminal coding agent | [[claude-code]], OpenCode, OpenClaw | CLI/IDE 入口、tool use、workspace、hooks |
| Personal always-on agent | [[nanobot]], Hermes, OpenClaude | channels、long-running loop、memory、scheduler |
| Agent app framework | [[src-agentscope-architecture|AgentScope]], LangGraph, LangChain, Eino | event loop、workflow graph、toolkit、service |
| Agent platform / OS | [[HiClaw]], OpenShell/NemoClaw | runtime、identity、policy、collaboration |
| Tool protocol layer | [[mcp]], FastMCP, GitHub MCP, Playwright MCP | tool/resource 接入和 schema |
| Agent gateway layer | [[agentgateway]], Plano | LLM/MCP/A2A traffic、policy、telemetry |
| Capability package layer | Anthropic Skills, agent-skills | Markdown + scripts + reusable workflow |
| Memory/context layer | [[agent-memory-project-map]], [[claude-context]] | recall、semantic search、context control |
| Runtime substrate | [[agent-runtime-sandbox-project-map]] | sandbox、session、credential、network |

## 选型建议

| 目标 | 优先看 | 工程关注点 |
|------|--------|------------|
| 做生产多 Agent 应用框架 | [[src-agentscope-architecture|AgentScope]] | AgentEvent、tool permission、workspace/offload、FastAPI |
| 做轻量个人 Agent 内核 | [[nanobot]] | channel bus、8 态状态机、provider fallback、skills/context |
| 做企业多 Agent 平台 | [[HiClaw]] | CRD、Matrix、Higress、credential isolation |
| 做 tool/resource 协议层 | [[mcp]] / FastMCP | tool schema、transport、client identity |
| 做 Agent 流量网关 | [[agentgateway]] | Gateway API、CEL RBAC、LLM/MCP/A2A federation |
| 做 coding agent 生态扩展 | [[claude-code]] 周边 | hooks、skills、memory、trace、templates |
| 做运行时安全与会话编排 | [[agent-runtime-sandbox-project-map]] | sandbox、session、policy、provider credentials |
| 做长期记忆和上下文 | [[agent-memory-project-map]], [[claude-context]] | source-of-truth、hybrid search、context injection |

## 当前知识库缺口

- 还缺少 OpenClaw、OpenCode、Hermes、LangGraph、Dify、Eino、ADK、FastMCP、Anthropic Skills 的深入 source 页。
- 还缺少 MCP server 生态地图，可把 FastMCP/GitHub MCP/Playwright MCP/Kubernetes MCP/agentgateway 放在同一页。
- 还缺少 Skills 项目地图，专门比较 Anthropic Skills、Codex skills、agent-skills、code-review/architecture/finance skills。
- 还缺少 Agent observability/eval 地图，整理 Langfuse、AgentOps、OpenJudge、trace viewer、token tracker。

## 相关页面

- [[claude-code]]
- [[mcp]]
- [[agent-memory]]
- [[agent-memory-project-map]]
- [[agent-runtime-sandbox-project-map]]
- [[ai-agent-plugin-patterns]]
- [[agent-sandbox]]
- [[agentcube]]
- [[agentgateway]]
- [[HiClaw]]
- [[nanobot]]
