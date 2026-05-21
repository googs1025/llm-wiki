---
title: agentmemory
tags: [agent-memory, ai-agent, llm-infra, open-source, mcp]
date: 2026-05-21
sources: [src-agentmemory-architecture]
related: [[claude-code]], [[claude-mem]], [[powermem]], [[claude-context]], [[mcp]], [[agent-memory]], [[event-driven-memory-pipeline]], [[hybrid-search-rrf]], [[ebbinghaus-forgetting-curve]], [[ai-as-compressor]]
---

# agentmemory

Rohit Ghumare 出品的本地化跨 Agent **持久记忆服务**（仓库 rohitg00/agentmemory，v0.9.21，Apache-2.0）。一个 worker 同时给 [[claude-code]] / Codex / Cursor / Gemini CLI / Hermes / OpenClaw / pi / OpenCode 及任何 [[mcp]] 客户端供应记忆。建立在 iii-engine 的 Worker/Function/Trigger 三原语之上。

## 解决的问题

AI 编码 Agent 跨会话是白板——每个新对话都得重新解释代码库、决策、踩过的坑。[[claude-mem]] 解决了单一 Agent（Claude Code）的版本；agentmemory 把这件事做到**跨 Agent**：所有 IDE / CLI Agent 共用同一个 `:3111` worker、同一份 SQLite，记忆在工具之间流通。

## 核心特征

- **跨 Agent 共享**：12 个 Claude Code hooks + Codex 6 hooks + 各 Agent 原生插件 + 53 个 [[mcp]] tools，所有客户端共用记忆
- **零外部依赖**：本地 Node ESM + iii-engine + SQLite，无需 Postgres / pgvector / Qdrant / Redis
- **零 LLM 默认**：启发式压缩（`buildSyntheticCompression`）是默认路径，要 `AGENTMEMORY_AUTO_COMPRESS=true` 才走 LLM——保护用户的 API token
- **Context injection 默认关**（issue #143）：Hook 只抓不注入，避免 Claude Pro session token 被记忆查询消耗
- **三流混合检索**：BM25 + Vector + Knowledge Graph，RRF (K=60) 融合，可选 reranker（[[hybrid-search-rrf]]）
- **多层记忆**：32+ KV scope（episodic / working / semantic / procedural / graph / orchestration / lessons / crystals / sketches / sentinels / …）+ 强度衰减 sweep（[[ebbinghaus-forgetting-curve]]）
- **实时 viewer**：默认 `:3113` 上跑 WebSocket UI，看记忆实时流入
- **950+ tests 通过 + 公开评测**：LongMemEval / Coding-Life benchmark 跑分内置在仓库

## 架构骨架

- **总线**：iii-engine WebSocket（钉版 v0.11.2，因为 v0.11.6 sandbox 模型不兼容当前 worker）
- **存储**：iii-engine StateModule 抽象的 SQLite，路径 `./data/state_store.db`
- **业务函数**：`src/functions/*.ts` 约 60 个 `mem::*` 函数，扁平注册在 `src/index.ts:204-303`
- **触发层**：124 REST endpoints `/agentmemory/*`（`:3111`）+ 53 MCP tools（默认仅 8 暴露）+ event triggers
- **状态层**：内存 BM25 倒排表 + 内存 VectorIndex（Float32Array cosine）+ HybridSearch + 周期 IndexPersistence

详细参见 [[src-agentmemory-architecture]]。

## 与 claude-mem / powermem 的关系

三者解决同一问题（[[agent-memory]]），但走向了三种不同的实现：

| 维度 | agentmemory | [[claude-mem]] | [[powermem]] |
|------|-------------|----------------|--------------|
| 部署形态 | Node + iii-engine + SQLite | Node + Express daemon + chroma + bullmq | OceanBase 数据库扩展 |
| 客户端范围 | 任何 MCP 客户端 + 8 个 Agent 原生插件 | 专一 Claude Code | 任何后端通过 SQL/向量 API 接入 |
| 检索栈 | BM25 + Vector + Graph (RRF) | Vector (chroma) + FTS5 | 向量 + 全文 + 稀疏 + 图 (四路) |
| LLM 用量 | **默认零 LLM** | LLM 压缩必需 | LLM 抽取必需 |
| 衰减机制 | 强度衰减 + 4 类定时 sweep | 无（只压缩不衰减） | working/short/long 三层 Ebbinghaus |
| MCP tool 数 | 53（默认 8） | 6 | 由后端决定 |

设计哲学层面：[[claude-mem]] 是 [[ai-as-compressor]] 的纯净实现（LLM 压噪声）；agentmemory 是对该哲学的**成本反思**（默认关 LLM，启发式优先）；[[powermem]] 是把同一套机制下沉到数据库层。

## 关键依赖

- iii-engine v0.11.2（外部 Rust 进程，Worker/Function/Trigger 总线）
- iii-sdk（TypeScript binding）
- `@modelcontextprotocol/sdk` — MCP 协议
- `@xenova/transformers` — 本地嵌入（零云依赖路径）
- `@clack/prompts` — CLI 交互

## 已知限制

- 内存 VectorIndex 暴力扫表，5 万 observation 量级以上需要替换为 ANN（HNSW / FAISS / pgvector）
- 默认无 `AGENTMEMORY_SECRET`，任何能访问 localhost 的本机进程都能读写记忆
- `unhandledRejection` 顶层 60s 节流吞掉异常，可能掩盖真正的 bug
- 添加一个 MCP tool 需同步 7 处文件（AGENTS.md 列出），PR 漏改风险高

## 相关页面

- [[src-agentmemory-architecture]] — 完整架构源摘要
- [[agent-memory]] — 领域综述
- [[claude-mem]] — 单 Agent 版同类
- [[powermem]] — 数据库后端同类
- [[claude-context]] — 互补项目（代码检索 MCP）
- [[event-driven-memory-pipeline]] — Hook → Compress → Index → Inject 范式
- [[hybrid-search-rrf]] — 三流 RRF 方法论
- [[ebbinghaus-forgetting-curve]] — 衰减理论
- [[ai-as-compressor]] — 哲学对照
- [[claude-code]] — 12 hooks 主要消费者
- [[mcp]] — 53 个 tool 的协议基础
