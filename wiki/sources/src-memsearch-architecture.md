---
title: memsearch 架构与设计思路分析
tags: [architecture, agent-memory, llm-infra, zilliz, milvus]
date: 2026-06-07
sources: [memsearch-architecture-analysis.md]
related: [[memsearch]], [[agent-memory]], [[milvus]], [[hybrid-search-rrf]], [[claude-code]], [[claude-context]], [[agent-recall]], [[agentmemory]], [[powermem]]
---

# memsearch 架构与设计思路分析

> 原文：`raw/memsearch-architecture-analysis.md` · 仓库：https://github.com/zilliztech/memsearch · 分析版本 v0.4.6 / HEAD `018a85f`

## 一句话定位

[[memsearch]] 是 Zilliz 出品的跨平台 [[agent-memory]] 系统：[[claude-code]]、Codex、OpenCode、OpenClaw 等平台通过 hook/skill 捕获会话摘要，写入 `.memsearch/memory/*.md`，再把 Markdown chunk 索引到 [[milvus|Milvus]] / Milvus Lite / Zilliz Cloud。

它的关键设计是 Markdown source-of-truth + 可重建 shadow index。查询时走 dense embedding + BM25 sparse + [[hybrid-search-rrf|RRF]]，再用 `expand` 和 transcript anchor 做 search → full section → original transcript 的渐进式回溯。

## 核心架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Platform plugins / skills                                                   │
│ Claude Code hooks │ Codex hooks │ OpenCode plugin │ OpenClaw plugin         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ capture / summarize / recall hint
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Markdown source of truth                                                     │
│ .memsearch/memory/YYYY-MM-DD.md │ .memsearch/PROJECT.md │ .memsearch/USER.md │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ memsearch CLI / watcher / one-shot index
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Python core                                                                  │
│ Scanner → Markdown Chunker → Composite chunk ID → Embedding provider         │
│        → MilvusStore → optional reranker / compact / maintenance             │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ dense vector + BM25 sparse + metadata
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Milvus family                                                                │
│ Milvus Lite local .db │ Milvus Server │ Zilliz Cloud                         │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ search / expand / transcript drill-down
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Agent recall workflow                                                        │
│ L1 search snippets → L2 full markdown section → L3 original transcript       │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 用户入口 | `memsearch index/search/expand/watch/compact/config` 等 CLI 命令 |
| 平台插件 | Claude Code / Codex / OpenCode / OpenClaw hook、skill、transcript parser |
| 编排核心 | `MemSearch` 统一扫描、切块、增量索引、搜索、压缩、watch |
| Markdown 处理 | 发现 Markdown 文件，按 heading/paragraph/line/sentence 切 chunk |
| Embedding 抽象 | OpenAI/Google/Voyage/Jina/Mistral/Ollama/local/ONNX provider protocol |
| 存储检索 | Milvus collection schema、BM25 Function、dense/sparse hybrid search |
| 记忆压缩 | daily memory compact、PROJECT/USER maintenance、prompt templates |
| 配置 | defaults → global config → project config → CLI flags，支持 `env:VAR` |

分层边界是：平台插件负责把宿主会话变成 Markdown 和 anchor；Python core 不理解某个宿主的 transcript 格式，只处理 Markdown → chunks → [[milvus|Milvus]] → search/expand。

## 关键数据流

### 1. 捕获与索引

```
Agent session ends / prompt submitted
        │
        ▼
Platform hook parses transcript and summarizes turn
        │
        ▼
Append markdown block to .memsearch/memory/YYYY-MM-DD.md
        │
        ▼
Scanner finds markdown files
        │
        ▼
Chunker splits by heading, paragraph, line, sentence
        │
        ▼
chunk_id = sha256(markdown:source:start:end:content_hash:model)[0:16]
        │
        ├─ if chunk_id already indexed: skip embedding
        │
        ├─ if old chunk_id missing from file: delete stale record
        │
        ▼
Embed cleaned content, store original content + metadata in Milvus
```

### 2. 语义检索与渐进式回溯

