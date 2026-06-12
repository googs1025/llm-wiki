# OpenAI Codex CLI 架构与设计思路分析

> 仓库：https://github.com/openai/codex · 分析日期：2026-06-12 · 版本：HEAD `bf667c7`（2026-06-12，[codex] Load AGENTS.md from all bound environments (#27696)）· 获取方式：GitHub API 复核 HEAD + codeload tarball 源码扫描。

## 一句话定位

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
| `codex-rs/apply-patch`, `config`, `context-fragments` | 补丁、配置、AGENTS.md/context 装载。 |

## 关键数据流

1. 用户入口创建 session，config/context 层加载 AGENTS.md、环境、approval policy、sandbox mode 和模型配置。
2. core agent 与 OpenAI/ChatGPT auth 后端交互，输出 event stream；工具事件进入 shell/apply_patch/MCP 等执行器。
3. 执行前走 sandbox/approval 判断；MCP server 路径把 approval request 转成可交互 elicitation，再把用户响应回灌 session。
4. 最近 commit 说明 AGENTS.md 已从所有 bound environments 装载，Codex 的上下文边界不只当前 cwd。

## 设计决策与哲学

- Rust workspace 让 terminal agent、app server、MCP server 共用协议和执行安全逻辑。
- approval/sandbox 是一等配置，适合和 Claude Code、OpenCode 对比工具治理。
- MCP server 不是外置插件，而是官方入口之一，说明 Codex 正从 CLI 向可嵌入 agent substrate 扩展。
- 仓库很大但核心可以按 surface/core/tools/governance 四层理解。

## 与已有项目的对比

和 [[claude-code]] 相比，Codex 的开源仓库能直接观察 Rust core、审批和 sandbox 实现；和 Pi/oh-my-pi 相比，Codex 更官方、更收敛，工具面没 oh-my-pi 那么激进；和 Multica 相比，Codex 是执行 loop，不是 managed teammate 平台。

## 选型提示

- 适合深挖的问题：入口协议、状态源、工具/运行时边界、部署模型、失败恢复和安全治理。
- 不要只看 README：本页结论来自源码目录、入口文件、核心包和 GitHub 当前 HEAD 的组合扫描。
- 后续如继续深化，应补充 release/tag 变更、关键 issue/PR 和真实部署案例。
