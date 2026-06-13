---
title: GitNexus
tags: [entity, code-intelligence, graph-rag, browser, static-analysis]
date: 2026-06-13
sources: [gitnexus-architecture-analysis.md]
related: [[code-graph]], [[code-semantic-search-rag-map]], [[code-review-graph]], [[deepwiki-open]], [[repo-wiki-generation]], [[mcp]]
---

# GitNexus

GitNexus 是 repo knowledge graph / Graph RAG 项目，强调浏览器端和交互式代码理解。它覆盖 `gitnexus/src` 核心图谱、web app、shared package、Claude/Cursor plugins、PR swarm review、eval 和 intra-procedural taint analysis。详见 [[src-gitnexus-architecture]]。

## 架构边界

GitNexus 不只是文档生成器，也不只是向量检索。它把静态分析、代码知识图谱、Graph RAG、浏览器 UI 和 agent/editor 插件放在同一条链路上，适合做交互式项目理解和 review 辅助。

## 关键设计

- `gitnexus/src` 承载图谱构建和分析逻辑。
- `gitnexus-web/src` 提供浏览器端交互。
- `gitnexus-shared/src` 共享类型和工具。
- Claude / Cursor integration 把图谱上下文接入 agent/editor。
- Taint analysis 表明它正在从结构图谱扩展到更具体的静态分析。

## 选型判断

需要交互式代码图谱和 Graph RAG 看 GitNexus；需要 local-first review graph / MCP 工具看 [[code-review-graph]]；需要自动生成 repo wiki 看 [[deepwiki-open]]；需要语义检索插件看 [[claude-context]] / [[memsearch]]。

