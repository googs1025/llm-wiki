---
title: code-review-graph
tags: [entity, code-graph, code-intelligence, mcp, local-first]
date: 2026-06-12
sources: [code-review-graph-architecture-analysis.md]
related: [[code-graph]], [[code-semantic-search]], [[repo-wiki-generation]], [[mcp]], [[code-semantic-search-rag-map]]
---

# code-review-graph

local-first code intelligence graph，面向 MCP/CLI/VSCode/skills 提供代码结构、变更理解和 review 相关上下文。详见 [[src-code-review-graph-architecture]]。

## 架构边界

它代表 Code RAG 从“语义搜索”进入“代码图谱”的路线。与 [[claude-context]] / [[memsearch]] 不同，code-review-graph 更强调图结构、调用关系、review evidence 和本地工具集成。

## 选型判断

适合需要结构化代码理解、review evidence、MCP 工具暴露的本地工作流。若目标是自动生成 repo wiki，应看 [[deepwiki-open]] 和 [[repo-wiki-generation]]。
