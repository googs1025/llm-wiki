---
title: claude-tap 架构与设计思路分析
tags: [architecture, observability, coding-agent, proxy]
date: 2026-06-12
sources: [claude-tap-architecture-analysis.md]
related: ["[[claude-code]]", "[[codex]]", "[[openclaw]]", "[[coding-agent-selection-map]]", "[[agent-framework-programming-model-map]]"]
---

# claude-tap 架构与设计思路分析

> 原文：`raw/claude-tap-architecture-analysis.md` · 仓库：https://github.com/liaohch3/claude-tap · 分析版本 HEAD `a11231b`（2026-06-12）

## 一句话定位

本地代理和 trace viewer，用 reverse proxy / forward proxy 截获 Claude Code、Codex CLI、Gemini CLI、Cursor CLI 等 coding agent 的真实 API 请求，落 SQLite trace，再提供 live viewer/export。它解决的是 agent 行为可观测和上下文取证，而不是执行任务。 这页和 [[claude-code]] [[codex]] [[openclaw]] [[coding-agent-selection-map]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────────── AI Coding CLI ────────────────┐
│ Claude Code / Codex / Gemini / Cursor / Kimi   │
└──────────────┬───────────────────────┬─────────┘
               │ reverse proxy target   │ forward proxy CONNECT/TLS
               v                       v
┌────────────────────────┐   ┌────────────────────────┐
│ proxy.py                │   │ forward_proxy.py        │
│ path allowlist, headers,│   │ MITM CA, HTTPS tunnel,  │
│ SSE/body reconstruction │   │ skip package downloads  │
└──────────────┬─────────┘   └──────────────┬─────────┘
               │ normalized trace record     │
               v                             v
┌──────────────────────────────────────────────────────┐
│ TraceWriter / TraceStore (SQLite, session summary)   │
└──────────────┬────────────────────────────┬──────────┘
               │ live broadcast             │ export
               v                            v
┌────────────────────────┐   ┌────────────────────────┐
│ LiveViewer/dashboard    │   │ self-contained viewer   │
│ search, diff, sections  │   │ HTML + embedded trace   │
└────────────────────────┘   └────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| CLI 编排 | 选择 client、检测目标 upstream、准备 CA/live dashboard、启动被包裹的 CLI。 |
| 反向代理 | 对已知 LLM API path 做 allowlist、转发 upstream、记录 request/response/SSE/usage。 |
| 正向代理/MITM | 处理 CONNECT/TLS 终止，适配必须访问真实域名的 OAuth/SaaS client。 |
| Trace 存储 | 按 session 写 SQLite，累积 token/model/error 摘要，支持迁移和清理。 |
| Viewer/export | 把 trace 渲染成本地 live dashboard 或 self-contained HTML，并支持 diff/lazy loading。 |

## 关键数据流

```
claude-tap --tap-client codex -- <prompt>
  │
  ├─ cli.py detects selected client and target API base URL
  │
  ├─ proxy.py / forward_proxy.py forwards model API request upstream
  │
  ├─ body, headers, SSE/WebSocket/Bedrock events are normalized
  │
  ├─ TraceWriter appends record and updates usage/model counters
  │
  └─ LiveViewer receives broadcast; export embeds JSON into viewer.html
```

## 设计决策与哲学

- **把“能不能记录”放在代理边界判断**：`proxy.py` 的 path allowlist 和 `forward_proxy.py` 的 package-manager skip 让它尽量只持久化模型相关请求，减少误抓普通下载流量。
- **SQLite 是本地证据库，不依赖托管服务**：`TraceWriter` 只追加本地 trace/session summary，适合 debug、复盘、分享 HTML artifact。
- **reverse proxy 与 forward proxy 并存**：前者适合可改 base URL 的 client，后者适合 OAuth 或真实域名绑定更强的 client。

## 与同类项目的架构差异

| 维度 | claude-tap | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | 请求级 trace viewer | tokscale: token usage analytics | cc-connect: remote chat bridge |
| 输入 | 真实 HTTP/SSE/WS 流量 | 本地 session 文件/数据库 | 聊天平台消息 |
| 输出 | 可审计 trace + diff viewer | 成本/用量报表 | 远程驱动 agent |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[claude-code]]
- [[codex]]
- [[openclaw]]
- [[coding-agent-selection-map]]
- [[agent-framework-programming-model-map]]
