# nanobot 架构与设计思路分析

> 仓库：https://github.com/googs1025/nanobot （fork 自 HKUDS/nanobot） · 分析日期：2026-05-20 · 版本：v0.2.0

## 一句话定位

nanobot 是 HKUDS 的极简个人 AI Agent 框架（Python ≥3.11, MIT, v0.2.0），定位为「Claude Code / Codex / OpenClaw 风格的轻量级长跑 Agent」。它通过一个事件驱动的 8 态 Agent 状态机，把 17 个聊天渠道、7+ 家 LLM 厂商、MCP、技能 / 记忆 / Cron / Heartbeat 编织成一个 ~16k 行的可读小内核——核心路径让开发者「能看懂、能改」，而周边能力（channel/provider/skill）通过 pkgutil 自动发现 + entry_points 插件机制接入，主代码不需要动。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Chat Platforms (外部)                              │
│  Telegram · Discord · Slack · Feishu · WeChat · QQ · Email · Matrix ·         │
│  DingTalk · WhatsApp · WeCom · MSTeams · WebSocket(WebUI) · CLI · ...         │
└────────────┬───────────────────────────────────────────────────▲─────────────┘
             │ inbound                                            │ outbound
┌────────────▼────────────────────────────────────────────────────┴─────────────┐
│  Channels Layer  (nanobot/channels/)                                           │
│  ┌──────────────────────────┐   ┌─────────────────────────────────────────┐   │
│  │  registry.py             │   │  manager.py — ChannelManager            │   │
│  │  pkgutil.iter_modules    │──▶│   _init_channels(): discover_all()      │   │
│  │  + entry_points          │   │   start_all(): channel.start()×N        │   │
│  │  ⇒ built-in shadows ext. │   │   _dispatch_outbound(): coalesce+retry  │   │
│  └──────────────────────────┘   │     - _stream_delta 合并                │   │
│                                 │     - _reasoning_* 仅在 show_reasoning  │   │
│                                 │     - fingerprint 去重 _send_with_retry │   │
│  base.py — BaseChannel(ABC)     │     - 指数退避 1s/2s/4s                 │   │
│  start / stop / send /          └─────────────────────────────────────────┘   │
│  send_delta / send_reasoning_*    pairing.py: DM 未授权 → 配对码              │
└────────────┬───────────────────────────────────────────────────▲──────────────┘
             │ publish_inbound                                    │ publish_outbound
┌────────────▼────────────────────────────────────────────────────┴──────────────┐
│  Message Bus  (nanobot/bus/queue.py)                                           │
│      asyncio.Queue[InboundMessage]   asyncio.Queue[OutboundMessage]            │
└────────────┬───────────────────────────────────────────────────▲───────────────┘
             │ consume_inbound                                    │
┌────────────▼────────────────────────────────────────────────────┴───────────────┐
│  AgentLoop  (nanobot/agent/loop.py)  — 事件驱动状态机                            │
│                                                                                  │
│   run() ──▶ inbound → priority cmd? ─yes─▶ inline dispatch (/stop /restart)      │
│                       │                                                          │
│                       no                                                         │
│                       ▼                                                          │
│              session 有活动 task? ─yes─▶ pending_queue (mid-turn 注入)            │
│                       │                                                          │
│                       no                                                         │
│                       ▼                                                          │
│   _dispatch(msg) ── per-session asyncio.Lock + 全局 Semaphore(默认 3)            │
│        │                                                                         │
│        ▼  state machine (_TRANSITIONS table)                                     │
│   ┌──────────┐ ok ┌─────────┐ ok ┌─────────┐ shortcut ┌──────┐                   │
│   │ RESTORE  │───▶│ COMPACT │───▶│ COMMAND │─────────▶│ DONE │                   │
│   └──────────┘    └─────────┘    └─────────┘          └──────┘                   │
│                                       │ dispatch                                 │
│                                       ▼                                          │
│                                  ┌────────┐ ok ┌─────┐ ok ┌──────┐ ok ┌───────┐  │
│                                  │ BUILD  │───▶│ RUN │───▶│ SAVE │───▶│RESPOND│  │
│                                  └────────┘    └──┬──┘    └──────┘    └───┬───┘  │
│                                                   │ checkpoint            │      │
│                                                   ▼                       ▼      │
│                                            AgentRunner               OutMsg→Bus  │
│                                                                                  │
│   持有：ContextBuilder · ToolRegistry · AgentRunner · SubagentManager            │
│          SessionManager · Consolidator · AutoCompact · Dream · CommandRouter     │
│          mcp_stacks · _pending_queues · _active_tasks · _concurrency_gate        │
└────────────┬─────────────────────────────────────────────────────────────────────┘
             │ provider.chat / chat_stream
