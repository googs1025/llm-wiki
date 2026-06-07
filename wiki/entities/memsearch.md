---
title: memsearch
tags: [agent-memory, ai-agent, llm-infra, zilliz, milvus, open-source]
date: 2026-06-07
sources: [src-memsearch-architecture]
related: [[agent-memory]], [[milvus]], [[hybrid-search-rrf]], [[claude-code]], [[claude-context]], [[agent-recall]], [[agentmemory]], [[powermem]]
---

# memsearch

memsearch 是 Zilliz 开源的跨平台 [[agent-memory]] 系统（仓库 `zilliztech/memsearch`，分析版本 v0.4.6 / HEAD `018a85f`）。它面向 [[claude-code]]、Codex、OpenCode、OpenClaw 等 coding agents，把会话摘要保存成 `.memsearch/memory/*.md`，并用 [[milvus|Milvus]] 做可重建的 hybrid search index。

## 解决什么

coding agent 的长期记忆通常卡在两个问题：一是不同宿主的 hook/transcript 格式不一致，二是历史上下文不能每次全量注入。memsearch 的答案是：宿主插件负责 capture，Python core 负责 Markdown index，Agent 需要时显式调用 memory-recall 做渐进式检索。

## 核心特征

- **Markdown source-of-truth**：daily memory、project summary、user profile 都是 `.md` 文件，Milvus 只是 shadow index。
- **跨平台插件**：支持 Claude Code、Codex、OpenCode、OpenClaw，各平台有独立 hooks、skills、transcript parser。
- **Milvus hybrid retrieval**：dense embedding + BM25 sparse + RRF，详见 [[hybrid-search-rrf]]。
- **渐进式 recall**：L1 search snippet → L2 `memsearch expand` full section → L3 transcript anchor。
- **本地优先**：插件默认路径偏 `memsearch[onnx]` + Milvus Lite，也可切 OpenAI/Google/Voyage/Jina/Mistral/Ollama/local 等 embedding provider。
- **记忆治理**：maintenance task 可按 digest/interval 维护 `.memsearch/PROJECT.md` 和 `.memsearch/USER.md`。

## 架构骨架

| 层 | 组件 | 职责 |
|----|------|------|
| 插件层 | `plugins/{claude-code,codex,opencode,openclaw}` | 捕获对话、写 Markdown、注入 recall 提示 |
| CLI/API | `memsearch index/search/expand/watch/compact/config` | 用户和插件统一入口 |
| Core | `MemSearch` | 扫描、切块、增量索引、搜索、压缩 |
| Storage | `MilvusStore` | schema、dense/BM25 hybrid search、metadata query |
| Config | `config.py` | defaults/global/project/CLI override 与 `env:VAR` |

完整分析见 [[src-memsearch-architecture]]。

## 与同类关系

memsearch 与 [[claude-context]] 同属 Zilliz 生态，并共享 [[milvus|Milvus]] hybrid retrieval，但 claude-context 主要索引代码库，memsearch 主要索引会话记忆。

与 [[agent-recall]] 相比，memsearch 更偏 Markdown journal + semantic recall；agent-recall 更偏 [[mcp]] tools + SQLite scoped facts。与 [[agentmemory]] / [[powermem]] 相比，memsearch 更轻量、更贴近个人 coding agent hook 工作流。

## 相关页面

- [[src-memsearch-architecture]]
- [[agent-memory]]
- [[milvus]]
- [[hybrid-search-rrf]]
- [[three-tier-search-protocol]]
- [[claude-code]]
- [[claude-context]]
- [[agent-recall]]
- [[agentmemory]]
- [[powermem]]
