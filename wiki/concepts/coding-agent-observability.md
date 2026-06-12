---
title: Coding Agent Observability
tags: [concept, coding-agent, observability, trace, token-usage, telemetry]
date: 2026-06-12
sources: [claude-tap-architecture-analysis.md, tokscale-architecture-analysis.md, loongsuite-pilot-architecture-analysis.md]
related: [[claude-tap]], [[tokscale]], [[loongsuite-pilot]], [[cc-connect]], [[codex]], [[claude-code]]
---

# Coding Agent Observability

Coding agent observability 关注本地/远程 coding agent 的上下文、工具、请求、流式响应、token usage、成本、session 历史和任务状态是否可观察、可审计、可复盘。

## 三条主线

| 方向 | 代表项目 | 数据来源 | 回答的问题 |
|---|---|---|---|
| 请求 trace | [[claude-tap]] | HTTP/SSE/WS 代理流量 | 这次 Agent 到底发了什么上下文？ |
| 用量/成本 | [[tokscale]] | 本地 session 文件/数据库 | 哪些 client/model/workspace 花了多少 token？ |
| 常驻 telemetry collector | [[loongsuite-pilot]] | hooks、SQLite、session、trace、CLI log | 多个 coding agent 的活动如何统一采集、脱敏、上报？ |

## 和执行层的边界

[[codex]]、[[claude-code]]、Pi 这类项目负责执行；[[claude-tap]]、[[tokscale]] 和 [[loongsuite-pilot]] 不执行任务，而是补足证据链、成本视角和长期 telemetry 管道。[[cc-connect]] 属于远程入口层，但也会产生运行状态和 usage footer，因此与 observability 相邻。

## 选型视角

如果问题是“单次请求为什么异常”，优先看 [[claude-tap]]；如果问题是“长期成本和 token 分布”，优先看 [[tokscale]]；如果问题是“把多种本地 coding agent 的活动统一接入组织观测后端”，[[loongsuite-pilot]] 更合适。三者的采集边界不同，组合后才覆盖请求证据、成本趋势和常驻 pipeline。
