---
title: Coding Agent / Personal Agent 选型地图
tags: [ai-agent, coding-agent, project-map, selection]
date: 2026-06-11
sources: [src-ai-agent-frameworks-stars, src-nanobot-architecture, src-nemoclaw-architecture, src-openshell-architecture]
related: [[claude-code]], [[nanobot]], [[mcp]], [[agent-memory-project-map]], [[agent-runtime-sandbox-project-map]], [[ai-agent-plugin-patterns]]
---

# Coding Agent / Personal Agent 选型地图

这页聚焦“用户直接使用的 Agent”：终端 coding agent、个人长跑 agent、Agent OS 和带 sandbox 的桌面/运行时封装。它和 [[agent-framework-programming-model-map]] 的区别是：这里先看**产品入口和日常开发体验**，不是先看框架 API。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 主语言 | 最近 push | GitHub 信号 | 一句话 |
|------|------|--------|-----------|-------------|--------|
| [[claude-code]] | https://github.com/anthropics/claude-code | Python | 2026-06-10 | 131k stars | 官方 terminal agentic coding tool |
| OpenCode | https://github.com/anomalyco/opencode | TypeScript | 2026-06-11 | 172k stars | 开源 coding agent 主线 |
| OpenClaude | https://github.com/Gitlawb/openclaude | TypeScript | 2026-06-11 | 28k stars | “runs anywhere, uses anything” 的 OpenClaude 路线 |
| [[src-nemoclaw-architecture|NemoClaw]] | https://github.com/NVIDIA/NemoClaw | TypeScript | 2026-06-11 | 21k stars | 在 OpenShell 内安全运行 Hermes / OpenClaw |
| [[nanobot]] | https://github.com/HKUDS/nanobot | Python | 2026-06-10 | 44k stars | 多渠道个人长跑 Agent |

这些仓库都还在活跃变化，旧版 source summary 只能作为架构底稿，选型时应以当前 README、release、examples 和目录结构为准。

## 选型结论

| 场景 | 首选 | 原因 | 避免条件 |
|------|------|------|----------|
| 终端内软件工程主力 | [[claude-code]] | 官方产品、hook/MCP/skills 生态完整，适合代码读写和 git workflow | 需要完全开源内核或自定义运行时 |
| 想要开源 coding agent 主线 | OpenCode | TypeScript 生态、活跃、适合研究 terminal coding agent 的开放实现 | 依赖商业 Claude Code 生态能力 |
| 多平台个人 Agent / Agent OS 实验 | OpenClaude / OpenClaw 系 | 强调不同环境、工具和宿主适配 | 需要稳定企业部署 SLA |
| 安全 sandbox 内运行 Agent | [[src-nemoclaw-architecture|NemoClaw]] + [[src-openshell-architecture|OpenShell]] | 明确处理 provider routing、policy、sandbox、credential 边界 | 只想要轻量本地 CLI |
| IM / 多渠道个人 assistant | [[nanobot]] | 17 channel、provider fallback、MCP、skills/memory 都在小内核里 | 主要需求是大型代码库自动修改 |

## 架构差异

| 维度 | [[claude-code]] | OpenCode | OpenClaude / OpenClaw 系 | [[src-nemoclaw-architecture|NemoClaw]] | [[nanobot]] |
|------|----------------|----------|---------------------------|----------------|-------------|
| 主入口 | CLI / IDE-like terminal | CLI | Agent runtime / product shell | `nemoclaw` / `nemohermes` CLI | CLI / IM / WebSocket / API |
| 扩展方式 | hooks / slash commands / skills / [[mcp]] | plugin / config / tools | runtime adapter / tools / memory | blueprint + onboard FSM + OpenShell adapter | pkgutil entry_points + skills markdown |
| 状态模型 | session transcript + CLAUDE.md + hooks | repo/session state | runtime/session state | host registry + OpenShell gateway state | 8 态 loop + checkpoint |
| 安全边界 | 依赖本地权限、hooks、MCP server 配置 | 依赖 agent 实现和 shell 权限 | 取决于 runtime | OpenShell supervisor / policy proxy / inference.local | 轻量本地进程，非强 sandbox |
| 记忆接入 | [[claude-mem]], [[memsearch]], [[agentmemory]] | [[memsearch]], [[agentmemory]] | [[tencentdb-agent-memory]], memsearch | memory provider + sandbox runtime | 内置 Markdown memory / dream |

关键判断：**Claude Code / OpenCode 是“coding loop 产品”，NemoClaw / OpenShell 是“安全运行底座”，nanobot 是“个人长跑 Agent 内核”**。它们不是互斥层，可以组合。

## 快速采用路径

- 个人开发效率：先用 [[claude-code]]，再加 [[claude-context]] 做代码语义检索、加 [[agent-memory-project-map]] 中的 memory 插件。
- 开源实现研究：用 OpenCode 对照 Claude Code 的工具循环、会话恢复、插件格式。
- 安全执行研究：从 [[src-openshell-architecture]] + [[src-nemoclaw-architecture]] 读起，看 gateway desired state、sandbox supervisor、provider credential routing。
- 多渠道 agent：用 [[nanobot]] 观察 channel/provider/skill 如何保持小内核。

## 后续核验清单

- OpenCode / OpenClaude 的插件和工具协议是否已稳定。
- Claude Code 官方 repo 是否只承载安装包/文档，核心实现是否可审计。
- NemoClaw 对 OpenShell / OpenClaw / Hermes 版本 pin 是否频繁变动。
- nanobot 的 channel/provider 插件 API 是否已承诺兼容。

