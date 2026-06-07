---
title: Milvus
tags: [vector-database, rag, llm-infra, open-source, zilliz]
date: 2026-06-07
sources: [src-claude-context-architecture, src-memsearch-architecture]
related: [[claude-context]], [[memsearch]], [[hybrid-search-rrf]], [[code-semantic-search]], [[agent-memory]]
---

# Milvus

Milvus 是 Zilliz 主导的开源向量数据库，也是 [[claude-context]] 和 [[memsearch]] 的核心检索后端。这个 wiki 里重点关注它在 AI Agent 工程里的角色：承接 dense vector、sparse/BM25、metadata filter 和 hybrid retrieval，让 Agent 能用自然语言检索代码或记忆。

## 在已分析项目中的用法

- [[claude-context]]：把代码库 chunk 索引到 Milvus / Milvus RESTful，做代码语义检索。
- [[memsearch]]：把 `.memsearch/*.md` 记忆 chunk 索引到 Milvus Lite / Milvus Server / Zilliz Cloud，做 dense + BM25 + RRF 的长期记忆检索。

## 关键能力

- **向量检索**：存储 embedding 并按相似度召回。
- **全文/稀疏检索**：在 memsearch 中通过 analyzer + BM25 Function 生成 sparse vector。
- **混合检索**：dense 和 sparse 两路召回后用 RRF 融合，详见 [[hybrid-search-rrf]]。
- **部署形态**：本地 Milvus Lite、Milvus Server、Zilliz Cloud。

## 相关页面

- [[src-claude-context-architecture]]
- [[src-memsearch-architecture]]
- [[claude-context]]
- [[memsearch]]
- [[hybrid-search-rrf]]
- [[code-semantic-search]]
- [[agent-memory]]
