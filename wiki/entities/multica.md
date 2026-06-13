---
title: Multica
tags: [entity, managed-agent, coding-agent, teammate, go]
date: 2026-06-13
sources: [multica-architecture-analysis.md]
related: [[coding-agent-selection-map]], [[agent-delegation]], [[claude-code]], [[codex]], [[pi]], [[open-cowork]]
---

# Multica

Multica 是 managed agents platform，把 Claude Code、Codex、Copilot CLI、OpenClaw、OpenCode、Hermes、Gemini、Pi 等本地或云 runtime 抽成可分配任务的 agent teammate。详见 [[src-multica-architecture]]。

## 架构边界

Multica 不重写 coding agent loop。它的核心是 workspace、agent profile、issue board、task queue、runtime daemon、autopilot、squad、skills、activity timeline 和 WebSocket progress，把现有 CLI agent 管成团队工作台。

## 关键设计

- Go/Chi backend 负责 auth、workspace、agents、issues、task queue、skills 和 integrations。
- PostgreSQL/pgvector 存产品状态、任务、活动和检索上下文。
- 本地 daemon 检测可用 agent CLI，claim/start 任务，并回传 progress/log。
- Squad / Autopilot 是调度层，负责分派和周期性自动工作。

## 选型判断

需要“把多个 coding agent 当 teammate 管”时看 Multica。需要桌面 agent host 和 GUI/IM 控制看 [[open-cowork]]；需要单个 CLI agent 执行面看 [[codex]] / [[claude-code]] / [[pi]]；需要服务化 Agent app 看 [[agentscope-runtime]]。

