---
title: ReMe
tags: [entity, agent-memory, agentscope, retrieval, context-management]
date: 2026-06-13
sources: [reme-architecture-analysis.md]
related: [[agentscope]], [[agent-memory]], [[agent-memory-selection-matrix]], [[mem0]], [[memsearch]], [[tencentdb-agent-memory]], [[hybrid-search-rrf]]
---

# ReMe

ReMe 是 [[agentscope]] 生态的 memory management toolkit。它同时提供文件优先的 ReMeLight 和更完整的 vector/service pipeline，把 personal memory、task memory、tool memory、working memory 拆成独立 summary / retrieve op。详见 [[src-reme-architecture]]。

## 架构边界

ReMe 关注的是 AgentScope 应用里的 context management 和跨 session 记忆，不是独立的通用记忆服务。ReMeLight 偏个人可读、可迁移、可手改；vector/service pipeline 偏规模化 agent 应用。

## 关键设计

- `MEMORY.md`、daily journal、dialog JSONL 和 tool result cache 保留人工可读 source-of-truth。
- personal / task / tool / working memory 分别 summary 和 retrieve，避免一个大 memory 表统管所有语义。
- pre-reasoning hook 检查 token，必要时压缩旧消息并 offload 长工具输出。
- vector pipeline 可做 semantic retrieval、rerank/fusion 和频率/效用更新。

## 选型判断

AgentScope 内部应用优先看 ReMe；需要跨 framework、server、MCP 和插件生态的通用记忆层看 [[mem0]]；需要 Markdown source-of-truth + Milvus hybrid search 看 [[memsearch]]；需要 OpenClaw/Hermes 深度集成看 [[tencentdb-agent-memory]]。