┌────────────▼───────────────────────────────────────────────────────────────────┐
│  Providers Layer  (nanobot/providers/)                                          │
│     factory.make_provider(config)                                               │
│       └─▶ _make_provider_core() — backend switch:                               │
│             anthropic | azure_openai | bedrock | github_copilot                 │
│             openai_codex | openai_compat (默认) | openai_responses              │
│       └─▶ FallbackProvider(primary, [fallbacks], factory)                       │
│             - 请求级 failover；circuit breaker (3 fail × 60s cooldown)          │
│             - has_streamed → 已吐字就放弃失败转移，避免重复输出                  │
│             - _NON_FALLBACK 错误（auth/quota/content_filter）直接返回            │
│   LLMProvider(ABC): chat / chat_stream / 内置重试政策 + 结构化错误码            │
└────────────────────────────────────────────────────────────────────────────────┘

支撑设施 (与 AgentLoop 平级)：
  cron/service.py       CronService    : at / every / cron(croniter+tz)，FileLock 持久化
  heartbeat/service.py  HeartbeatService: 2 phase——LLM 虚拟工具调用决定 skip/run
  api/server.py         OpenAI-Compatible API + SSE 流
  cli/commands.py       Typer CLI: nanobot onboard / agent / gateway / login ...
  nanobot.py            Programmatic facade: Nanobot.from_config().run(msg)
  agent/tools/          read_file/exec/grep/web_*/notebook/spawn/mcp/message/...
  skills/               clawhub · cron · github · image-generation · long-goal ·
                         memory · my · skill-creator · summarize · tmux · weather
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| CLI / SDK 入口 | `nanobot/__main__.py`, `nanobot/cli/commands.py`, `nanobot/nanobot.py` | Typer CLI（`onboard`/`agent`/`gateway`/...）+ 程序化外观 `Nanobot.from_config().run()` |
| 渠道层 | `nanobot/channels/{base,registry,manager,telegram,discord,slack,feishu,wechat,qq,websocket,...}.py` | `BaseChannel` 抽象；`registry.discover_all` 用 pkgutil + entry_points 自动发现；`ChannelManager` 启动 / 路由 / 重试 / 流式合并 / 去重 |
| 消息总线 | `nanobot/bus/queue.py`, `nanobot/bus/events.py` | 两条 `asyncio.Queue`；`InboundMessage` / `OutboundMessage` dataclass |
| Agent 内核 | `nanobot/agent/loop.py` (1613 lines), `nanobot/agent/runner.py` (1308) | `AgentLoop` 8 态状态机；`AgentRunner` provider-agnostic tool-using 循环；checkpoint / mid-turn 注入 |
| 上下文构建 | `nanobot/agent/context.py`, `nanobot/agent/skills.py`, `nanobot/agent/memory.py` (1162) | `ContextBuilder` 拼 system prompt；`SkillsLoader` workspace + builtin 合并；`MemoryStore` + `Consolidator` + `Dream` 两阶段记忆 |
| 工具集 | `nanobot/agent/tools/` (registry, filesystem, shell, web, search, mcp, notebook, spawn, message, ...) | 由 `ToolRegistry` 注册；按 OpenAI tool-call schema 暴露给 LLM |
| Provider 层 | `nanobot/providers/{base,factory,registry,fallback_provider,anthropic_provider,openai_compat_provider,bedrock_provider,...}.py` | `LLMProvider` ABC + 内置重试；`make_provider` 工厂；`FallbackProvider` 请求级 failover + 熔断；spec 注册表标记 OAuth/local/direct |
| 会话 | `nanobot/session/{manager,goal_state,webui_turns}.py` | `Session` 持久化到 `~/.nanobot/sessions/<key>.json`；`SessionManager` 跨进程；`goal_state` 支撑 `/goal` 长目标 |
| 命令路由 | `nanobot/command/{router,builtin}.py` | 三档优先级：priority(/stop)、exact、prefix；内置 `/new /model /history /goal /dream* /pairing /help /status /restart` |
| 调度 & 主动唤起 | `nanobot/cron/service.py`, `nanobot/heartbeat/service.py` | `CronService`（at/every/cron + ZoneInfo + FileLock）；`HeartbeatService` 周期 LLM 决定 skip/run |
| OpenAI 兼容 API | `nanobot/api/server.py` | 把 nanobot 当成上游 LLM 暴露给外部工具，支持 SSE 流 |
| WebUI | `nanobot/web/dist/` + `nanobot/channels/websocket.py` + `webui/` | WebUI 编译产物随 wheel 发布；WebSocket 渠道托管 + 静态文件 |
| 配置 / 工具基础 | `nanobot/config/`, `nanobot/utils/`, `nanobot/security/`, `nanobot/pairing/` | Pydantic v2 schema；网络白名单；DM 配对码授权 |

