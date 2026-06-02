# AgentScope 架构与设计思路分析

> 仓库：https://github.com/agentscope-ai/agentscope · 分析日期：2026-06-02 · 版本：main HEAD `e129177`（2026-06-01，`fix(workspace): add locks to mcp and skill operations in LocalWorkspace. (#1710)`）

## 一句话定位

AgentScope 2.0 是一个面向生产化多 Agent 应用的 Python 框架：它把 Agent 推理循环、模型 provider、工具 / MCP / skill、workspace、权限、人类确认、长任务 offload 和 FastAPI 服务层拆成可组合的异步组件。它的核心不是固定编排 DSL，而是以 `Agent.reply_stream()` 为中心的事件流，把 ReAct 过程中的模型输出、tool call、tool result、确认请求和外部执行结果统一建模成可持久化的 `AgentEvent` / `Msg`。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 公共 SDK / Agent 核心 | `src/agentscope/agent/_agent.py`, `src/agentscope/state/_state.py`, `src/agentscope/event/_event.py`, `src/agentscope/message/_base.py` | 管理 session state、上下文、ReAct 循环、事件流和最终消息聚合。 |
| 模型抽象与 provider | `src/agentscope/model/_base.py`, `src/agentscope/model/_*/_model.py`, `src/agentscope/formatter/*` | 把统一 `Msg` / content blocks 转成各 provider API 请求，把流式 / 非流式响应转回 `ChatResponse`。 |
| 工具、MCP、skill | `src/agentscope/tool/*`, `src/agentscope/mcp/*`, `src/agentscope/skill/*` | 注册 Python tools、MCP tools、agent skills，生成 JSON schema，执行工具并归一成 `ToolChunk` / `ToolResponse`。 |
| 权限与确认 | `src/agentscope/permission/*`, `src/agentscope/tool/_builtin/*` | 在工具执行前做 deny/ask/allow、模式检查、危险路径检查，并通过事件请求用户确认或外部执行。 |
| Workspace / offload | `src/agentscope/workspace/*` | 为每个 session 提供本地 / Docker / E2B 执行环境，暴露 tools/MCP/skills，并持久化压缩上下文和超长工具结果。 |
| FastAPI app/service | `src/agentscope/app/_app.py`, `src/agentscope/app/_router/*`, `src/agentscope/app/_service/*`, `src/agentscope/app/storage/*` | 多租户、多 session 服务层；负责 agent 组装、SSE 事件输出、存储、调度、后台任务。 |
| 长任务与计划任务 | `src/agentscope/app/_middleware/_tool_offload_middleware.py`, `src/agentscope/app/_manager/_background_task_manager.py`, `src/agentscope/app/_manager/_scheduler/*` | 把慢工具 offload 到后台，结果完成后重新注入上下文；用 APScheduler 驱动定时 agent run。 |

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

超时和回退路径主要有三类：模型层 `ChatModelBase.__call__()` 只重试 provider 声明为 retryable 的异常；工具层先把 schema/permission 错误归一成 tool result，而不是直接崩掉 ReAct 循环；服务层的 `ToolOffloadMiddleware` 会把超过阈值的工具转成后台任务，并在完成后把结果以 `HintBlock` 重新注入下一次 reasoning。

## 设计决策与哲学

- **事件流是核心协议，而不是“最终文本”**：`Agent._reasoning_impl()` 在模型调用开始、文本 / thinking / data / tool-call delta、模型调用结束时都发事件，最后才把 `ChatResponse.content` 保存进上下文；这使 SDK、SSE、存储和前端 UI 可以共享同一种流式语义（`src/agentscope/agent/_agent.py:741-840`）。
- **ReAct 循环把“等待人类/外部系统”作为一等状态**：`_reply_impl()` 在收到 `RequireUserConfirmEvent` 或 `RequireExternalExecutionEvent` 后立即返回一个等待消息，并要求后续通过 `UserConfirmResultEvent` / `ExternalExecutionResultEvent` 继续同一个 reply（`src/agentscope/agent/_agent.py:542-685`）。这比把确认做成阻塞输入更适合 Web 服务和异步 UI。
- **工具执行被拆成“验证/权限/上下文写入”和“原始 I/O”两层**：`_execute_tool_call()` 负责 schema 校验、permission、事件和 context 写入；`_acting()` / `Toolkit.call_tool()` 只负责实际执行并产生 `ToolChunk` / `ToolResponse`（`src/agentscope/agent/_agent.py:1280-1588`, `src/agentscope/tool/_toolkit.py:240-388`）。这个边界让 middleware 可以安全地拦截 tool I/O，而不篡改 permission 语义。
- **Provider 适配走统一 `Msg` 和 formatter，而不是在 Agent 里写 if/else**：`ChatModelBase` 固定 credential/model/parameters/stream/retry/context_size，provider 子类只实现 `_call_api()`；formatter 再把 AgentScope 的 blocks 转成 OpenAI、Anthropic、DashScope 等格式（`src/agentscope/model/_base.py:35-180`）。
- **Workspace 是工具资源和上下文外溢的边界**：`WorkspaceBase` 明确给 Agent 暴露 `list_tools()`、`list_mcps()`、`list_skills()`、`offload_context()`、`offload_tool_result()`，并把 Local / Docker / E2B 作为后端实现（`src/agentscope/workspace/_base.py:1-190`）。这让“本地 agent SDK”和“服务端多租户 session”共用同一组资源接口。
- **服务层每轮重新组装 Agent，状态落在 storage/session**：`ChatService.stream_chat()` 先构造 middleware，再调用 `get_agent()` 从 AgentRecord、SessionRecord、Credential、Workspace 组装 Agent，运行后再持久化 reply 和 `AgentState`（`src/agentscope/app/_service/_chat.py:76-230`, `src/agentscope/app/_service/_agent.py:14-152`）。这避免把长期状态绑死在进程内 Agent 实例上。
- **慢工具不取消，而是 offload 后再注入**：`ToolOffloadMiddleware` 超时后不取消底层 task，而是注册到 `BackgroundTaskManager`，先返回 synthetic `ToolResponse`，完成后把结果放入 pending hints 并在 session idle 时 retrigger（`src/agentscope/app/_middleware/_tool_offload_middleware.py:21-406`）。

