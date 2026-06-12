---
title: Token Usage Observability
tags: [concept, token-usage, cost, observability, coding-agent, telemetry]
date: 2026-06-12
sources: [tokscale-architecture-analysis.md, loongsuite-pilot-architecture-analysis.md]
related: [[tokscale]], [[loongsuite-pilot]], [[coding-agent-observability]], [[codex]], [[claude-code]], [[ai-as-compressor]]
---

# Token Usage Observability

Token usage observability 指跨模型、跨客户端、跨 workspace 汇总 token、cache read/write、reasoning token 和成本的能力。它是 coding agent 进入长期使用后的基础治理面。

## 为什么重要

Agent 工具调用越多，成本越难从单次对话感知。需要把 session 历史转成按日期、模型、client、workspace、session 的统计，才能知道哪些工作流消耗最大。

## 代表项目

[[tokscale]] 从 Claude Code、Codex、OpenCode、Pi、Cursor、Gemini 等本地数据源解析 usage，再通过多源 pricing service 估价。

[[loongsuite-pilot]] 不只是 token cost CLI，它把 token / trace / tool / session 等 agent activity 统一成 telemetry entry，并能通过 JSONL、SLS、HTTP、OTLP trace 输出到后端。因此它更适合长期采集和上报，[[tokscale]] 更适合本地扫描与成本报表。

## 与 trace 的区别

[[claude-tap]] 关注单次请求的证据；Token usage observability 关注长期成本和趋势。两者互补：trace 找原因，usage 看规模。[[loongsuite-pilot]] 则把 usage 视为更大 telemetry schema 的一部分，适合和组织级日志/trace 后端连接。