分层关键约束：
- **bus 是唯一的渠道↔Agent 通道**：channel 不 import agent，agent 不 import channel，两边都只看 `bus/events.py`。
- **provider 不感知 fallback**：`FallbackProvider` 本身实现 `LLMProvider`，对 Agent 透明；同时工厂方法 `_make_provider_core` 创建的 plain provider 不再包 fallback，防递归。
- **command router 优先于状态机**：`/stop` 类 priority 命令在 `AgentLoop.run()` 主循环里就被拦截，不进入 `_dispatch` 任务，从而能取消正在执行的任务。
- **per-session 串行 + 跨 session 并行**：每个 session_key 一把 `asyncio.Lock`；全局 `Semaphore(NANOBOT_MAX_CONCURRENT_REQUESTS, 默认 3)` 控制总并发。

## 关键数据流

**Telegram 用户消息从触发到回复的端到端路径**：

```
[Telegram 用户] ──msg──▶ TelegramChannel._handle_message()  (channels/base.py:199)
                            │   ├─ is_allowed() → allowFrom / 配对码兜底
                            │   └─ supports_streaming → meta["_wants_stream"]=True
                            ▼
                       bus.publish_inbound(InboundMessage)        (bus/queue.py)
                            ▼
                       AgentLoop.run() consume_inbound            (loop.py:789)
                            ├─ priority cmd? → 直接派发 (/stop /restart /status)
                            ├─ session 有 pending? → put 到该 session 的注入队列
                            └─ asyncio.create_task(_dispatch(msg))
                            ▼
                       _dispatch():  Lock(session) ∩ Semaphore(3)  (loop.py:864)
                            │   注册 pending_queue → 接收 mid-turn 注入
                            ▼
                       状态机：RESTORE → COMPACT → COMMAND → BUILD → RUN → SAVE → RESPOND
                            │
                            ▼ RUN 阶段
                       AgentRunner.run(spec)            (agent/runner.py:112)
                            │
                  ┌─────────┴─────────┐
                  │   for iteration:   │
                  │     provider.chat / chat_stream → LLMResponse
                  │     ├─ FallbackProvider 在此 transparently failover
                  │     ├─ has_tool_calls? → 并行 / 串行执行工具
                  │     │     - 工具结果回填到 messages
                  │     │     - 每次执行后 _emit_checkpoint (持久化到 session.metadata)
                  │     │     - on_progress / on_stream → bus.publish_outbound
                  │     ├─ _try_drain_injections → 把 pending_queue 里的用户新消息
                  │     │     插入到当前对话末尾（保持 role 交替）
                  │     └─ finish_reason == "stop" → break
                  └─────────┬─────────┘
                            ▼
                       SAVE: session.add_message / sessions.save / consolidator
                       RESPOND: assemble OutboundMessage → bus.publish_outbound
                            ▼
                       ChannelManager._dispatch_outbound()       (channels/manager.py:275)
                            ├─ _coalesce_stream_deltas: 合并连续 _stream_delta
                            ├─ _should_suppress_outbound: SHA1 指纹去重
                            ├─ _reasoning_delta/_end → 仅在 channel.show_reasoning=True
                            └─ _send_with_retry: 1s/2s/4s 指数退避
                            ▼
                       TelegramChannel.send / send_delta / send_reasoning_delta
                            ▼
                       [Telegram 用户]
```

**中断与恢复路径**：

