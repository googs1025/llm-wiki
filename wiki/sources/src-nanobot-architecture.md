---
title: nanobot 架构与设计思路分析
tags: [architecture, ai-agent, llm, python, chat-bot, mcp]
date: 2026-05-20
sources: [nanobot-architecture-analysis.md]
related: [[nanobot], [[claude-code]], [[mcp]], [[claude-agent-sdk]], [[ai-agent-plugin-patterns]]]
---

# nanobot 架构与设计思路分析

> 原文：`raw/nanobot-architecture-analysis.md` · 仓库：https://github.com/googs1025/nanobot （fork 自 HKUDS/nanobot） · 分析版本 v0.2.0

## 一句话定位

[[nanobot]] 是 HKUDS 的极简个人 AI Agent 框架（Python ≥3.11, MIT, v0.2.0），定位为「[[claude-code]] / Codex / OpenClaw 风格的轻量级长跑 Agent」。它通过一个事件驱动的 **8 态 Agent 状态机**，把 17 个聊天渠道、7+ 家 LLM 厂商、[[mcp]]、技能 / 记忆 / Cron / Heartbeat 编织成一个 ~16k 行的可读小内核——核心路径让开发者「能看懂、能改」，而周边能力（channel / provider / skill）通过 pkgutil 自动发现 + entry_points 插件机制接入，主代码不需要动。

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

| 层 / 模块 | 职责 |
|----------|------|
| CLI / SDK 入口 | Typer CLI（`onboard`/`agent`/`gateway`/...）+ 程序化外观 `Nanobot.from_config().run()` |
| 渠道层 | `BaseChannel` 抽象；`registry.discover_all` 用 pkgutil + entry_points 自动发现；`ChannelManager` 启动 / 路由 / 重试 / 流式合并 / 去重 |
| 消息总线 | 两条 `asyncio.Queue`；`InboundMessage` / `OutboundMessage` dataclass，channel 与 agent 解耦的唯一桥梁 |
| Agent 内核 | `AgentLoop` 8 态状态机；`AgentRunner` provider-agnostic tool-using 循环；checkpoint / mid-turn 注入 |
| 上下文构建 | `ContextBuilder` 拼 system prompt；`SkillsLoader` workspace + builtin 合并；`MemoryStore` + `Consolidator` + `Dream` 两阶段记忆 |
| 工具集 | `ToolRegistry` 注册 filesystem / shell / web / search / mcp / notebook / spawn / message / ...，按 OpenAI tool-call schema 暴露 |
| Provider 层 | `LLMProvider` ABC + 内置重试；`make_provider` 工厂；`FallbackProvider` 请求级 failover + 熔断；spec 注册表标记 OAuth/local/direct |
| 会话 | `Session` 持久化到 `~/.nanobot/sessions/<key>.json`；`goal_state` 支撑 `/goal` 长目标 |
| 命令路由 | 三档优先级：priority(/stop)、exact、prefix；14 个内置斜杠命令（`/new /model /history /goal /dream* /pairing /help /status /restart`） |
| 调度 & 主动唤起 | `CronService`（at/every/cron + ZoneInfo + FileLock）；`HeartbeatService` 周期 LLM 决定 skip/run |
| OpenAI 兼容 API | 把 nanobot 当成上游 LLM 暴露给外部工具，支持 SSE 流 |
| WebUI | WebUI 编译产物随 wheel 发布；WebSocket 渠道托管 + 静态文件 |

分层关键约束：
- **bus 是唯一的渠道↔Agent 通道**：channel 不 import agent，agent 不 import channel，两边都只看 `bus/events.py`。
- **provider 不感知 fallback**：`FallbackProvider` 本身实现 `LLMProvider`，对 Agent 透明；工厂方法 `_make_provider_core` 创建的 plain provider 不再包 fallback，防递归。
- **command router 优先于状态机**：`/stop` 类 priority 命令在 `AgentLoop.run()` 主循环里就被拦截，不进入 `_dispatch` 任务，从而能取消正在执行的任务。
- **per-session 串行 + 跨 session 并行**：每个 session_key 一把 `asyncio.Lock`；全局 `Semaphore(NANOBOT_MAX_CONCURRENT_REQUESTS, 默认 3)` 控制总并发。

## 关键数据流

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

## 设计决策与哲学

- **小内核 + 可插拔层（核心 DNA）**：bus 解耦 channel 与 agent，`channels/registry.py` 用 pkgutil + entry_points 自动发现 channel，`providers/factory.py` 走工厂 + Fallback 装饰——三处机制让新增 channel / provider 几乎不动主代码。这种风格和 [[claude-code]] 的 hook plugin 思路一脉相承。

