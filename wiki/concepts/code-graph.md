---
title: Code Graph
tags: [concept, code-intelligence, code-rag, graph, mcp]
date: 2026-06-12
sources: [code-review-graph-architecture-analysis.md, gitnexus-architecture-analysis.md]
related: [[code-review-graph]], [[code-semantic-search]], [[repo-wiki-generation]], [[mcp]], [[code-semantic-search-rag-map]]
---

# Code Graph

Code graph 把仓库从文件/文本块提升为符号、调用、依赖、变更、风险和证据的图结构，服务于 review、RAG、影响面分析和 agent 工具调用。

## 和语义搜索的区别

[[code-semantic-search]] 关注“给定 query 找相似代码块”；code graph 关注“代码元素之间如何连接”。两者互补：语义搜索负责召回，图负责解释路径、边界和影响。

## 代表项目

- [[code-review-graph]]：local-first code intelligence graph for MCP/CLI/VSCode。
- GitNexus：browser-side repo knowledge graph + Graph RAG + taint analysis。

## 选型提示

需要 line-level evidence、调用关系、变更影响面时，code graph 比纯 vector search 更有解释力；需要快速语义召回时，vector/hybrid search 更轻。
