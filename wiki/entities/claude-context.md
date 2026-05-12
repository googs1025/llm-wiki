---
title: Claude Context
tags: [mcp, code-rag, llm-infra, open-source, zilliz]
date: 2026-05-12
sources: [src-claude-context-architecture]
related: [[mcp]], [[milvus]], [[claude-code]], [[claude-mem]], [[code-semantic-search]], [[hybrid-search-rrf]], [[merkle-dag-fingerprint]], [[ai-agent-plugin-patterns]]
---

# Claude Context

[zilliztech/claude-context](https://github.com/zilliztech/claude-context)，v0.1.13。Zilliz 出品的 [[mcp|MCP]] 插件，把整个代码库通过 [[code-semantic-search|语义检索]]"塞进" AI Agent 上下文。

## 解决什么

让 [[claude-code]] / Cursor / Gemini CLI / Codex 等 Agent 在大型 repo 中**一次查询直达目标**，避免多轮 grep/read 探索。

## 三段式架构

| 层 | 包 | 职责 |
|---|---|---|
| 引擎 | `packages/core` | Splitter / Embedding / VectorDB / Sync —— 不感知协议 |
| 协议 | `packages/mcp` | 4 个 MCP 工具 + handlers + SyncManager + Snapshot |
| 客户端 | `packages/vscode-extension`、`packages/chrome-extension` | 独立 UI |

详见 [[ai-agent-plugin-patterns]] 的"三段式接口分层"原则。

## 4 个 MCP 工具

- `index_codebase` — 全量索引
- `search_code` — 自然语言查询
- `clear_index` — 清除（协作式取消）
- `get_indexing_status` — 进度查询

## 关键技术选型

- **Splitter**：AST (tree-sitter ×9 语言) → LangChain 字符切分兜底
- **Embedding**：OpenAI / Voyage / Gemini / Ollama 四选一
- **VectorDB**：[[milvus|Milvus]] / Milvus-RESTful
- **检索**：Dense + Sparse 双向量 + RRF 重排（详见 [[hybrid-search-rrf]]）
- **增量同步**：[[merkle-dag-fingerprint|Merkle DAG]]，5 分钟后台轮询

## 关键常量

| 参数 | 值 | 说明 |
|------|---|------|
| `EMBEDDING_BATCH_SIZE` | 100 | 流式批处理 |
| `CHUNK_LIMIT` | 450000 | Milvus 单 collection 上限保护 |
| `chunkSize / chunkOverlap` | 2500 / 300 | AST splitter 默认 |

## 与 claude-mem 的对照

[[claude-mem]] 解决**跨会话记忆**，claude-context 解决**代码库理解**——但两者共享大量设计原则：接口分层、协议通道纪律、流式批处理、状态自愈。汇总在 [[ai-agent-plugin-patterns]]。

## 演进方向

接口层稳定，实现层在扩展：

- 多 provider（Gemini Embedding 2、Solidity 语言支持）
- 后台同步可配置化（`CLAUDE_CONTEXT_BACKGROUND_SYNC` env）
- 请求级 splitter 切换

## 参考

- [[src-claude-context-architecture]]
- DeepWiki: https://deepwiki.com/zilliztech/claude-context
