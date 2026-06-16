---
title: nanobot
tags: [ai-agent, llm, python, chat-bot, mcp, entity]
date: 2026-05-20
sources: [src-nanobot-architecture.md]
related: [[claude-code]], [[mcp]], [[claude-agent-sdk]], [[ai-agent-plugin-patterns]]
---

# nanobot

> HKUDS 出品的极简个人 AI Agent 框架。Claude Code / Codex / OpenClaw 风格的轻量级长跑 Agent。

## 核心数据

| 字段 | 值 |
|------|----|
| 项目主仓 | https://github.com/HKUDS/nanobot |
| 本次 ingest | https://github.com/googs1025/nanobot （fork） |
| 协议 | MIT |
| 版本 | v0.2.0（截至 2026-05-20） |
| 语言 / 运行时 | Python ≥3.11，单 asyncio event loop |
| 代码规模 | ~16k 行 Python，无 C 扩展 |
| 安装 | `pip install nanobot` → `nanobot onboard` |
| 程序化用法 | `from nanobot import Nanobot; Nanobot.from_config().run(msg)` |

## 它解决什么问题

把"个人聊天机器人 + 长跑 AI Agent"这件事压成一个**能看懂、能改**的小内核：

1. **接入多 IM 渠道很烦** → 17 个内置 channel（Telegram / Discord / Slack / Feishu / WeChat / QQ / Email / Matrix / DingTalk / WhatsApp / WeCom / MSTeams / WebSocket / CLI / ...），加新渠道写一个 module + entry_points 即可。
2. **多家 LLM SDK 差异大** → 7 个内置 backend（anthropic / azure_openai / bedrock / github_copilot / openai_codex / openai_compat / openai_responses），自家 `openai_compat_provider` 走 OpenAI 协议方言覆盖 DeepSeek / Kimi / Qwen / vLLM / Ollama / LongCat / MiMo / StepFun / ...
3. **LLM 失败要切模型** → `FallbackProvider` 在 provider 层做透明 failover，Agent 不感知；`has_streamed` 防拼接错乱 + 3×60s 熔断。
4. **用户中途想打断 / 改主意** → 状态机 + checkpoint：每次工具执行后写 `runtime_checkpoint`，`/stop` 取消后下次 inbound 用 `_state_restore` 续接；或不打断，用 mid-turn 注入直接塞进 messages 末尾。
5. **长期记忆 / 主动行为** → Skills / Memory / Dream / Heartbeat 全部以**上下文（Markdown 文件）**形式注入 system prompt，而非编排层；`HeartbeatService` 周期触发 LLM 自己决定 skip/run。
6. **MCP 工具生态** → 通过 `mcp>=1.26` 接 [[mcp]] server stdio，工具自动归入 `ToolRegistry` 暴露给 LLM。

## 核心架构（一句话版）

`Channels → MessageBus(2 × asyncio.Queue) → AgentLoop(8 态状态机) → Providers(可 fallback)`

详情见源摘要：[[src-nanobot-architecture]]。

## 关键技术决策

- **bus 解耦 channel ↔ agent**：channel 不 import agent，agent 不 import channel。
- **8 态状态机替代单巨函数**：`RESTORE → COMPACT → COMMAND → BUILD → RUN → SAVE → RESPOND → DONE`，每态一个可单测 handler，跳转走 `_TRANSITIONS` 显式表。
- **pkgutil + entry_points 自动发现**：built-in shadows external，新增 channel 不需要改主代码。
- **provider 级 failover**：`FallbackProvider` 实现 `LLMProvider`，Agent 透明感知不到；`has_streamed` 信号防止已吐字后跨模型拼接错乱。
- **per-session 串行 + 跨 session 并行**：`asyncio.Lock` × `Semaphore(3)`。
- **能力即上下文**：skills / memory / heartbeat / dream 都是注入 system prompt 的 Markdown 文件，而非编排层 — 体现 [[ai-agent-plugin-patterns]] 的「Markdown is the universal interface」。

## 重要依赖

| 依赖 | 用途 |
|------|------|
| `openai >= 2.8.0` | OpenAI 原生 SDK（取代 litellm） |
| `anthropic >= 0.45.0` | Anthropic 原生 SDK（含 `thinking_blocks`） |
| `mcp >= 1.26` | [[mcp]] 协议接入第三方工具 server |
| `typer` | CLI（`onboard` / `agent` / `gateway` / `login` / ...） |
| `pydantic v2` | 配置 schema |
| `filelock` | cron 任务跨进程持久化 |
| `croniter` + `zoneinfo` | cron 表达式解析 + 时区 |
| `oauth-cli-kit` | 交互式 OAuth 登录（GitHub Copilot / ...） |

## 内置 Skills

`clawhub · cron · github · image-generation · long-goal · memory · my · skill-creator · summarize · tmux · weather`

每个 skill 是 workspace 下一个 markdown 目录，包含 description + 操作 prompt + 可选工具，按需被 LLM 通过 skill 列表选择激活。

## 14 个内置斜杠命令

`/new /model /history /goal /dream /dream-status /dream-stop /pairing /help /status /restart /stop /memory /skills`

三档路由优先级：**priority**（`/stop` 类，主循环立即拦截）→ **exact** → **prefix**。

## 部署形态

- **CLI 单进程**：`nanobot agent` 启动事件循环，所有渠道在同一进程内并发。
- **OpenAI 兼容 API**：`nanobot.api.server` 把 nanobot 当成上游 LLM 暴露 SSE 流，供外部工具调用。
- **Gateway 模式**：多 agent 实例的反代（用 `nanobot gateway`）。
- **WebUI**：编译后的 SPA 随 wheel 发布，通过 WebSocket channel 服务。

## 与同类对比

| 维度 | nanobot | [[claude-code]] | autogen / langgraph |
|------|---------|------------|---------------------|
| 定位 | 个人长跑 IM Agent | CLI 内开发助手 | 编排框架 |
| 用户交互 | 多 IM 渠道 / WebUI | 终端 stdin/stdout | API / 自托管 UI |
| 状态机 | 显式 8 态 + checkpoint | Hook lifecycle | 图驱动 |
| Provider 解耦 | FallbackProvider 装饰 | 原生 Anthropic | 由用户实现 |
| 记忆 | Markdown 注入 system prompt | CLAUDE.md / auto-memory | 由用户实现 |
| 插件机制 | pkgutil + entry_points | Hook + slash command + MCP | 代码继承 |

## 设计灵感

README 明确说"inspired by Claude Code / Codex / OpenClaw"。最直接的影子：
- Skills + Memory + AGENTS.md / SOUL.md / USER.md / TOOLS.md 的工作区约定 ← [[claude-code]] 的 CLAUDE.md 系
- 斜杠命令系 ← [[claude-code]] 的 slash command
- MCP 集成 ← Claude Code 同期推进
- 8 态状态机 + checkpoint 续接 ← Codex 长跑 agent 的中断恢复需求

## 相关页面

- [[src-nanobot-architecture]] — 详细架构与设计哲学
- [[claude-code]] — 灵感来源（Anthropic CLI Agent）
- [[mcp]] — 工具协议
- [[claude-agent-sdk]] — 对照：编程式 Agent SDK 范式
- [[ai-agent-plugin-patterns]] — 9 条设计原则中"pkgutil 自动发现"和"Markdown 即接口"在此体现