```
用户发送 /stop ──▶ AgentLoop.run() 检到 priority cmd
                    └─▶ commands.dispatch_priority(cmd_stop)
                          └─▶ 取消该 session 的 active_tasks
                                  │
                                  ▼
                          _dispatch() 收到 CancelledError
                                  │
                                  ├─ session = sessions.get_or_create(key)
                                  ├─ _restore_runtime_checkpoint(session)
                                  │   ↑ runtime_checkpoint 在每次工具执行后 _emit_checkpoint 时
                                  │     已经写进了 session.metadata，包含：
                                  │     · phase (final_response / tool_pending)
                                  │     · iteration
                                  │     · assistant_message（已生成的部分回复）
                                  │     · completed_tool_results
                                  │     · pending_tool_calls
                                  ├─ _clear_pending_user_turn(session)
                                  └─ sessions.save(session)
                                  ▼
                          finally: 把 pending_queue 里残留的 InboundMessage
                                   重新 publish_inbound 回总线（不丢消息）

下一次 inbound 时 ──▶ _state_restore (loop.py:1220) 读 runtime_checkpoint
                        + pending_user_turn，把上次中断的上下文物化进 history，
                        新消息接着这段历史继续推理。
```

补充：
- **超时**：`runner_wall_llm_timeout_s(sessions, session_key)` 按 session 计算 LLM 调用墙钟超时；provider 自身有 `_CHAT_RETRY_DELAYS=(1,2,4)` + `_PERSISTENT_MAX_DELAY=60` + `_PERSISTENT_IDENTICAL_ERROR_LIMIT=10`。
- **错误传递**：`LLMResponse.finish_reason="error"` 携带 `error_status_code` / `error_kind` / `error_type` / `error_code` / `error_retry_after_s` / `error_should_retry` 结构化字段，`FallbackProvider._should_fallback` 据此区分"可换模型"vs"换了也没用"（auth/quota/content_filter/context_length/invalid_request → 直接返回错误，不进 fallback）。
- **回退路径**：若所有 fallback 全失败，返回最后一次的错误 `LLMResponse`；若主模型熔断又无 fallback，合成 `"Primary model X circuit open and no fallbacks available"` 错误响应。

## 设计决策与哲学

- **「小内核 + 可插拔层」是项目核心 DNA**：README 反复强调 "small, readable core"，代码层面用三层解耦贯彻：(1) `bus/queue.py:8-44` 只有两条 `asyncio.Queue`，channel 与 agent 通过事件对象通信，零耦合；(2) `channels/registry.py:17-71` 用 `pkgutil.iter_modules` + `importlib.metadata.entry_points` 自动发现 channel——built-in 优先，外部插件不需改主代码；(3) `providers/factory.py:31-104` 走工厂 + 抽象基类 + Fallback 装饰，新增厂商只需写一个 module 并在 `providers/registry.py` 加进 spec 表。

- **事件驱动状态机替代单巨函数 `loop.py:63-72,149-158`**：`TurnState` 枚举把一次会话切成 8 个可单测的 handler（`_state_restore` ~ `_state_respond`）；`_TRANSITIONS: dict[(state, event), state]` 是一张显式跳转表，handler 返回事件字符串，调度器查表。这种结构让"`/stop` → checkpoint 保存 → 下次 RESTORE 续接"成为状态机自然的一环，而不是散弹式 if-else。代价是事件字符串（`"ok"`/`"dispatch"`/`"shortcut"`）是无类型约束的 magic string。

- **Provider 级 Failover 而非 Agent 级 `fallback_provider.py:58-249`**：`FallbackProvider` 本身实现 `LLMProvider` 接口，Agent 完全感知不到。关键巧思：用 `has_streamed[0]` 跟踪 stream 是否已吐字——一旦吐了第一个 token，主模型再失败也不再 failover（避免前后内容拼接错乱）。同时维护 3 次连续失败的熔断器（`_PRIMARY_FAILURE_THRESHOLD=3`, `_PRIMARY_COOLDOWN_S=60`），熔断后直接跳过主模型省一次往返；半开探测留给下一次请求。`_NON_FALLBACK_ERROR_KINDS={auth, permission, content_filter, refusal, context_length, invalid_request}` 区分"换模型救不了"的错误，提前短路。

