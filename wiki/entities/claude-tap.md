---
title: claude-tap
tags: [entity, coding-agent, observability, proxy, trace]
date: 2026-06-12
sources: [claude-tap-architecture-analysis.md]
related: [[coding-agent-observability]], [[claude-code]], [[codex]], [[tokscale]], [[cc-connect]]
---

# claude-tap

本地代理和 trace viewer，用 reverse proxy / forward proxy 截获 Claude Code、Codex CLI、Gemini CLI、Cursor CLI 等 coding agent 的真实 API 请求，落 SQLite trace 并提供 live viewer/export。详见 [[src-claude-tap-architecture]]。

## 架构边界

claude-tap 是观察与取证工具，不执行任务。它回答“Agent 到底把什么上下文和工具 schema 发给了模型”，而 [[tokscale]] 回答“用了多少 token/成本”，[[cc-connect]] 回答“如何从聊天平台远程驱动 agent”。

## 选型判断

适合 debug prompt、tool schema、streaming response、token usage 原始证据和 provider 兼容问题。不适合做任务调度、权限隔离或长期记忆。
