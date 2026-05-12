---
title: claude-mem
tags: [agent-memory, claude-code, open-source, llm-infra]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[claude-code]], [[claude-agent-sdk]], [[agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[ai-as-compressor]]
---

# claude-mem

给 [[claude-code]] 装上长期记忆的开源插件（v13.1.0, 仓库 thedotmack/claude-mem）。

## 解决的问题

宿主 Claude Code 本身没有跨会话记忆——每次开新会话都是白板。claude-mem 通过宿主提供的 6 个生命周期 hook 无侵入采集工具调用，异步压缩成结构化"观察"存进本地双索引，下次开会话时自动检索并注入相关历史。

## 核心特征

- **跨会话连续性**：用户问"上次怎么解决这个 bug"时能真的检索到上次的步骤
- **本地优先**：所有数据存 `~/.claude-mem/`，开源核心可审计
- **无侵入采集**：通过宿主 hook 接口工作，不修改 Claude Code
- **多 profile 支持**：两个环境变量切换工作账号 / 私人账号

## 架构骨架

- **边缘**：`bun-runner.js` + 6 个 Lifecycle Hook handler
- **后台**：Worker Service（Express daemon，端口 `37700 + uid%100`）+ BullMQ
- **存储**：SQLite (FTS5) + Chroma 向量库

详细工作流参见 [[event-driven-memory-pipeline]]。

## 设计哲学

claude-mem 是 [[ai-as-compressor]] 设计哲学的典型实现——LLM 不是用来"回答用户"，而是用来把噪声大的工具调用日志压缩成结构化字段。压缩用的 token 成本，换来后续每次会话的检索效率。

## 关键依赖

- [[claude-agent-sdk]] — 异步压缩/总结
- BullMQ — 后台任务队列（待建实体页）
- Chroma — 向量库（待建实体页）
- better-sqlite3 + FTS5 — 主存储 + 全文检索
- MCP (Model Context Protocol) — Skill / 远程模式

## 部署模式

| 模式 | 存储 | 适用 |
|------|------|------|
| 单机 | SQLite + Chroma | 个人开发者 |
| server-beta | Postgres + MCP + Docker | 团队共享 + 审计 |

通过 `runtime-selector.ts` 在两种模式间切换，保留单机回退。

## 演进方向

从「单机插件」演化到「团队可共享的后台服务」（PR #2383）。

## 参考

- 完整分析：[[src-claude-mem-architecture]]