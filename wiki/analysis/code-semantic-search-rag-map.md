---
title: Code Semantic Search / Code RAG 对比地图
tags: [code-rag, semantic-search, project-map, selection]
date: 2026-06-11
sources: [src-claude-context-architecture, src-memsearch-architecture]
related: [[claude-context]], [[memsearch]], [[milvus]], [[code-semantic-search]], [[hybrid-search-rrf]], [[merkle-dag-fingerprint]]
---

# Code Semantic Search / Code RAG 对比地图

代码语义检索和 Agent memory 容易混在一起。区别是：Code RAG 主要解决“大代码库如何按需给上下文”，Memory 主要解决“跨会话事实如何保存和召回”。[[claude-context]] 和 [[memsearch]] 正好代表两条路线。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 定位 |
|------|------|-----------|-------|--------|------|
| [[claude-context]] | https://github.com/zilliztech/claude-context | 2026-06-08 | 11k | TypeScript | Code search MCP for Claude Code |
| [[memsearch]] | https://github.com/zilliztech/memsearch | 2026-06-01 | 1.9k | Python | Markdown memory + Milvus unified memory layer |
| [[milvus]] | https://github.com/milvus-io/milvus | 2026-06-11 | 44k | Go | cloud-native vector database |
| tree-sitter | https://github.com/tree-sitter/tree-sitter | 2026-06-10 | 25k | Rust | incremental parsing system |

## 选型

| 需求 | 首选 |
|------|------|
| 大代码库语义搜索 MCP | [[claude-context]] |
| coding agent 会话/项目记忆搜索 | [[memsearch]] |
| 自建大规模向量/混合检索底座 | [[milvus]] |
| 需要 AST-aware chunking | tree-sitter + fallback splitter |

## 架构差异

| 维度 | [[claude-context]] | [[memsearch]] | [[milvus]] | tree-sitter |
|------|--------------------|---------------|------------|-------------|
| 处理对象 | repo source code | Markdown memory / transcripts | vector collections | source parse tree |
| 真相层 | git workspace files | `.memsearch/*.md` | 外部业务数据 | 源码文本 |
| 索引层 | AST/langchain chunks + vector | Markdown chunks + Milvus dense/BM25 | ANN + scalar/filter | 不负责索引 |
| Agent 接口 | MCP search tools | hook/skill/search/expand | SDK/API | library |
| 核心风险 | 增量同步和 chunk 质量 | Markdown/index 一致性 | 运维复杂度 | 语言 grammar 覆盖 |

## Code RAG 的设计轴

- **chunking**：函数/类边界优先，失败时字符切分兜底，避免边缘语言卡死全库。
- **incremental sync**：用 content hash / Merkle DAG 判断变更，避免全量重嵌入。
- **hybrid retrieval**：代码路径、符号名、错误信息适合 BM25；意图和设计问题适合 vector。
- **evidence trace**：返回文件、行号、chunk id，避免 Agent 只拿摘要无法定位。
- **memory 分离**：代码检索结果不应直接变成长期记忆，除非经过写入策略和 scope 审核。

## 避坑条件

- 不要只做 vector top-k；代码里的路径、函数名、issue id 经常更适合 lexical search。
- 不要把 AST parser 失败当 fatal；[[claude-context]] 的 AST 优先 + fallback 是更稳模式。
- 不要让索引成为唯一事实；repo 文件或 Markdown 文件必须可重建索引。
- 不要把所有 chunk 自动注入上下文；先 search，再 open/expand。

