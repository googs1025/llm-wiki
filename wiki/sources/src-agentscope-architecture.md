---
title: AgentScope 架构与设计思路分析
tags: [architecture, ai-agent, multi-agent, mcp, agent-service]
date: 2026-06-02
sources: [agentscope-architecture-analysis.md]
related: ["[[mcp]]", "[[agent-memory]]", "[[ai-agent-plugin-patterns]]", "[[agent-credential-isolation]]", "[[claude-code]]", "[[agent-sandbox]]", "[[nanobot]]"]
---

# AgentScope 架构与设计思路分析

> 原文：`raw/agentscope-architecture-analysis.md` · 仓库：[agentscope-ai/agentscope](https://github.com/agentscope-ai/agentscope) · 分析版本 main HEAD `e129177`（2026-06-01）

## 一句话定位

AgentScope 2.0 是一个面向生产化多 Agent 应用的 Python 框架：它把 Agent 推理循环、模型 provider、工具 / [[mcp]] / skill、workspace、权限、人类确认、长任务 offload 和 FastAPI 服务层拆成可组合的异步组件。它的核心不是固定编排 DSL，而是以 `Agent.reply_stream()` 为中心的事件流，把 ReAct 过程中的模型输出、tool call、tool result、确认请求和外部执行结果统一建模成可持久化的 `AgentEvent` / `Msg`。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ User / App surface                                                           │
│  Python SDK: Agent.reply()/reply_stream() · FastAPI app · scheduled triggers │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ Msg / AgentEvent stream
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Agent core (src/agentscope/agent)                                            │
│  AgentState · ContextConfig · ReActConfig · PermissionEngine                 │
│  reply loop: observe input → reason → act → persist context → repeat         │
└──────────────┬───────────────────────┬───────────────────────┬──────────────┘
               │                       │                       │
               ▼                       ▼                       ▼
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────┐
│ Model layer              │ │ Toolkit / tool layer      │ │ Middleware layer │
│ ChatModelBase            │ │ Toolkit, ToolBase         │ │ on_reply         │
│ provider adapters        │ │ builtin tools, MCP tools  │ │ on_reasoning     │
│ FormatterBase            │ │ skill viewer, tool groups │ │ on_acting        │
│ model cards YAML         │ │ permission checks         │ │ on_model_call    │
└──────────────┬───────────┘ └──────────────┬───────────┘ └────────┬─────────┘
               │                            │                      │
               ▼                            ▼                      ▼
┌──────────────────────────┐ ┌──────────────────────────┐ ┌──────────────────┐
│ LLM provider APIs        │ │ WorkspaceBase             │ │ App service      │
│ OpenAI / DashScope       │ │ Local / Docker / E2B      │ │ ChatService      │
│ Anthropic / Gemini       │ │ MCP clients, skills       │ │ SessionManager   │
│ Ollama / DeepSeek / xAI  │ │ offloaded context/results │ │ BackgroundTask   │
└──────────────────────────┘ └──────────────────────────┘ └──────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 公共 SDK / Agent 核心 | 管理 session state、上下文、ReAct 循环、事件流和最终消息聚合。 |
| 模型抽象与 provider | 把统一 `Msg` / content blocks 转成各 provider API 请求，把流式 / 非流式响应转回 `ChatResponse`。 |
| 工具、MCP、skill | 注册 Python tools、MCP tools、agent skills，生成 JSON schema，执行工具并归一成 `ToolChunk` / `ToolResponse`。 |
| 权限与确认 | 在工具执行前做 deny/ask/allow、模式检查、危险路径检查，并通过事件请求用户确认或外部执行。 |
| Workspace / offload | 为每个 session 提供本地 / Docker / E2B 执行环境，暴露 tools/MCP/skills，并持久化压缩上下文和超长工具结果。 |
| FastAPI app/service | 多租户、多 session 服务层；负责 agent 组装、SSE 事件输出、存储、调度、后台任务。 |
| 长任务与计划任务 | 把慢工具 offload 到后台，结果完成后重新注入上下文；用 APScheduler 驱动定时 agent run。 |

这个分层的关键约束是：`Agent` 只依赖抽象接口，不直接关心 provider SDK、Docker/E2B 细节、Redis 存储或 FastAPI 请求对象。服务层通过 `get_agent()` 每次从 storage/session/workspace 重新组装一个 Agent，Agent 内部再用统一事件流表达执行过程。

## 关键数据流

```
┌────────────┐
│ User Msg   │
└─────┬──────┘
      │ Agent.reply_stream(inputs)
      ▼
┌────────────────────────────────────────────────────────────────────┐
│ Agent._reply_impl                                                   │
│  1. validate incoming Msg / continuation event                      │
│  2. append input to AgentState.context                              │
│  3. emit ReplyStartEvent                                            │
│  4. loop until max_iters                                            │
└─────┬──────────────────────────────────────────────────────────────┘
      │
      ├── reasoning ------------------------------------------------┐
      │   ┌──────────────────────────────────────────────────────┐  │
      │   │ _prepare_model_input(): system prompt + summary      │  │
      │   │ + context + tool schemas                             │  │
      │   └───────────────┬──────────────────────────────────────┘  │
      │                   ▼                                         │
      │   ┌──────────────────────────────────────────────────────┐  │
      │   │ ChatModelBase / provider adapter                     │  │
      │   │ FormatterBase converts Msg blocks to provider format │  │
      │   └───────────────┬──────────────────────────────────────┘  │
      │                   ▼                                         │
      │   Text / thinking / data / tool-call deltas as events       │
      │                                                             │
      └── acting ---------------------------------------------------┘
          ┌──────────────────────────────────────────────────────┐
          │ _execute_tool_call                                   │
          │  check tool exists + validate JSON schema            │
          │  PermissionEngine: DENY / ASK / ALLOW / PASSTHROUGH  │
          └───────────────┬──────────────────────────────────────┘
                          │
       ┌──────────────────┴──────────────────┐
       ▼                                     ▼
┌───────────────┐                    ┌────────────────────┐
│ ask / external│                    │ Toolkit.call_tool  │
│ execution evt │                    │ ToolChunk stream   │
└───────┬───────┘                    └─────────┬──────────┘
        │                                      │
        ▼                                      ▼
 return waiting Msg                   ToolResult events
                                               │
                                               ▼
                                  save ToolResultBlock into context
                                               │
                                               ▼
                                  next reasoning iteration or final Msg
```

服务化路径是在这个本地流外面包一层持久化和 SSE：

```
HTTP POST /chat
     │
     ▼
FastAPI router
     │  encode AgentEvent as "data: <json>"
     ▼
ChatService.stream_chat
     │
     ├─ build ToolOffloadMiddleware
     ├─ get_agent(storage, workspace_manager, user, agent, session)
     │     ├─ load AgentRecord / SessionRecord / AgentState
     │     ├─ instantiate model and optional fallback model
     │     ├─ get per-session workspace
     │     └─ build Toolkit(tools + skills + MCPs)
     │
     ├─ SessionManager.run(session_id) serializes the run
     ├─ persist input Msg
     ├─ stream Agent.reply_stream() events
     ├─ reconstruct AssistantMsg by append_event()
     └─ persist reply Msg + updated AgentState
```

## 设计决策与哲学

- **事件流是核心协议，而不是“最终文本”**：模型调用、文本 / thinking / data / tool-call delta、tool result、reply end 都是事件；这让 SDK、SSE、存储和前端 UI 可以共享同一种流式语义，也适合做 [[agent-memory]] 或观测流水线。
- **ReAct 循环把“等待人类/外部系统”作为一等状态**：确认和外部执行通过 `RequireUserConfirmEvent` / `RequireExternalExecutionEvent` 暂停，再用 continuation event 恢复，比阻塞式输入更适合 Web 服务。
- **工具执行被拆成“验证/权限/上下文写入”和“原始 I/O”两层**：permission 语义在 `Agent` 内部，工具 I/O 通过 `Toolkit.call_tool()` 和 middleware 拦截；这和 [[agent-credential-isolation]]、[[ai-agent-plugin-patterns]] 里强调的边界治理一致。
- **Workspace 是工具资源和上下文外溢的边界**：Local / Docker / E2B workspace 给同一个 Agent 暴露 tools、[[mcp]]、skills 与 offload，和 [[agent-sandbox]] 的“执行环境原语”在问题域上相邻，但 AgentScope 更偏应用框架。
- **慢工具不取消，而是 offload 后再注入**：服务层把超时工具转为后台任务，先给模型 synthetic result，任务完成后再把结果作为 hint 注入下一次 reasoning，避免单个慢 I/O 卡死 SSE 回复。

## 核心组件

### Agent

`Agent` 构造时接收模型、toolkit、middlewares、state、context/react config 和 offloader。核心 `_reply_impl()` 先区分新输入和 continuation event，再进入 `cur_iter < max_iters` 的 ReAct loop：需要 reasoning 时准备 system prompt、summary、context、tool schemas 并调用模型；模型产出 tool calls 后按 sequential/concurrent batch 执行；如果触发用户确认或外部执行，就返回等待消息，让后续事件恢复同一个 reply。

### App Service

FastAPI chat router 只负责把 `ChatService.stream_chat()` 的 `AgentEvent` 编码成 SSE。`ChatService` 才是服务端运行入口：它构造 `ToolOffloadMiddleware`，调用 `get_agent()` 从 storage、session、credential、workspace 组装 Agent，在 `SessionManager.run(session_id)` 中串行运行同一 session，并把输入消息、reply 消息、更新后的 `AgentState` 写回 storage。

## 相关页面

- [[mcp]]
- [[agent-memory]]
- [[ai-agent-plugin-patterns]]
- [[agent-credential-isolation]]
- [[claude-code]]
- [[agent-sandbox]]
- [[nanobot]]