## 关键组件深入解读

### Agent（`src/agentscope/agent/_agent.py`）

`Agent` 构造函数接收 `ChatModelBase`、`Toolkit`、middleware、`AgentState`、context/react config 和 offloader。初始化时它从 `AgentState.permission_context` 创建 `PermissionEngine`，把 middleware 按 hook 是否实现预分类为 `_reply_middlewares`、`_reasoning_middlewares`、`_acting_middlewares`、`_model_call_middlewares` 等（`src/agentscope/agent/_agent.py:94-180`）。

核心入口 `reply_stream()` 只是消费 `_reply()` 并过滤最终 `Msg`，真正的状态机在 `_reply_impl()`：先判断输入是新消息还是 continuation event；新消息会写入 context 并生成新的 `reply_id`，continuation event 则恢复等待中的 tool call；随后进入 `cur_iter < max_iters` 的 loop。每轮如果需要 reasoning，先做 context compression，再调用模型；如果模型产出 tool calls，则按 sequential/concurrent batch 执行；如果执行中需要确认或外部执行，函数会返回等待消息而不是阻塞。

这种设计把“Agent 一次回复”拆成多个可恢复片段：第一次可能只跑到 `REQUIRE_USER_CONFIRM`，第二次用 `UserConfirmResultEvent` 恢复，第三次再拿到后台工具结果。它适合浏览器 UI、队列系统和定时任务，因为外部系统只需要持久化 `AgentState` 和最后一个 `AssistantMsg`。

### Toolkit / Tool（`src/agentscope/tool/*`）

`Toolkit` 是 AgentScope 的工具注册中心。构造时它把普通 tools、skills、MCP clients 归入默认 `"basic"` group，也允许额外 tool groups；内置 `ResetTools` 用于激活/重置 tool group，内置 `SkillViewer` 用于让模型读取 skill 指令（`src/agentscope/tool/_toolkit.py:66-169`）。

`get_tool_schemas()` 会根据当前激活 group 收集所有可用工具 schema，供模型 tool calling 使用。`call_tool()` 则承担执行层归一：先检查工具是否存在或 group 是否激活，再解析 JSON input；如果工具需要 state injection，就把 `_agent_state` 注入；之后兼容 coroutine、async generator、sync generator 三类返回，并把所有中间 `ToolChunk` 累积成最终 `ToolResponse`。普通异常会变成 error tool chunk，MCP 异常会单独标注，`asyncio.CancelledError` 会变成 interrupted result。

### App Service（`src/agentscope/app/*`）

`create_app()` 注册 agent、credential、session、chat、workspace、schedule、background_task、model 等 FastAPI routers，并在 lifespan 中打开 storage、workspace manager、session manager、background task manager 和 scheduler。HTTP chat router 本身只把 `ChatService.stream_chat()` 的事件编码成 SSE frame。

`ChatService` 是服务端运行 agent 的单一入口。它先创建 `ToolOffloadMiddleware`，再用 `get_agent()` 从 storage/session/workspace 组装 Agent：读取 agent config、session state、model credential、fallback model、workspace tools/skills/MCPs，最后构造 `Toolkit` 并把 workspace 作为 offloader 传给 Agent。运行时通过 `SessionManager.run(session_id)` 串行化同一 session 的执行，把输入消息、reply 消息和更新后的 `AgentState` 全部写回 storage。

## 性能 / 资源开销

仓库没有给出基准数据。代码层能看到的性能取舍主要是：模型调用默认流式返回，减少首 token 延迟；`ToolContext` 对 read file cache 做条目数和字节数限制；context compression 在 token 估算超过阈值后触发，并可把被压缩上下文和超长工具结果 offload 到 workspace；服务端长工具超时后转后台执行，避免单个慢 I/O 阻塞整个 SSE 回复。

## 安全模型

AgentScope 的安全边界集中在工具执行前：`PermissionEngine` 按 deny → ask → tool-specific checks → allow → bypass → default ask 的顺序决策，且工具自身还能实现 `check_permissions()`。workspace 后端决定真实执行环境：LocalWorkspace 直接操作本地目录；Docker/E2B workspace 把工具和 MCP 放到更隔离的环境中；服务层通过 user_id / agent_id / session_id 划分 storage 记录。需要注意的是，AgentScope 仍然是 agent framework，不是独立沙箱产品；如果把 Bash/Edit/Write 这类工具放进 LocalWorkspace，权限规则和运行目录隔离必须由调用方配置清楚。