- **告别 litellm，回归原生 SDK（2026-03-21 commit `3dfdab7`）**：原本依赖 litellm 做多家 LLM 统一，现在改为直接用 `openai>=2.8.0` + `anthropic>=0.45.0` 原生 SDK + 自家 `openai_compat_provider` 走 OpenAI 协议方言（DeepSeek/Kimi/Qwen/MiniMax/Ollama/vLLM/LongCat/MiMo/StepFun/...）。`providers/registry.py` 维护一张 spec 表标记 `is_oauth / is_local / is_direct`，工厂据此豁免 `api_key` 校验。这套手写适配以代码量换控制力——可以精细处理每家的 `reasoning_content`、Anthropic `thinking_blocks`、各种结构化错误码、prompt cache header。

- **Mid-turn 注入而非"排队等下一轮" `loop.py:822-852, runner.py:157-199`**：每个活跃 session 持有一个 `asyncio.Queue(maxsize=20)`。用户在 Agent 还在工作时再发消息，不会启动新 task 抢锁，而是塞进这个队列，由 runner 在工具调用之间 `_try_drain_injections` 取出来插入到 messages 末尾（同 role 自动合并）。`_MAX_INJECTIONS_PER_TURN=3` 和 `_MAX_INJECTION_CYCLES=5` 防止失控。task 取消时 finally 块把残留消息重新 `publish_inbound` 回总线，避免丢失。

- **Outbound 合并 + 去重 `channels/manager.py:275-454`**：流式输出经常 1 token 1 个 `_stream_delta`，全部直送 Telegram 会触发限速。`_coalesce_stream_deltas` 在 dispatcher 循环里贪心合并同 (channel, chat_id) 的连续 delta，遇到边界把多余的塞回本地 `pending` buffer（asyncio.Queue 不支持 push_front）。普通消息用 SHA1 内容指纹 + `origin_message_id` 在 `_origin_reply_fingerprints` 里去重，防止 Hook 误重复发送。

- **DM 配对码代替"静默拒绝" `channels/base.py:184-247, pairing.py`**：未在 allowFrom 名单的 sender 私聊机器人，会收到一个一次性配对码而不是被无视；用户把码贴到信任设备上即可加入白名单。这是 IM 机器人常见的"我把它加好友怎么没反应"问题的根治方案。

- **Skills / Memory / Dream / Heartbeat 是上下文层而非编排层 `agent/context.py:37-76`**：`ContextBuilder.build_system_prompt` 把 identity / 工作区根的 `AGENTS.md`+`SOUL.md`+`USER.md`+`TOOLS.md` / `MEMORY.md` / 总是激活的 skills / skills 列表 / 最近 Dream 处理过后的 unprocessed history / 归档 summary 拼成一个 system message。`HEARTBEAT.md` 由 `HeartbeatService` 周期性读出，再让 LLM 通过一个虚拟 `heartbeat` tool 决定 skip/run——把"该不该跑后台任务"这种判断也交给模型而非硬编码规则。

- **Per-session 串行 + Cross-session 并行**：`_session_locks` 保证同一会话内消息按到达顺序处理；`_concurrency_gate=asyncio.Semaphore(3)` 限制全局总并发；`NANOBOT_MAX_CONCURRENT_REQUESTS=0` 可关掉总并发限制。这套设计在多群 / 多人场景下既不会"一个会话死等另一个会话的 LLM 调用"也不会无限并发打爆 provider 配额。

## 关键组件深入解读

### AgentLoop 状态机（nanobot/agent/loop.py）

`AgentLoop` 是 ~1600 行的核心类，构造时一次性装配整个 agent 运行所需的所有协作者：`bus / provider / workspace / tools / runner / subagents / sessions / context / consolidator / auto_compact / dream / commands / mcp_stacks`。`__init__` 还做了三件关键的事：(1) 注册默认工具集 `_register_default_tools()`；(2) `register_builtin_commands(self.commands)` 装好 14 个内置斜杠命令；(3) 初始化每会话锁 `_session_locks` 和全局信号量 `_concurrency_gate`。

`run()` 是一个无限循环：从 bus 拿一条 InboundMessage，先走 priority 命令短路（`/stop` 等无锁立即派发），再检查这个 session 是不是已经有 task 在跑——如果是就路由到该 session 的 `pending_queue` 做 mid-turn 注入；否则 `asyncio.create_task(_dispatch(msg))` 创建任务。`_dispatch` 在锁 + 信号量保护下进入状态机，状态机由一张 `_TRANSITIONS` 表驱动，每个 `_state_*` handler 返回事件字符串决定下一态。`_state_run` 是真正调用 LLM 的地方，它把上下文交给 `AgentRunner`，runner 内部循环 LLM → 工具，最后把结果回到 `_state_save`/`_state_respond`。

