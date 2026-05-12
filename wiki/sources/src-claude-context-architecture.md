---
title: Claude Context 架构深度分析
tags: [mcp, code-rag, claude-code, llm-infra, semantic-search]
date: 2026-05-12
sources: [claude-context-architecture-analysis.md]
related: [[claude-context]], [[mcp]], [[milvus]], [[claude-code]], [[code-semantic-search]], [[hybrid-search-rrf]], [[merkle-dag-fingerprint]], [[ai-agent-plugin-patterns]], [[claude-mem]]
---

# Claude Context 架构深度分析

> 原文：`raw/claude-context-architecture-analysis.md` · 仓库：[zilliztech/claude-context](https://github.com/zilliztech/claude-context) · 分析版本 v0.1.13

## 一句话定位

[[claude-context]] 是 Zilliz 出品的 [[mcp|MCP]] 插件——把整个代码库通过 [[code-semantic-search|语义检索]] "塞进" AI Agent 的上下文，让 [[claude-code]] / Cursor / Gemini CLI / Codex 等 Agent **不必多轮"瞎找"** 就能直达相关代码。

## 解决的核心痛点

| 传统做法 | 问题 | Claude Context 方案 |
|----------|------|---------------------|
| 把整个目录塞进 prompt | Token 爆炸 | 向量库存储，只取 top-K |
| Agent 多轮 grep/read | 慢、消耗工具调用次数 | 一次语义查询直达 |
| 仅靠关键词匹配 | 找不到概念相关代码 | dense + sparse 混合检索 + RRF 重排 |

**一句话**：代码分块 → 向量化 → 存入 [[milvus|Milvus]] → 混合检索 → 通过 MCP 暴露给 AI Agent。

## Monorepo 架构

```
claude-context/
├── packages/
│   ├── core/                 # 引擎层（纯领域逻辑）
│   │   ├── splitter/         # AST / LangChain
│   │   ├── embedding/        # OpenAI/Voyage/Gemini/Ollama
│   │   ├── vectordb/         # Milvus / Milvus-REST
│   │   ├── sync/             # Merkle DAG 增量
│   │   └── context.ts        # 编排器
│   ├── mcp/                  # MCP 协议适配
│   ├── vscode-extension/
│   └── chrome-extension/
```

**三段式分层**：引擎层（core）不感知协议 / 协议层（mcp）只做转换 / 客户端独立 UI。

## 三大核心流程

### 索引（`indexCodebase`）

```
1. loadIgnorePatterns()      .gitignore / .contextignore
2. prepareCollection()       建 Milvus collection（dense + sparse）
3. getCodeFiles()            按扩展名/ignore 规则递归
4. processFileList()         逐文件流式：
     ├─ splitter.split()     AST → 失败 fallback LangChain
     ├─ chunkBuffer 累积到 100
     ├─ embedding.embed() + vectorDB.insert()
     └─ signal?.aborted → IndexAbortError
5. FileSynchronizer.initialize()   Merkle DAG 快照
```

关键常量：`EMBEDDING_BATCH_SIZE=100`、`CHUNK_LIMIT=450000`、`chunkSize=2500/overlap=300`

### 检索（`semanticSearch`）

```
query
  ├─► embedding.embed()   → dense
  └─► 原 query            → sparse
              ↓
   vectorDB.hybridSearch(
     [dense:{nprobe:10}, sparse:{drop_ratio:0.2}],
     rerank:{strategy:'rrf', k:100}
   )
              ↓
   deduplicateResults() → {content, path, lines, score}
```

详见 [[hybrid-search-rrf]]。

### 增量同步（`reindexByChange`）

旧 Merkle root ≠ 新 root → `checkForChanges()` → `{added, removed, modified}` → 删向量 / 重新嵌入 → 新快照写 `~/.context/merkle/<md5>.json`。

详见 [[merkle-dag-fingerprint]]。

## MCP 工具集（4 个）

| 工具 | 作用 |
|------|------|
| `index_codebase` | 全量索引 |
| `search_code` | 自然语言查询 |
| `clear_index` | 清除（带协作式取消） |
| `get_indexing_status` | 进度查询 |

## 关键设计决策

| 设计点 | 理由 |
|--------|------|
| Splitter / Embedding / VectorDB 三层接口 | 多组合，避免锁死 OpenAI |
| AST 优先，LangChain 兜底 | 函数/类边界比固定长度更语义化 |
| Merkle DAG 文件指纹 | 千万行 repo 增量同步 |
| Hybrid Search + RRF | 语义 + 精确符号双覆盖 |
| stdout 强制重定向 stderr | MCP 用 stdout 传 JSON-RPC |
| AbortSignal 协作式取消 | issue #199 后台仍在写"已清空" |
| Snapshot 自愈 | issue #295 客户端误判触发无限重建 |
| `CHUNK_LIMIT = 450000` | Milvus 单 collection 上限保护 |

完整原则汇总：[[ai-agent-plugin-patterns]]。

## 与 claude-mem 的对照

| | [[claude-mem]] | [[claude-context]] |
|---|---|---|
| 目标 | 跨会话**记忆** | 代码库**理解** |
| 数据 | 工具调用日志 → 压缩观察 | 源代码 → AST 分块 |
| 检索 | [[three-tier-search-protocol]] | [[hybrid-search-rrf]] |
| 增量 | 内容哈希去重 | [[merkle-dag-fingerprint]] |
| 集成 | Claude Code Lifecycle Hook | [[mcp|MCP]] 工具 |

两者都是 [[ai-agent-plugin-patterns|AI Agent 外挂]] 模式的优秀样本。

## Git 演进信号

近 30 天高频改动：`core/src/context.ts`（12）、`mcp/src/handlers.ts`（10）、`config.ts`（7）、`sync.ts`（6）。

最近主线：
1. 后台同步可配置化（#314）— `CLAUDE_CONTEXT_BACKGROUND_SYNC` env
2. 取消语义健壮性（#199 / #369）
3. 多 embedding provider（#366 Gemini Embedding 2）
4. 多语言支持（#367 Solidity）
5. 请求级 splitter（#363）

**特征**：接口层稳定，实现层在扩展。典型成熟期开源项目。

## 配置示例（Claude Code）

```bash
claude mcp add claude-context \
  -e OPENAI_API_KEY=sk-xxx \
  -e MILVUS_ADDRESS=your-zilliz-endpoint \
  -e MILVUS_TOKEN=your-zilliz-key \
  -- npx @zilliz/claude-context-mcp@latest
```
