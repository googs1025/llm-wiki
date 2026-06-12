---
title: cc-connect
tags: [entity, coding-agent, chatops, im-bridge, go]
date: 2026-06-12
sources: [cc-connect-architecture-analysis.md]
related: [[claude-code]], [[codex]], [[agent-delegation]], [[coding-agent-observability]], [[open-cowork]]
---

# cc-connect

把本地 AI coding agent 连接到飞书、钉钉、Slack、Telegram、Discord、企业微信等消息平台的 Go bridge。详见 [[src-cc-connect-architecture]]。

## 架构边界

它是远程入口层：把聊天平台消息转给本地 agent session，再把 streaming event、usage、attachment 转回平台。它不是 trace viewer，也不是桌面 Agent OS。

## 选型判断

- 想用 IM 远程驱动本地 coding agent：cc-connect。
- 想观察 API 流量：[[claude-tap]]。
- 想桌面端聚合 agent/sandbox/skills：[[open-cowork]]。
- 想跨 agent delegation plugin：[[codex-plugin-cc]]。