最有意思的细节是 **checkpoint**：runner 在每次工具执行后 `_emit_checkpoint` 把当前轮的 phase / iteration / assistant_message / completed_tool_results / pending_tool_calls 写进 `session.metadata["runtime_checkpoint"]`。一旦 task 被 `/stop` 取消，`_dispatch` 的 except 分支会调 `_restore_runtime_checkpoint` 把这份"半成品"物化回 session 历史；下次 inbound 时 `_state_restore` 读出来继续。这是把"中断恢复"从异常处理变成了状态机一等公民。

### FallbackProvider（nanobot/providers/fallback_provider.py）

273 行的 `FallbackProvider` 是一个标准的装饰器模式：实现 `LLMProvider` 接口，内部持有一个 primary + 若干 fallback preset + 一个 `provider_factory` 回调。`chat_stream` 关键路径用 `has_streamed: list[bool] = [False]` 通过包装 `on_content_delta` 回调追踪是否已经向用户吐字——这是判断能否安全 failover 的核心信号。

`_should_fallback` 是一个细致的多维分类器：先看 `response.error_should_retry` 显式信号，再看 HTTP 状态码（400/401/403/404/422 → 不 fallback；408/409/429 + 5xx → fallback），再看 `error_kind` / `error_type` / `error_code` 是否在 fallback 集合或 non-fallback 集合，最后落到错误文本 token 匹配作为兜底。`_FALLBACK_ERROR_TOKENS` 涵盖了配额耗尽、余额不足、限速、超时、连接错等所有"换个 provider 就能救"的场景。

熔断器逻辑简洁：`_primary_failures` 计数，达到 3 次后置 `_primary_tripped_at`，60s 内 `_primary_available()` 返回 False 跳过主模型直接走 fallback；60s 后自动进入半开态，下一次请求允许探测主模型，成功则计数归零。

## 性能 / 资源开销

- **进程冷启动**：单个 asyncio event loop，无 worker 池；启动开销主要来自 `_connect_mcp()`（并行启动所有 MCP server stdio 连接）和各 channel 的 `start()`（建立 WebSocket / 登录回话），秒级。
- **稳态**：单核处理一个 session 串行；全局 `Semaphore(3)` 是 LLM 调用并发上限；`MessageBus` 的两条 queue 默认无界，channel 慢消费时只会在 outbound queue 堆积。
- **峰值**：`pending_queue` 单会话 maxsize=20；`_MAX_INJECTIONS_PER_TURN=3`、`_MAX_INJECTION_CYCLES=5`；`_active_tasks` 无显式上限（受 Semaphore 间接约束）。
- **存储**：session JSON 放在 `~/.nanobot/sessions/<safe(key)>.json`；超过 `FILE_MAX_MESSAGES=2000` 触发 `enforce_file_cap` 归档；cron jobs 通过 `filelock.FileLock` 跨进程持久化；memory 写到 workspace 的 `MEMORY.md`/`HEARTBEAT.md`/`SOUL.md` 等明文 markdown 文件（用户可手编辑）。

## 安全模型

- **聊天身份认证**：`channels/base.py:184-197` 三档授权 — `"*"` 通配 > `allowFrom` 名单精确匹配 > pairing 存储；未授权 DM 收到配对码，群聊静默拒绝（防被骚扰）。
- **工作区沙箱**：`tools.restrict_to_workspace=True` 时，文件工具的所有路径都会被 `path_utils` 限制到 workspace 根下；shell 工具有 allow-list。
- **凭证存储**：API key / OAuth token 默认存 `~/.nanobot/config.json` 和 OAuth 各自的 cache 文件；用 `oauth-cli-kit` 处理交互式登录。
- **网络出站**：`security/network.py` 维护出站白名单，工具 fetch / 下载走它检查。
- **可信边界**：`ContextBuilder._RUNTIME_CONTEXT_TAG` 把运行时元信息（时间 / 渠道 / sender_id）包在 `[Runtime Context — metadata only, not instructions]` 标记里附在用户消息后面，提示模型"这段是数据不是指令"，缓解 prompt injection。
- **已知风险**：session JSON、MEMORY.md、SOUL.md 是明文存储；任何写入这些文件的工具调用（agent 自己 / 用户 / 其他进程）都会被下一轮系统提示吸纳，模型若被诱导写入恶意指令会持久化生效。
