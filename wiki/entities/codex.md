---
title: OpenAI Codex CLI
tags: [entity, coding-agent, ai-agent, rust, openai]
date: 2026-06-12
sources: [codex-architecture-analysis.md, codex-plugin-cc-architecture-analysis.md]
related: [[claude-code]], [[coding-agent-selection-map]], [[agent-delegation]], [[coding-agent-observability]], [[tokscale]]
---

# OpenAI Codex CLI

OpenAI 官方 terminal coding agent，重点是把仓库上下文、工具调用、审批/沙箱、patch 和会话状态组织成一个本地开发循环。详见 [[src-codex-architecture]]。

## 架构边界

Codex CLI 是执行 loop 本体：它负责读写仓库、调用工具、维护 session/app-server/MCP 等运行状态。它不是消息平台、trace viewer 或 token 报表工具；这些能力分别由 [[cc-connect]]、[[claude-tap]]、[[tokscale]] 这类生态配套补齐。

## 选型判断

| 场景 | 判断 |
|---|---|
| 官方 OpenAI coding agent | 优先看 Codex CLI |
| 想在 Claude Code 内调用 Codex review/rescue | 看 [[codex-plugin-cc]] 和 [[agent-delegation]] |
| 想观察请求上下文 | 看 [[claude-tap]] |
| 想统计用量成本 | 看 [[tokscale]] |

## 相关源码页

- [[src-codex-architecture]]
- [[src-codex-plugin-cc-architecture]]
