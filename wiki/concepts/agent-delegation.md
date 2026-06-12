---
title: Agent Delegation
tags: [concept, ai-agent, plugin, coding-agent, delegation]
date: 2026-06-12
sources: [codex-plugin-cc-architecture-analysis.md, codex-architecture-analysis.md]
related: [[codex-plugin-cc]], [[codex]], [[claude-code]], [[ai-agent-plugin-patterns]], [[agent-skills-plugin-system-map]]
---

# Agent Delegation

Agent delegation 是让一个 Agent/工作流把审查、修复、取证或后台任务委托给另一个 Agent 的模式。它不同于普通工具调用：被委托方通常有自己的 session、状态、模型和输出格式。

## 典型实现

[[codex-plugin-cc]] 是当前 wiki 里的代表：Claude Code slash command 通过 companion/broker/job state 调用 [[codex]] 做 review、adversarial review 或 rescue task。

## 设计要点

- **边界清晰**：委托方不应把被委托方当成普通函数调用；需要 job id、status、result、cancel。
- **输出可审计**：review/rescue 输出应保留原文，避免中间层过度改写。
- **生命周期清理**：session end 时要清理后台 job、broker 和残留进程。
- **权限最小化**：review-only 与 write-capable task 要分开。

## 和插件/技能的关系

[[agent-skills-plugin-system-map]] 讨论 plugin / skill / MCP tool 三种扩展形态；agent delegation 是更高一层的协作模式，常由 plugin 或 slash command 承载。
