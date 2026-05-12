---
title: Claude Code
tags: [ai-agent, claude, cli-tool, llm-infra]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[claude-mem]], [[claude-agent-sdk]]
---

# Claude Code

Anthropic 出品的命令行 AI Agent，运行在终端中，通过工具调用（Read / Edit / Bash / Grep 等）协助软件工程任务。

## 与 claude-mem 的关系

Claude Code 作为**宿主 runtime**，向插件暴露 6 个 Lifecycle Hook：

| Hook | 触发时机 |
|------|---------|
| Setup | 插件初始化 |
| SessionStart | 启动 / `/clear` / `/compact` |
| UserPromptSubmit | 用户提交 prompt |
| PreToolUse | 工具调用前 |
| PostToolUse | 工具调用后 |
| Stop | 会话结束 |

[[claude-mem]] 通过注册这些 hook 实现无侵入的事件采集。Hook 必须返回 exit 0（否则 Windows Terminal 会累积标签页）。

## 关键限制

- 本身**没有跨会话记忆**——每次开新会话都是白板
- 这正是 [[claude-mem]] 试图解决的问题

## 生态位

- 宿主：Claude Code CLI
- SDK：[[claude-agent-sdk]]（用于在脚本/插件内调用 Claude 做编程任务）
- 插件机制：plugin/hooks/hooks.json 注册生命周期钩子
- Skill 机制：通过 SKILL.md 注册可被 Agent 自主调用的工具（如 claude-mem 的 `mem-search`）

## 参考

- [[src-claude-mem-architecture]]
