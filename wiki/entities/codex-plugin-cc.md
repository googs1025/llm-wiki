---
title: Codex Plugin for Claude Code
tags: [entity, plugin, coding-agent, claude-code, openai]
date: 2026-06-12
sources: [codex-plugin-cc-architecture-analysis.md]
related: [[codex]], [[claude-code]], [[agent-delegation]], [[agent-skills-plugin-system-map]], [[ai-agent-plugin-patterns]]
---

# Codex Plugin for Claude Code

Claude Code 插件形态的 Codex 接入层，把 `/codex:*` slash command、Codex app-server broker、后台 job 状态和 session hook 组合起来。详见 [[src-codex-plugin-cc-architecture]]。

## 架构边界

它不是新的 coding agent，而是 [[claude-code]] 与 [[codex]] 之间的 delegation bridge。核心价值在于跨 agent 审查、rescue task、review gate 和 job 状态管理。

## 选型判断

适合：已经用 Claude Code，但希望引入 Codex 做独立 review 或救援任务。

不适合：想替代 Codex CLI 本体、做通用插件框架、或远程消息平台入口；这些分别看 [[codex]]、[[agent-skills-plugin-system-map]]、[[cc-connect]]。

## 相关概念

- [[agent-delegation]]
- [[ai-agent-plugin-patterns]]
- [[agent-skills-plugin-system-map]]
