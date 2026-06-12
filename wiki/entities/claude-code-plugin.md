---
title: Claude Code 插件机制
tags: [entity, claude-code, plugin-system]
date: 2026-06-12
sources: [powermem-architecture-analysis.md]
related: [claude-code, powermem, claude-mem, mcp]
---

# Claude Code 插件机制

[[claude-code]] 的官方插件机制通过 `--plugin-dir`、marketplace install 或本地插件目录加载。一个插件通常由 `.claude-plugin/plugin.json`、`hooks/`、`skills/`、`.mcp.json`、scripts/config 等根级目录组成。**Hook + Skill + MCP server** 是最常见的三条扩展通道。

本页以 [[powermem]] 的 Claude Code 插件为参考实现；2026-06-12 重新核验 PowerMem 仓库时，最新 tag 为 `v1.1.3`，`apps/claude-code-plugin/` 仍包含 `.claude-plugin/`、`hooks/`、`skills/`、`config/`、`.mcp.json`。

## 插件结构

| 路径 | 作用 |
|------|------|
| `.claude-plugin/plugin.json` | 插件 manifest：name、description、version、author、repository 等 |
| `hooks/` | Claude Code lifecycle hook 的配置、wrapper 和二进制/脚本 |
| `skills/` | Slash command / skill 入口，每个目录提供一个能力 |
| `.mcp.json` | MCP server 配置，允许插件暴露或连接 MCP 工具 |
| `scripts/` / `config/` | 初始化、启动、停止、配置和诊断辅助 |

PowerMem 的 manifest 当前声明 `memory-powermem`，description 是给 Claude Code 增加 add/search/update/delete memory 能力，并指向 OceanBase / PowerMem 仓库。

## Hook 事件模型

Claude Code hook 不是只覆盖 4 个事件。当前常见事件族包括：

| 事件 | 插件用途 |
|------|----------|
| `SessionStart` | 初始化上下文、检查服务状态、准备本地环境 |
| `UserPromptSubmit` | 在用户 prompt 进入模型前检索记忆并注入 additional context |
| `PreToolUse` | 工具调用前做授权、审计或上下文记录 |
| `PostToolUse` | 工具调用后采集结果、记录文件/命令行为 |
| `Stop` | turn 结束后异步写记忆、flush 状态 |
| `PreCompact` / `PostCompact` | 上下文压缩前后保存/恢复重要信息 |

PowerMem 的关键路径是 `UserPromptSubmit` hook：自动搜索相关记忆，并把结果注入到 Claude Code 的上下文。它用 Go 原生二进制 `powermem-hook` 加 shell/PowerShell wrapper，避免要求用户的 Claude Code 进程直接依赖 Python 环境。

## Skill 格式

Skill 是 Markdown + scripts 的能力包。对 Claude Code 来说，skill 既是用户可见的 slash command，也是给模型看的工作流说明。PowerMem 当前提供：

- `init`：创建插件本地 venv，安装 `powermem` 后端和默认本地 embedding 依赖；
- `remember`：主动写入记忆；
- `recall`：主动检索记忆；
- `status`：检查 server / hook / config 状态；
- `stop`：停止本地服务；
- `reset`：清理本地状态。

这和 Codex skills 的哲学一致：`SKILL.md`/Markdown 是能力说明，脚本负责可执行动作，宿主 Agent 决定何时调用。

## `.mcp.json` 与双模式

- Go 原生二进制 `powermem-hook`（跨平台编译，无 Python 依赖）+ bash/PowerShell wrapper
- `UserPromptSubmit` hook 自动检索注入到对话上下文（`POWERMEM_PROMPT_SEARCH=0` 关闭）
- 默认 HTTP 模式 → `POST /api/v1/memories`；可选 MCP 模式 → 通过 [[mcp]] 工具
- marketplace 安装后需要 `/reload-plugins`，再运行 `/memory-powermem:init`

HTTP 模式适合本地 server 已经运行、hook 只需快速 REST 调用的场景；MCP 模式适合把 memory 能力作为工具暴露给 Agent，让 Agent 主动调用 add/search/update/delete。

## 与 [[claude-mem]] 的对照

| 维度 | PowerMem Claude Code 插件 | [[claude-mem]] |
|------|---------------------------|----------------|
| 定位 | PowerMem 后端的 Claude Code connector | 独立 Claude Code memory 插件 |
| 后端 | PowerMem server / SDK / OceanBase/SeekDB 等存储 | 自带 memory pipeline / worker / vector store |
| hook 重点 | UserPromptSubmit 检索注入 + skill 主动管理 | 跨会话采集、压缩、检索、注入 |
| 安装形态 | Claude Code plugin / marketplace / `--plugin-dir` | npm/本地插件式安装 |
| 适合场景 | 已决定用 PowerMem 作为统一 memory backend | 只想给 Claude Code 快速加长期记忆 |

## 选型判断

- 需要统一 memory backend、MCP/API/CLI/Dashboard 多入口：看 [[powermem]] 插件。
- 只关心 Claude Code 的跨会话记忆闭环：看 [[claude-mem]]。
- 需要把插件能力迁移到其他 Agent 宿主：关注 Skill + MCP + hook 三层是否解耦，避免把逻辑写死在某个生命周期事件里。

## 相关页面

- 平台：[[claude-code]]
- 参考实现：[[powermem]]、[[src-powermem-architecture]]
- 同类项目：[[claude-mem]]（独立 npm 包，与 powermem 插件功能重叠但定位不同 —— claude-mem 是独立 agent 记忆，powermem 插件只是接入层）
- 工具协议：[[mcp]]