- **事件驱动状态机替代单巨函数**：`TurnState` 8 个枚举 + `_TRANSITIONS` 跳转表把一次会话切成可单测的 handler，"`/stop` → checkpoint → 下次 RESTORE 续接"成为状态机自然的一环，不是散弹式 if-else。

- **Provider 级 Failover 而非 Agent 级**：`FallbackProvider` 实现 `LLMProvider` 接口对 Agent 透明；`has_streamed` 信号防止已吐字后跨模型拼接错乱；3 次失败 × 60s 冷却的熔断器；`_NON_FALLBACK_ERROR_KINDS={auth, permission, content_filter, refusal, context_length, invalid_request}` 区分"换模型救不了"的错误提前短路。

- **告别 litellm，回归原生 SDK（2026-03-21 commit）**：现在直接用 `openai` + `anthropic` 原生 SDK + 自家 `openai_compat_provider` 走 OpenAI 协议方言适配 DeepSeek / Kimi / Qwen / vLLM / Ollama / ... 以代码量换控制力，可以精细处理 `reasoning_content`、Anthropic `thinking_blocks`、各家结构化错误码、prompt cache header。

- **Mid-turn 注入而非"排队下一轮"**：每个活跃 session 持有 `asyncio.Queue(maxsize=20)`，用户在 Agent 工作时再发消息会塞进队列，由 runner 在工具调用之间插入到 messages 末尾。`_MAX_INJECTIONS_PER_TURN=3` 防失控；task 取消时残留消息重新 `publish_inbound` 回总线。

- **Outbound 合并 + 去重**：流式 `_stream_delta` 在 dispatcher 循环里贪心合并同 (channel, chat_id) 的连续片段，遇到边界塞回本地 buffer；普通消息用 SHA1 指纹 + `origin_message_id` 去重，防止 Hook 误重复发送。

- **DM 配对码代替"静默拒绝"**：未在 allowFrom 名单的 sender 私聊机器人会收到一次性配对码而不是被无视，根治了"我加好友怎么没反应"的体验问题。群聊则静默拒绝防被骚扰。

- **Skills / Memory / Dream / Heartbeat 是上下文层而非编排层**：`ContextBuilder` 把 identity / `AGENTS.md`+`SOUL.md`+`USER.md`+`TOOLS.md` / `MEMORY.md` / always skills / skills 列表 / Dream 处理后的历史 / 归档 summary 拼成 system prompt；`HEARTBEAT.md` 由 `HeartbeatService` 周期读取，再让 LLM 通过虚拟 `heartbeat` tool 决定 skip/run——"该不该跑后台任务"也交给模型。这种「能力即上下文」的设计与 [[ai-agent-plugin-patterns]] 中的「Markdown is the universal interface」一致。

- **Per-session 串行 + Cross-session 并行**：`_session_locks` 保证同一会话内消息按到达顺序处理；`Semaphore(3)` 限制全局总并发。多群 / 多人场景下既不会"一个会话死等另一个"也不会无限并发打爆 provider 配额。

## 关键组件深入解读

### AgentLoop 状态机（nanobot/agent/loop.py）

`AgentLoop` 是 ~1600 行的核心类，构造时一次性装配整个 agent 运行所需的所有协作者。`run()` 是无限循环：从 bus 拿 InboundMessage → priority 命令短路 → 检查 session 是否已有 task（有则路由到 pending_queue 做 mid-turn 注入）→ 否则 `asyncio.create_task(_dispatch(msg))`。`_dispatch` 在锁 + 信号量保护下进入状态机，状态机由 `_TRANSITIONS` 表驱动。

最有意思的细节是 **checkpoint**：runner 在每次工具执行后把当前轮 phase / iteration / assistant_message / completed_tool_results / pending_tool_calls 写进 `session.metadata["runtime_checkpoint"]`。一旦 task 被 `/stop` 取消，`_dispatch` 的 except 分支会调 `_restore_runtime_checkpoint` 把"半成品"物化回 session 历史；下次 inbound 时 `_state_restore` 读出来继续。这把「中断恢复」从异常处理变成了状态机一等公民。

## 相关页面

- [[nanobot]] — 项目实体页
- [[claude-code]] — 设计灵感来源（Anthropic CLI Agent）
- [[mcp]] — Model Context Protocol，nanobot 通过 `mcp>=1.26` 接入第三方工具
- [[claude-agent-sdk]] — 对照：另一种 Agent 编程 SDK 范式
- [[ai-agent-plugin-patterns]] — Agent 外挂的 9 条设计原则（pkgutil 自动发现、Markdown 即接口在此体现）