```
User asks a question that needs memory
        │
        ▼
$memory-recall skill runs memsearch search --json-output
        │
        ▼
Query embedding + raw query text
        │
        ├─ dense AnnSearchRequest over embedding
        ├─ BM25 AnnSearchRequest over sparse_vector
        ▼
Milvus hybrid_search + RRFRanker(k=60)
        │
        ▼
L1: snippets with chunk_hash/source/heading/line range
        │
        ▼
memsearch expand <chunk_hash>
        │
        ▼
L2: full heading section from source markdown
        │
        ▼
Optional L3: parse original transcript anchor
```

### 3. 启动注入与长期维护

```
Agent starts in project
        │
        ▼
Plugin resolves project root and collection name
        │
        ├─ first run: install/warm uvx memsearch[onnx]
        ├─ first config: set embedding.provider = onnx
        ├─ Milvus Lite: run one-shot background index
        └─ Milvus Server/Zilliz: start watch singleton
        │
        ▼
Inject short status + "use $memory-recall" hint
        │
        ▼
Maintenance task hashes recent memory markdown
        │
        ├─ unchanged digest: skip
        └─ changed and due: LLM rewrites PROJECT.md / USER.md
```

## 设计决策与哲学

- **Markdown 是 source of truth**：Milvus 只是 shadow index，`compact()` 也把摘要写回 daily Markdown 后再索引，和 [[agent-recall]] 的 SQLite truth model 不同。
- **chunk 主键绑定 model**：主键包含 source、line range、content hash、embedding model；这同时支撑增量索引和模型切换后的索引隔离。
- **检索由 [[milvus|Milvus]] 同时承担 dense 和 BM25**：`content` 通过 analyzer + BM25 Function 生成 sparse vector，再与 dense vector 做 [[hybrid-search-rrf|RRF]]。
- **平台插件和核心解耦**：Codex/Claude/OpenCode/OpenClaw 处理 hook 生命周期和 transcript；core 只处理 Markdown，可跨宿主复用。
- **渐进式上下文控制**：search 返回 L1 片段，`expand` 返回 L2 完整 heading section，必要时再沿 anchor 回到 L3 transcript，和 [[three-tier-search-protocol]] 的目标一致。
- **本地优先但可远端**：插件首次体验偏 ONNX + Milvus Lite；配置同时支持 OpenAI 等 provider、Milvus Server 和 Zilliz Cloud。
- **维护任务偏治理而非事实存储**：PROJECT/USER 摘要按输入 digest 和 interval 更新，事实仍来自 `.memsearch/memory/*.md`。

## 关键组件

`MemSearch` 是核心编排器：扫描 Markdown、切 chunk、计算新旧 chunk 差集、只 embedding 新 chunk、删除 stale chunk。embedding 前会剥掉 HTML comments，避免 session/turn/transcript path 污染向量；但 Milvus 里保留原始 content，方便 `expand` 和 transcript drill-down。

`MilvusStore` 是检索关键：collection 里同时有 `embedding` dense vector、`content` analyzer field、BM25 生成的 `sparse_vector` 和 source/heading/line metadata。搜索时 dense 和 BM25 两路并发请求，再用 RRF 融合。

## 与同类关系

| 维度 | memsearch | [[claude-context]] | [[agent-recall]] | [[agentmemory]] / [[powermem]] |
|------|-----------|--------------------|------------------|--------------------------------|
| 主要对象 | coding agent 会话记忆 Markdown | 代码库语义检索 | MCP-native 实体/关系/观察 | 跨 Agent 记忆服务 / 中间件 |
| source of truth | `.memsearch/*.md` | indexed code files | SQLite | SQLite / OceanBase / service storage |
| 检索 | Milvus dense + BM25 + RRF | Milvus dense/sparse + RRF | SQLite/FTS + scope | BM25/vector/graph 或多路混合 |
| 上下文控制 | search → expand → transcript | code search chunks | briefing cache + open/search | viewer/context injection/tools |

[[memsearch]] 和 [[claude-context]] 都来自 Zilliz，并共享 Milvus hybrid retrieval 的技术路径；区别是 claude-context 解决“当前代码库理解”，memsearch 解决“过去会话记忆”。

## 相关页面

- [[memsearch]]
- [[agent-memory]]
- [[milvus]]
- [[hybrid-search-rrf]]
- [[three-tier-search-protocol]]
- [[claude-code]]
- [[claude-context]]
- [[agent-recall]]
- [[agentmemory]]
- [[powermem]]
