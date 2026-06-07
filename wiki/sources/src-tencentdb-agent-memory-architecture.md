---
title: TencentDB-Agent-Memory 架构与设计思路分析
tags: [architecture, agent-memory, llm-infra, openclaw, tencent-cloud]
date: 2026-06-07
sources: [tencentdb-agent-memory-architecture-analysis.md]
related: [[tencentdb-agent-memory]], [[agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[hybrid-search-rrf]], [[ai-as-compressor]], [[agentmemory]], [[memsearch]], [[powermem]]
---

# TencentDB-Agent-Memory 架构与设计思路分析

> 原文：`raw/tencentdb-agent-memory-architecture-analysis.md` · 仓库：https://github.com/TencentCloud/TencentDB-Agent-Memory · 分析版本 v0.3.6 / HEAD `f92b102`

## 一句话定位

[[tencentdb-agent-memory]] 是腾讯云出品的 OpenClaw / Hermes Agent 记忆插件，npm 包名 `@tencentdb-agent-memory/memory-tencentdb`。它把长期记忆做成 L0 Conversation → L1 Atom → L2 Scenario → L3 Persona 的分层语义金字塔，同时把短期长任务日志做 context offload，压缩成可回溯的 Mermaid 符号画布。

它和普通“向量库里塞历史”的差别在于：底层保留证据，中层建立结构，高层注入可读画像/场景导航；召回时既能自动注入 L1/L2/L3，也能让 Agent 调 `tdai_memory_search` / `tdai_conversation_search` 主动下钻。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Host surfaces                                                                 │
│ OpenClaw plugin hooks/tools │ Hermes Python provider │ Standalone HTTP Gateway │
└──────────────────────────────┬───────────────────────────────────────────────┘
                               │ HostAdapter + LLMRunnerFactory
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ TdaiCore host-neutral facade                                                  │
│ handleBeforeRecall │ handleTurnCommitted │ searchMemories │ searchConversations│
└──────────────┬─────────────────────┬─────────────────────┬───────────────────┘
               │                     │                     │
               ▼                     ▼                     ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────────┐
│ Recall path           │  │ Capture / pipeline    │  │ Store abstraction         │
│ L1 hybrid search      │  │ L0 record + checkpoint│  │ SQLite + sqlite-vec + FTS5 │
│ L2 scene navigation   │  │ L1 extraction         │  │ Tencent Cloud VectorDB     │
│ L3 persona injection  │  │ L2 scene blocks       │  │ BM25 sparse + dense vector │
└──────────┬───────────┘  │ L3 persona            │  └─────────────┬────────────┘
           │              └──────────┬───────────┘                │
           ▼                         ▼                            ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Persistent artifacts                                                          │
│ conversations/*.jsonl │ records/*.jsonl │ scene_blocks/*.md │ persona.md      │
│ vectors.db / TCVDB collections │ refs/*.md / mmds/*.mmd for context offload    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| OpenClaw 插件入口 | 解析配置、注册工具、挂载 auto-recall / auto-capture / shutdown hook |
| Host-neutral core | 用 `HostAdapter` / `LLMRunnerFactory` 抹平 OpenClaw、Hermes、Gateway 差异 |
| L0 捕获 | 原子游标捕获新消息，写 conversations JSONL，并可写 L0 向量索引 |
| L1 结构化记忆 | LLM 从 L0 提取 persona/episodic/instruction 记忆，去重/合并后写 records 和 store |
| L2 场景块 | 工具型 LLM 在 `scene_blocks/` 沙箱内维护场景 Markdown、索引和导航 |
| L3 用户画像 | 根据变更场景增量生成 `persona.md`，并附加 scene navigation |
| Pipeline 调度 | L1 阈值/idle/warmup，L2 downward-only timer，L3 全局串行队列 |
| 检索与存储 | SQLite / TCVDB 后端抽象，FTS/BM25/vector/hybrid search |
| Context offload | 工具日志卸载、Mermaid 画布、L3 压缩、MMD 注入和 token 预算控制 |
| Hermes / Gateway | Node HTTP sidecar 暴露 TDAI Core；Python provider 管理 sidecar 生命周期 |

## 关键数据流

### 1. OpenClaw 自动召回与捕获

```
OpenClaw before_prompt_build
        │
        ▼
index.ts caches original prompt and calls TdaiCore.handleBeforeRecall()
        │
        ▼
auto-recall sanitizes user text
        │
        ├─ L1: keyword / embedding / hybrid search
        ├─ L2: read scene index and build scene navigation
        └─ L3: read persona.md
        │
        ▼
Return prependContext + appendSystemContext
        │
        ▼
OpenClaw agent runs with injected memory
        │
        ▼
OpenClaw agent_end
        │
        ▼
TdaiCore.handleTurnCommitted()
        │
        ├─ checkpoint.captureAtomically() records only new messages
        ├─ write L0 JSONL and optional L0 vector rows
        └─ notify MemoryPipelineManager
```

### 2. L0→L1→L2→L3 长期记忆管线

```
L0 raw messages captured
        │
        ▼
MemoryPipelineManager.notifyConversation(sessionKey)
        │
        ├─ threshold path: conversation_count >= warmup/everyN
        ├─ idle path: l1Idle timer fires
        └─ flush path: shutdown / session end
        │
        ▼
L1 Runner
        │
        ├─ read L0 from VectorStore or JSONL fallback
        ├─ LLM scene segmentation + memory extraction
        ├─ batch dedup / update / merge / skip
        └─ write records/YYYY-MM-DD.jsonl + store rows
        │
        ▼
L2 Runner
        │
        ├─ read changed L1 records
        ├─ LLM edits scene_blocks/*.md inside sandbox
        ├─ normalize filenames / sync scene_index
        └─ optional persona update signal
        │
        ▼
L3 Runner
        │
        ├─ read changed scene blocks
        ├─ LLM writes persona.md
        └─ append fresh scene navigation
```

### 3. 存储与检索策略

```
Config storeBackend
        │
        ├─ sqlite
        │    ├─ vectors.db
        │    ├─ L1 records + vec0 + FTS5
        │    ├─ L0 conversations + vec0 + FTS5
        │    └─ client-side hybrid = FTS5 + embedding + RRF
        │
        └─ tcvdb
             ├─ l1_memories collection
             ├─ l0_conversations collection
             ├─ profiles collection
             ├─ server-side dense embedding
             ├─ client-side BM25 sparse vector
             └─ native hybridSearch + RRFRerank
```

### 4. Context offload 短期记忆

```
after_tool_call captures heavy tool result
        │
        ▼
Write raw refs/*.md and offload entries
        │
        ▼
L1 summarizes tool pairs
        │
        ▼
L1.5 judges task boundary / active MMD
        │
        ▼
L2 updates Mermaid task canvas with node_id mapping
        │
        ▼
before_prompt_build / contextEngine assemble
        │
        ├─ mild compression: replace old tool results with summaries
        ├─ aggressive compression: delete/compress until below threshold
        ├─ emergency fallback: truncate oversized messages
        └─ inject active/history MMD within token budget
```

## 设计决策与哲学

- **宿主中立 core**：OpenClaw in-process 插件和 Hermes sidecar 都走同一个 `TdaiCore`，这和 [[event-driven-memory-pipeline]] 的“采集层/处理层分离”一致。
- **长期记忆是分层金字塔**：L0 保留原始对话，L1 提取 atom，L2 归纳 scenario，L3 生成 persona，避免把历史平铺成无结构向量堆。
- **动态/稳定上下文分离**：L1 recall 走 `prependContext`，L2/L3/工具指南走 `appendSystemContext`，降低 prompt cache 被动态片段击穿的概率。
- **JSONL 和 store 各司其职**：records JSONL 是 append-only 备份/恢复材料，SQLite/TCVDB 是检索引擎。
- **混合检索可本地可云端**：SQLite 路径用 FTS5 + embedding + RRF；TCVDB 路径用 server-side embedding + BM25 sparse + native hybridSearch，属于 [[hybrid-search-rrf]] 的工程化变体。
- **offload 保留可追溯性**：原始工具日志放 `refs/*.md`，上下文里只保留 Mermaid MMD 和 node_id，符合 [[three-tier-search-protocol]] 的“先高层、再下钻”思想。

## 关键组件

`TdaiCore` 是项目核心 facade：`handleBeforeRecall()`、`handleTurnCommitted()`、`searchMemories()`、`searchConversations()` 给所有宿主复用。它内部用 promise gate 防 scheduler start 并发竞态，并在 shutdown 前 drain 后台 L0 embedding 任务。

`MemoryPipelineManager` 是长期记忆节奏控制器：L1 有 threshold / idle / flush 三条触发路径，warmup 从 1→2→4 逐步放缓；L2 用 downward-only timer；L3 是全局串行队列，避免画像生成并发改写。

## 与同类关系

| 维度 | TencentDB-Agent-Memory | [[agentmemory]] | [[memsearch]] | [[powermem]] |
|------|------------------------|-----------------|---------------|--------------|
| 主形态 | OpenClaw 插件 + Hermes sidecar | 跨 Agent worker / MCP / REST | 多平台 coding agent memory CLI/plugin | 记忆中间件 / SDK / API / MCP |
| 长期记忆层次 | L0→L1→L2→L3 | 多层记忆 + graph/vector/BM25 | Markdown memory + Milvus shadow index | working/short/long + 衰减 |
| 短期上下文 | Context offload + Mermaid MMD | context injection 可配置 | search/expand/transcript | 偏长期记忆和应用层 |
| 存储 | SQLite + sqlite-vec/FTS5 或 TCVDB | SQLite | Markdown + Milvus | OceanBase / SeekDB |

这个项目最有辨识度的地方是把“长期个性化记忆”和“短期任务上下文卸载”合并到同一个插件，而不是只做 recall。

## 相关页面

- [[tencentdb-agent-memory]]
- [[agent-memory]]
- [[event-driven-memory-pipeline]]
- [[three-tier-search-protocol]]
- [[hybrid-search-rrf]]
- [[ai-as-compressor]]
- [[agentmemory]]
- [[memsearch]]
- [[powermem]]
