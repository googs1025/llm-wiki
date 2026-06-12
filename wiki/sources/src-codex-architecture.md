---
title: OpenAI Codex CLI 架构与设计思路分析
tags: [architecture, coding-agent, rust, cli, openai]
date: 2026-06-12
sources: [codex-architecture-analysis.md]
related: [[[coding-agent-selection-map]], [[agent-skills-plugin-system-map]], [[claude-code]], [[mcp]], [[cloud-native-security]], [[agent-runtime-sandbox-selection-map]]]
---

# OpenAI Codex CLI 架构与设计思路分析

`openai/codex` 是 OpenAI 官方本地 coding agent。当前仓库主实现是 `codex-rs` Rust workspace，包含 CLI/TUI、app server/daemon、MCP server、core agent、config、context fragments、apply-patch、shell command safety、analytics、hooks、cloud tasks 等 crates；顶层 npm 包更多是安装/分发入口。

## 核心架构图

```text
┌──────────────────────────── user surface ────────────────────────────────────┐
│ `codex` CLI/TUI · `codex app` · IDE/app server · MCP server                   │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ codex-rs core/session/config/context                                          │
│ AGENTS.md · prompts · skills/plugins · model/provider client · event protocol │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ tool execution                │  │ governance                                  │
│ shell · apply_patch · MCP     │  │ approval policy · sandbox mode · telemetry  │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ local workspace / bound environments / optional cloud task integration         │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `codex-rs/cli`, `tui`, `app-server*` | 不同用户入口：terminal、desktop/app server、daemon/transport。 |
| `codex-rs/core`, `core-api`, `codex-client` | agent session、model API、event protocol 和核心 loop。 |
| `codex-rs/mcp-server` | 把 Codex 暴露成 MCP tool，包含 exec/patch approval request handling。 |
| `codex-rs/shell-command` | 命令安全分类：安全命令自动通过，危险 git/powershell/find 等触发审批。 |

## 关键数据流

1. 用户入口创建 session，config/context 层加载 AGENTS.md、环境、approval policy、sandbox mode 和模型配置。
2. core agent 与 OpenAI/ChatGPT auth 后端交互，输出 event stream；工具事件进入 shell/apply_patch/MCP 等执行器。
3. 执行前走 sandbox/approval 判断；MCP server 路径把 approval request 转成可交互 elicitation，再把用户响应回灌 session。

## 设计决策

- Rust workspace 让 terminal agent、app server、MCP server 共用协议和执行安全逻辑。
- approval/sandbox 是一等配置，适合和 Claude Code、OpenCode 对比工具治理。
- MCP server 不是外置插件，而是官方入口之一，说明 Codex 正从 CLI 向可嵌入 agent substrate 扩展。

## 对比定位

和 [[claude-code]] 相比，Codex 的开源仓库能直接观察 Rust core、审批和 sandbox 实现；和 Pi/oh-my-pi 相比，Codex 更官方、更收敛，工具面没 oh-my-pi 那么激进；和 Multica 相比，Codex 是执行 loop，不是 managed teammate 平台。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
