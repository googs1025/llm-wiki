---
title: Codex Plugin for Claude Code 架构与设计思路分析
tags: [architecture, ai-agent, coding-agent, plugin]
date: 2026-06-12
sources: [codex-plugin-cc-architecture-analysis.md]
related: ["[[claude-code]]", "[[codex]]", "[[ai-agent-plugin-patterns]]", "[[agent-skills-plugin-system-map]]", "[[coding-agent-selection-map]]"]
---

# Codex Plugin for Claude Code 架构与设计思路分析

> 原文：`raw/codex-plugin-cc-architecture-analysis.md` · 仓库：https://github.com/openai/codex-plugin-cc · 分析版本 HEAD `807e03a`（2026-04-18）

## 一句话定位

Claude Code 插件形态的 Codex 接入层，把 `/codex:*` slash command、Codex app-server broker、后台 job 状态和 session hook 组合起来，让 Claude Code 可以调用 Codex 做 review、adversarial review 和 rescue task。它不是新的 agent runtime，而是一个跨 agent 委托/审查胶水层。 这页和 [[claude-code]] [[codex]] [[ai-agent-plugin-patterns]] [[agent-skills-plugin-system-map]] 形成对比，重点帮助理解项目边界和选型位置。

## 核心架构图

```
┌──────────────────── Claude Code Session ────────────────────┐
│ /codex:review /rescue /status /result /cancel /setup          │
│ command markdown: tools + argument policy + UX mode choice     │
└───────────────┬───────────────────────────────┬───────────────┘
                │ foreground/background          │ hooks
                v                                v
┌─────────────────────────────┐     ┌────────────────────────────┐
│ codex-companion.mjs          │     │ session lifecycle / gate    │
│ parse args, git target, job  │     │ env, broker cleanup, review │
│ state, rendering, setup      │     │ before stop if enabled      │
└───────────────┬─────────────┘     └──────────────┬─────────────┘
                │ app-server JSON-RPC / child proc  │
                v                                  │
┌─────────────────────────────┐                    │
│ app-server-broker.mjs        │<───────────────────┘
│ socket server, busy control, │
│ streaming notification route │
└───────────────┬─────────────┘
                v
┌─────────────────────────────┐
│ OpenAI Codex CLI / appserver │
└─────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|------|------|
| Claude 插件入口 | 把 Claude Code slash command 映射为 review/rescue/status/result/cancel/setup 等操作，并约束 allowed-tools 与交互策略。 |
| Companion CLI | 统一解析参数、检查 Codex 安装/登录、收集 git review context、创建/更新 job state、渲染结果。 |
| App-server broker | 复用 Codex app-server 连接，通过 JSON-RPC over socket 转发 turn/review 请求，并串行化 streaming ownership。 |
| 生命周期与审查 gate | 在 Claude session start/end 写入环境、清理 broker/job，并可在 stop 前强制 Codex review gate。 |
| 测试与发布 | Node test runner 覆盖命令渲染、broker endpoint、git target、state/runtime 行为。 |

## 关键数据流

```
User runs /codex:review --background
  │
  ├─ command markdown estimates git diff size and chooses background UX
  │
  ├─ codex-companion.mjs review parses --base/--scope and git context
  │
  ├─ app-server broker starts or reuses Codex app-server connection
  │
  ├─ Codex review stream writes tracked job log/state
  │
  └─ /codex:status and /codex:result read the persisted job snapshot
```

## 设计决策与哲学

- **插件是“薄入口”，状态在 companion 层集中**：命令 markdown 只负责 Claude Code 侧工具权限和交互策略，真正的参数、job、输出渲染集中在 `codex-companion.mjs`，避免多个 slash command 各自实现状态机。
- **broker 复用 app-server，但主动串行化 streaming 请求**：`app-server-broker.mjs` 用 active request/stream socket 防止多个 Claude command 同时占用 Codex app-server，保留 interrupt 的例外路径。
- **把 review gate 做成可选 hook**：`stop-review-gate-hook.mjs` 只有配置打开时才阻断 session stop，默认不改变 Claude Code 的结束语义。

## 与同类项目的架构差异

| 维度 | Codex Plugin for Claude Code | 同类 A | 同类 B |
|------|------|------|------|
| 扩展形态 | Claude Code plugin + Codex CLI | Claude Code 自身 slash command/agent | OpenAI Codex CLI 原生命令 |
| 核心价值 | 跨 agent 委托与审查 | 单 agent 内部技能/子代理 | 独立 coding agent 工作流 |
| 状态边界 | 插件 state + Codex app-server/job log | Claude session state | Codex session/rollout/app-server state |

## 选型提示

如果你在快速理解或选型，先判断它是“执行任务的 agent/runtime”、“观察与计量工具”、“消息/插件 bridge”，还是“Kubernetes/GPU 控制面”。同一条 star 列表里的项目经常解决的是相邻但不同的问题：比如 trace viewer 不能替代 remote control bridge，GPU Operator 也不能替代 DRA driver 或 device plugin 的分配路径。

## 相关页面

- [[claude-code]]
- [[codex]]
- [[ai-agent-plugin-patterns]]
- [[agent-skills-plugin-system-map]]
- [[coding-agent-selection-map]]
