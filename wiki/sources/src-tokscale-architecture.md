---
title: Tokscale 架构与设计思路分析
tags: [architecture, observability, rust, coding-agent]
date: 2026-06-12
sources: [tokscale-architecture-analysis.md]
related: ["[[claude-code]]", "[[codex]]", "[[openclaw]]", "[[agent-memory-selection-matrix]]", "[[coding-agent-selection-map]]"]
---

# Tokscale 架构与设计思路分析

> 原文：`raw/tokscale-architecture-analysis.md` · 仓库：https://github.com/junhoyeo/tokscale · 分析版本 HEAD `aebe4ea`（2026-06-10）

## 一句话定位

Rust 实现的 AI token usage analytics 工具，从 Claude Code、Codex、OpenCode、Pi、Cursor、Gemini 等本地 session 文件/数据库中解析 usage，做并行扫描、归一化、成本定价和 TUI/JSON/报表展示。它是“本地账单与行为计量层”，不是 agent 执行器。 这页和 [[claude-code]] [[codex]] [[openclaw]] [[agent-memory-selection-matrix]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────── Local Agent Data ────────────┐
│ ~/.claude  ~/.codex  OpenCode DB  ...    │
└──────────────┬──────────────────────────┘
               │ paths + scanner settings
               v
┌──────────────────────────────────────────┐
│ Scanner (walkdir + rayon)                │
│ files[], opencode_dbs, hermes_db, ...    │
└──────────────┬──────────────────────────┘
               │ per-client parser
               v
┌──────────────────────────────────────────┐
│ UnifiedMessage / sessionize / workspace  │
└──────────────┬──────────────────────────┘
               │ parallel aggregation
               v
┌──────────────────────┐   ┌────────────────────────┐
│ Daily/session totals  │<──│ PricingService datasets │
│ model/client/provider │   │ custom + public sources │
└──────────────┬───────┘   └────────────────────────┘
               v
┌──────────────────────────────────────────┐
│ CLI table / JSON / TUI / graph frontend   │
└──────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| CLI/TUI | 定义 models/monthly/hourly/pricing/clients/login 等命令和交互式 TUI。 |
| 扫描器 | 发现不同 agent 的 session 文件、SQLite DB、额外 scan path，并做并行文件遍历。 |
| Parser/session 模型 | 把各 agent 特有 JSONL/DB 归一成 UnifiedMessage、session、workspace、time metrics。 |
| 聚合器 | 按日期/session/client/model/provider/workspace 做 rayon map-reduce 聚合。 |
| 定价服务 | 组合 custom/LiteLLM/OpenRouter/models.dev/Cursor override，给模型 usage 估价。 |

## 关键数据流

```
tokscale models --group-by client,model
  │
  ├─ CLI parses client/date/home flags and scanner settings
  │
  ├─ scanner discovers local JSONL/SQLite session sources in parallel
  │
  ├─ sessions/<client>.rs normalizes usage into UnifiedMessage
  │
  ├─ aggregator folds messages into daily/session/model totals
  │
  ├─ PricingService resolves model price with fallbacks/overrides
  │
  └─ CLI/TUI renders table, JSON, cache, contribution graph
```

## 设计决策与哲学

- **先归一消息，再做聚合**：各 agent parser 吸收格式差异，后续 group-by 和成本计算只依赖 UnifiedMessage/TokenBreakdown。
- **并行扫描与聚合是核心性能假设**：`scanner.rs` 和 `aggregator.rs` 使用 walkdir/rayon，适合大规模本地 session 历史。
- **定价采用多源 fallback**：`PricingService` 组合 custom、LiteLLM、OpenRouter、models.dev 和 Cursor override，承认模型 ID 演进很快。

## 与同类项目的架构差异

| 维度 | Tokscale | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | usage/cost analytics | claude-tap: request trace | cc-connect: remote control bridge |
| 数据来源 | session 文件/DB | HTTP/SSE/WS 流量 | 聊天平台消息和 agent stdout |
| 输出 | 成本/模型/时间报表 | 上下文证据和 diff | 聊天回复和任务执行 |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[claude-code]]
- [[codex]]
- [[openclaw]]
- [[agent-memory-selection-matrix]]
- [[coding-agent-selection-map]]
