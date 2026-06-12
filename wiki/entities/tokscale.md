---
title: Tokscale
tags: [entity, coding-agent, observability, token-usage, rust]
date: 2026-06-12
sources: [tokscale-architecture-analysis.md]
related: [[token-usage-observability]], [[coding-agent-observability]], [[claude-code]], [[codex]], [[claude-tap]]
---

# Tokscale

Rust 实现的本地 AI token usage analytics，从 Claude Code、Codex、OpenCode、Pi、Cursor、Gemini 等 session 文件/数据库解析 usage，做扫描、归一化、定价和 TUI/JSON 报表。详见 [[src-tokscale-architecture]]。

## 架构边界

Tokscale 是成本/用量观测层，不是请求 trace viewer，也不是 agent 执行器。它通过本地 session 文件/数据库还原 usage；[[claude-tap]] 则通过代理捕获真实请求。

## 选型判断

适合回答“哪些模型/客户端/项目花了多少 token 和钱”。不适合排查某次请求具体 prompt 或工具 schema；那应看 [[claude-tap]]。
