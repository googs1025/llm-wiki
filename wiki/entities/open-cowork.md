---
title: Open Cowork
tags: [entity, coding-agent, desktop-agent, sandbox, electron]
date: 2026-06-12
sources: [open-cowork-architecture-analysis.md]
related: [[agent-delegation]], [[coding-agent-observability]], [[cc-connect]], [[codex]], [[claude-code]]
---

# Open Cowork

Open Cowork 是 Electron desktop agent host，用 Claude/OpenAI-compatible chat、Skills、MCP、WSL2/Lima sandbox、GUI automation 和 Feishu/Slack remote control，把本地 coding agent 能力包装成桌面协作入口。详见 [[src-open-cowork-architecture]]。

## 架构边界

它是桌面端 agent host，不是 trace viewer、token analytics 或独立 LLM serving 平台。与 [[cc-connect]] 相比，Open Cowork 更偏本机桌面/sandbox/GUI 操作；cc-connect 更偏把已有本地 agent session 接到 IM。

## 选型判断

适合需要桌面端聚合 agent、skills、MCP 和 sandbox 的场景。不适合只做 telemetry，此时看 [[loongsuite-pilot]]；也不适合只做请求取证，此时看 [[claude-tap]]。
