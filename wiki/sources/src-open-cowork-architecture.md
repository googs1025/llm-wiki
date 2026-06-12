---
title: Open Cowork 架构与设计思路分析
tags: [architecture, desktop-agent, electron, sandbox, mcp]
date: 2026-06-12
sources: [open-cowork-architecture-analysis.md]
related: [[[coding-agent-selection-map]], [[agent-runtime-sandbox-selection-map]], [[agent-skills-plugin-system-map]], [[mcp]], [[claude-code]], [[cloud-native-security]]]
---

# Open Cowork 架构与设计思路分析

`OpenCoworkAI/open-cowork` 是桌面端 agent host，而不是 terminal coding agent。它用 Electron main/preload/renderer 包装模型 API、Claude/Pi-compatible agent runner、SQLite/session、Skills、MCP、workspace 文件管理、WSL2/Lima 沙盒和远程控制，让非开发者通过 GUI 使用 AI 自动化文件、文档和桌面应用。

## 核心架构图

```text
┌──────────────────────────── Electron renderer ───────────────────────────────┐
│ chat UI · trace panel · settings · skills/MCP/sandbox status · session store  │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ preload IPC bridge
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ Electron main process                                                         │
│ agent-runner · tool-executor · session/db · skills manager · MCP manager      │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ workspace + SQLite memory     │  │ sandbox / desktop integration               │
│ files · sessions · traces      │  │ path guard · WSL2 · Lima · GUI automation   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ Claude/OpenAI-compatible models · MCP connectors · Feishu/Slack remote input  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `src/main/claude/agent-runner.ts` | agent 执行核心，测试覆盖 history rebuild 和 SDK session 恢复。 |
| `src/main/sandbox/**` | path guard 与 WSL/Lima sandbox 相关逻辑。 |
| `src/main/skills/**`, `.claude/skills` | 技能加载、安装、校验、启停。 |
| `src/main/memory/**`, `src/main/session/**`, `src/main/db/**` | SQLite/session/memory 管理。 |

## 关键数据流

1. 用户在 GUI 选择 workspace 并输入任务，renderer 通过 preload IPC 调用 main process。
2. agent-runner 组装模型、历史、技能、MCP 工具和 workspace 上下文，产生 trace/tool events。
3. 文件/命令工具先过 workspace path guard；若 WSL2/Lima 可用，bash 路由到 VM，否则回退本机受限执行。

## 设计决策

- 桌面 app 优先降低使用门槛，代价是 Electron/IPC/OS sandbox/installer 复杂度。
- 安全模型是多级：path guard 是基础，WSL2/Lima 是增强；README 也提醒仍需审查高风险操作。
- Skills 处理文档/PPT/XLS/PDF 这类桌面生产力任务，区别于 coding-agent 纯代码工作流。

## 对比定位

和 Multica 相比，Open Cowork 是单用户桌面入口；和 Codex/Pi 相比，它不是终端执行 loop，而是 GUI host；和 OpenShell/agent-sandbox 相比，它有 VM 级隔离但不是 K8s/runtime primitive。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
