---
title: Pi Agent Harness
tags: [entity, coding-agent, agent-harness, typescript, tui]
date: 2026-06-13
sources: [pi-architecture-analysis.md]
related: [[coding-agent-selection-map]], [[agent-skills-plugin-system-map]], [[claude-code]], [[codex]], [[mcp]], [[openshell]]
---

# Pi Agent Harness

Pi 是 TypeScript agent harness monorepo，而不是单一 coding CLI。核心包包括 `pi-ai` 多 provider LLM API、`pi-agent-core` tool calling/state 管理、`pi-coding-agent` 交互式 coding CLI 和 `pi-tui` terminal UI。详见 [[src-pi-architecture]]。

## 架构边界

Pi 的抽象顺序是先把多 provider LLM API 做稳，再在其上构建 agent core 和 coding agent。它默认不限制文件、进程、网络或凭据权限，因此团队或生产使用需要外部 sandbox，例如 [[openshell]]、Docker 或 micro-VM。

## 关键设计

- `packages/ai` 统一 provider registry、stream/complete、tool schema、token/cost、OAuth/API key。
- `packages/agent` 管理 agent loop 和 tool state。
- `packages/coding-agent` 聚合代码仓库工作流。
- `packages/tui` 提供 terminal rendering。
- TypeBox schema 用于 tool call 参数校验。

## 选型判断

需要 provider-neutral agent harness 时看 Pi。需要 Rust/IDE/LSP/DAP/hashline 等强工具能力看 [[oh-my-pi]]；需要治理边界和审批策略看 [[codex]]；需要把多个 CLI agent 编排成团队协作看 [[multica]]。

