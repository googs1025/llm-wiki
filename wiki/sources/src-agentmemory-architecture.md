---
title: agentmemory 架构与设计思路分析
tags: [architecture, ai-agent, agent-memory, hybrid-search, mcp]
date: 2026-05-21
sources: [agentmemory-architecture-analysis.md]
related: [[agentmemory], [[claude-code]], [[mcp]], [[claude-mem]], [[powermem]], [[agent-memory]], [[hybrid-search-rrf]], [[event-driven-memory-pipeline]], [[ebbinghaus-forgetting-curve]], [[ai-as-compressor]]]
---

# agentmemory 架构与设计思路分析

> 原文：`raw/agentmemory-architecture-analysis.md` · 仓库：https://github.com/rohitg00/agentmemory · 分析版本 v0.9.21

## 一句话定位

[[agentmemory]] 是为 AI 编码 Agent（[[claude-code]] / Codex / Cursor / Gemini CLI / Hermes / OpenClaw / pi / OpenCode 及任何 [[mcp]] 客户端）提供**持久跨会话记忆**的本地服务：通过 Hook 抓取工具调用（[[event-driven-memory-pipeline]]） → 零 LLM 启发式压缩（[[ai-as-compressor]] 的反向取舍）→ 三流混合检索（BM25 + Vector + Knowledge Graph，[[hybrid-search-rrf]]）→ MCP / REST / 12 个 Hook 把上下文回注 Agent。所有客户端共用同一个 `:3111` worker，状态落在 iii-engine 托管的 SQLite。

## 核心架构图

```
                          ┌─────────────────────────────────────────────┐
                          │            AI 编码 Agent (任何 MCP 客户端)   │
                          │  Claude Code · Codex · Cursor · Gemini · pi │
                          └──────┬───────────┬───────────┬──────────────┘
                                 │ hooks     │ MCP       │ REST
                                 │ (POST)    │ (stdio)   │
                                 ▼           ▼           ▼
            ┌──────────────────────────────────────────────────────────────┐
            │           agentmemory worker (Node ESM, src/index.ts)         │
            │                                                              │
            │  ┌──── 触发层 (src/triggers/, src/mcp/) ──────────────────┐   │
            │  │  HTTP: 124 REST endpoints  /agentmemory/*  (:3111)    │   │
            │  │  MCP:  53 tools (8 default)  via mcp::tools::call     │   │
            │  │  WS:   live stream (viewer)                  (:3113)  │   │
            │  └──────────────────────────────┬─────────────────────────┘   │
            │                                 │                            │
            │  ┌──── 业务函数层 (src/functions/, ~60 个 mem::*) ────────┐   │
            │  │  Ingest:  observe · compress(-synthetic) · enrich     │   │
            │  │  Recall:  search · smart-search · context · timeline  │   │
            │  │  Persist: remember · evict · auto-forget · retention  │   │
            │  │  Tiers:   summarize → consolidate → semantic/procedural│  │
            │  │  Graph:   graph · graph-retrieval · temporal-graph    │   │
            │  │  Orch:    actions · routines · leases · signals ·     │   │
            │  │           checkpoints · sentinels · crystallize       │   │
            │  └──────────────────────────────┬─────────────────────────┘   │
            │                                 │                            │
            │  ┌──── 状态层 (src/state/) ─────┴─────────────────────────┐   │
            │  │  StateKV (iii-sdk WS → SQLite)  ──────────────────┐    │   │
            │  │  SearchIndex (BM25 + stemmer + synonyms + CJK)    │    │   │
            │  │  VectorIndex (Float32Array cosine, in-memory)     │    │   │
            │  │  HybridSearch (BM25 · Vector · Graph RRF + rerank)│    │   │
            │  │  IndexPersistence (periodic flush to KV)          │    │   │
            │  └────────────────────────────────────────────────────────┘   │
            │                                 │                            │
            │  ┌──── Provider 层 (src/providers/) ──────────────────────┐   │
            │  │  LLM:        OpenAI · Anthropic · Minimax · OpenRouter│   │
            │  │  Embedding:  OpenAI · Voyage · Xenova(local) · noop   │   │
            │  │  Wrapper:    fallback-chain + circuit-breaker + resilient │
            │  └────────────────────────────────────────────────────────┘   │
            └────────────────────────┬─────────────────────────────────────┘
                                     │ WebSocket (ws://localhost:49134)
                                     ▼
                          ┌─────────────────────────┐
                          │   iii-engine (v0.11.2)  │
                          │   StateModule → SQLite  │
                          │   ./data/state_store.db │
                          └─────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 引导层 | 加载 config、连接 iii-engine、串起 50+ 函数注册、启动 viewer、安装定时器、绑定信号 |
| 触发层 | 124 REST endpoints + 53 MCP tools + 事件触发；所有都走 `sdk.registerFunction` + `sdk.registerTrigger({type:"http"})` |
| 业务函数层 | ~60 个 `mem::xxx` 函数：observe / compress / search / remember / consolidate / graph / lessons / crystallize / … |
| 状态层 | KV scope（32+ 类记忆命名空间） + BM25 倒排表 + Vector cosine + Hybrid RRF + 周期持久化 + 重排器 |
| Provider 层 | LLM 与嵌入抽象，带 fallback 链、断路器、resilient 包装 |
| Hooks（独立脚本） | Claude Code 生命周期 Hook 脚本，**不导入 iii-sdk**，stdin 读 JSON → fetch POST → AbortSignal.timeout |
| Viewer | 实时 WebSocket UI（`mem-live` stream），默认 `:3113` |
| CLI | `agentmemory` / `agentmemory demo` / `agentmemory connect <agent>`；含 iii-engine 自动安装与版本钉定 |
| Plugin | 各 Agent 的原生插件清单（hooks + skills + MCP 接入） |
| Evals | LongMemEval / Coding-Life 评测脚本 + 内部 metrics-store + self-correct + validator |

关键约束（源自 `AGENTS.md`）：

- **iii-engine 是强制总线**：所有函数注册都走 `sdk.registerFunction` / `sdk.trigger`，禁止绕过 iii-sdk 用独立 SQLite 或进程内替代方案。
- **REST endpoint 必须白名单字段**：不要把 `req.body` 原样塞给 `sdk.trigger`，要显式挑字段。
- **MCP tool 增删要同步 7 处**：tools-registry / server switch / triggers/api / index 注册 + 计数 / 测试 / README / plugin.json。这是高维护成本耦合点。
- **Hook 脚本不依赖 iii-sdk**：保持轻量，AbortSignal.timeout 包裹 fetch，任何错误必须吞掉，不能阻塞 Agent。

## 关键数据流

### Ingest（写路径）

```
Claude Code 工具调用
        │
        ▼
src/hooks/post-tool-use.ts  (standalone Node, AbortSignal.timeout)
        │  HTTP POST /agentmemory/observe
        ▼
src/triggers/api.ts  ──► sdk.trigger({function_id: "mem::observe"})
        │
        ▼
src/functions/observe.ts:registerObserveFunction
  ├─ 验证 payload (sessionId / hookType / timestamp)
  ├─ DedupMap.isDuplicate()    ← 内存级去重（短时间窗内同 toolName+toolInput）
  ├─ stripPrivateData()        ← 自动脱敏 (PII / 密钥)
  ├─ extractImage()            ← 多模态：识别 data:image / iVBORw0KGgo / /9j/
  └─ kv.set(KV.observations(sessionId), RawObservation)
        │
        ▼
buildSyntheticCompression()   ← 零 LLM 启发式（默认，issue #138）
       OR  : compressFunction()                ← LLM 压缩（AGENTMEMORY_AUTO_COMPRESS=true）
        │
        ▼
CompressedObservation { id, title, facts[], narrative, concepts[], files[], importance }
        │
        ▼
SearchIndex.add()  (BM25, 内存倒排表 + termFreq + IDF)
        +
VectorIndex.add()  (Float32Array, cosine, embedding 异步获取)
        │
        ▼
WebSocket stream  →  Viewer (mem-live group)
        │
        ▼
[周期] IndexPersistence 把 BM25 + Vector 序列化回 KV
```

### Recall（读路径）

```
query (string)
  │
  ▼
QueryExpansion         ← reformulations + temporalConcretizations + entityExtractions
  │
  ▼
HybridSearch.tripleStreamSearch()  (src/state/hybrid-search.ts:77)
  │
  ├─►  BM25     SearchIndex.search(query, 2N)
  │             stemmer + synonyms + CJK segmenter
  │
  ├─►  Vector   embeddingProvider.embed(query) → VectorIndex.search()
  │             Float32Array 暴力扫表 + cosineSimilarity
  │
  └─►  Graph    extractEntitiesFromQuery() → GraphRetrieval.searchByEntities(depth=2)
                LLM 离线抽取 entity/edge, 在线只做 BFS
  │
  ▼
RRF 融合（K=60，w_bm25=0.4, w_vec=0.6, w_graph=0.3）
  │
  ▼
[可选] Reranker  (RERANK_ENABLED=true) → src/state/reranker.ts
  │
  ▼
Token-budget trim
  │
  ▼
返回给 Agent（format = full / compact / narrative）
```

### Boot 启动序列

```
loadConfig + provider + embeddingProvider
    │
    ▼
registerWorker(engineUrl)  ──── WebSocket ─────► iii-engine :49134
    │                                                 │
    │  invocationTimeoutMs: 180s（src/index.ts:168）   │
    │  telemetry { project_name: "agentmemory", ... } │
    ▼
new StateKV(sdk) + new MetricsStore + new DedupMap + new VectorIndex
    │
    ▼
register* (50+ 业务函数, src/index.ts:204-303)
    │   privacy / observe / compress / search / context / summarize /
    │   migrate / file-index / consolidate / patterns / remember / evict /
    │   relations / timeline / profile / auto-forget / export-import / enrich /
    │   claude-bridge? / graph? / consolidation-pipeline / team? / governance /
    │   actions / frontier / leases / routines / signals / checkpoints / mesh /
    │   branch-aware / flow-compress / sentinels / sketches / crystallize /
    │   diagnostics / facets / verify / lessons / obsidian-export / reflect /
    │   working-memory / skill-extract / cascade / sliding-window /
    │   query-expansion / temporal-graph / retention / compress-file / replay
    ▼
HybridSearch 装配 (bm25Index + vectorIndex + embeddingProvider + kv + 权重)
    │
    ▼
registerApiTriggers + registerEventTriggers + registerMcpEndpoints
    │
    ▼
indexPersistence.load()
    ├─ 恢复 BM25 索引（如有）→ bm25Index.restoreFrom()
    └─ 恢复 Vector 索引
       ├─ validateDimensions(activeDim)
       ├─ mismatch != 0 ?
       │   ├─ AGENTMEMORY_DROP_STALE_INDEX=true  → 丢弃并 console.warn
       │   └─ 否则                                 → throw Error（拒绝启动）
       └─ vectorIndex.restoreFrom()
    │
    ▼
needsRebuild ? void rebuildIndex(kv)  ← fire-and-forget, 可能数小时
            : backfill BM25 from KV.memories (legacy gap before #257)
    │
    ▼
bootLog "Ready. Triple-stream (BM25+Vector+Graph) search active."
    │
    ▼
startViewerServer(restPort + 2, kv, sdk, secret, restPort)
    │
    ▼
后台定时器（全部 .unref()）：
    auto-forget          每 3,600,000ms (1h)
    lesson-decay-sweep   每 86,400,000ms (24h)
    insight-decay-sweep  每 86,400,000ms (24h)
    consolidate-pipeline 每 7,200,000ms (2h)
    │
    ▼
process.on("SIGINT" | "SIGTERM", shutdown)
    healthMonitor.stop + dedupMap.stop + indexPersistence.stop
    viewerServer.close → indexPersistence.save → sdk.shutdown → exit(0)
```

补充说明：
- **超时**：iii-sdk invocationTimeoutMs=180s（src/index.ts:168）。在写压力下 `state::set` 偶尔超过 30s 默认值（issue #204）。
- **错误传递**：顶层 `process.on("unhandledRejection")` 60s 节流后日志，不让一次 timeout 杀掉长生命周期 worker。
- **回退路径**：embedding provider 缺失时退化为 BM25-only；vector 索引 search 失败 fallthrough 到 BM25-only；graph 检索失败被 best-effort try/catch 吞掉。

## 设计决策与哲学

- **iii-engine 作为强制总线**：所有 50+ 业务函数都走 `sdk.registerFunction` / `sdk.trigger`，不允许绕过。代价是引入外部 iii-engine 进程依赖（钉到 v0.11.2，因为 v0.11.6 sandbox 模型不兼容当前 worker）；收益是统一审计、WebSocket 重放、远端代理可能性。这与 [[claude-mem]] 的"进程内 chroma + bullmq"形成鲜明对比——agentmemory 把"消息总线"外置，[[claude-mem]] 把它内置。
- **三流混合检索 + RRF**：BM25 抓字面（文件名/命令）、Vector 抓语义、Graph 抓实体关系；RRF (K=60) 比加权求和更鲁棒。设计上与 [[powermem]] 的"向量+全文+稀疏+图四路"接近，但 agentmemory 没有稀疏第四路、用 SQLite + 内存索引替代 OceanBase。参见 [[hybrid-search-rrf]]。
- **零 LLM 压缩为默认**（issue #138）：`buildSyntheticCompression()` 用 toolName 启发式推断 ObservationType + 正则抽 files。理由：默认开启 LLM 压缩 = 用户 API key 按工具调用频率持续烧 token。`AGENTMEMORY_AUTO_COMPRESS=true` 才进 LLM 路径。这是对 [[ai-as-compressor]] 的反向取舍——"AI 是好压缩器但成本不可见"。
- **Context injection 默认关**（issue #143）：Hook 只抓不注入。"自动塞 4000 字记忆进 Claude" 对 Claude Pro 用户是 token 杀手——所以默认关，要 `AGENTMEMORY_INJECT_CONTEXT=true` 显式开启。这是项目对"成本可见性"的执着。
- **向量维度守卫**：持久化 vector index 维度与当前 embedding provider 不匹配时**拒绝启动**而不是 silently 让 cosineSimilarity 跨维度永远返回 0。可通过 `AGENTMEMORY_DROP_STALE_INDEX=true` 显式丢弃旧索引。"宁愿失败也不要静默错误"。
- **In-process BM25 + Vector**：不依赖 Postgres / pgvector / Qdrant；BM25 用 Map<term, Set<obsId>> 倒排表 + termCount，Vector 用 Map<obsId, Float32Array> 暴力扫表 + cosine。极简实现，5 万条以内体感无延迟；超过此规模需替换为 ANN（HNSW / FAISS / pgvector）。
- **多层记忆模型 + 强度衰减**：32+ KV scope（episodic / working / semantic / procedural / graph / orchestration / lessons / insights / crystals / sketches / sentinels / routines / leases / signals / checkpoints / facets / ...）。`applyDecay()` 用 `strength * 0.9^periods` 指数衰减，配合 auto-forget (1h)、lesson-decay-sweep (24h)、consolidation (2h) 形成 Ebbinghaus 风格的"主动遗忘"机制——参见 [[ebbinghaus-forgetting-curve]]，与 [[powermem]] working/short/long 三层定时调度同构。
- **Hooks 与 SDK 解耦**：Hook 脚本是 standalone Node，**不导入 iii-sdk**，只走 HTTP；`AbortSignal.timeout()` 包裹 fetch，全 try/catch 吞错。设计目标：Hook 失败绝不能阻塞 Agent 工具调用。这与 [[claude-mem]] 的 hook 方式如出一辙——都是 [[event-driven-memory-pipeline]] 的最佳实践沉淀。
- **MCP "默认 8 / 全量 53" 双轨**：53 个 MCP tools 是完整能力面，但默认只暴露 8 个核心工具（recall / save / compress_file / 等）给 Agent，避免选项过多让模型迷失；`AGENTMEMORY_TOOLS=all` 全量暴露给高级用户。
- **fire-and-forget rebuild**：首次启动若索引为空，`rebuildIndex` 可能耗时数小时（每条 observation 一次 embedding 调用，受云端速率限制），所以**绝不 await**——不阻塞 viewer 端口绑定与服务可用。索引边用边补，搜索质量随时间收敛。

## 关键组件深入解读

### `src/state/hybrid-search.ts` — 检索核心

`HybridSearch.tripleStreamSearch(query, limit, entityHints?)` 三流并行：BM25 同步取 `limit * 2`；Vector 异步 `embed(query)` 失败则降级 BM25-only；Graph 用 `extractEntitiesFromQuery` 或传入 `entityHints`，BFS 深度 2。顶 5 个 vector 结果做 "expansion search"（用 obsId 做相似度扩散，找邻居）。`searchWithExpansion(query, limit, expansion)` 把 query reformulations × 三流并行做 `Promise.all`，再用 `combinedScore` 去重最大值。

### `src/state/schema.ts` — KV scope 总线

`KV` 是 `const` 对象，既有固定 key（`mem:sessions` / `mem:memories` / `mem:audit`）又有函数形式（`observations(sessionId)` / `teamShared(teamId)` / `embeddings(obsId)`）。这种"函数化 key"模式让一个 KV scope 能横向分片到 sessionId / teamId / userId，避免单 scope 无限增长。`generateId(prefix)` 用 `ts.toString(36) + uuid.slice(0,12)` 生成时间排序友好的 ID；`fingerprintId(prefix, content)` 用 sha256 前 16 字符做内容寻址（content-addressable dedup）；`jaccardSimilarity()` 给 dedup 提供回退方案。

## 相关页面

- [[agentmemory]] — 项目实体页（这是该实体的源摘要）
- [[claude-mem]] — 同类项目（专一 Claude Code，进程内 chroma + bullmq）
- [[powermem]] — 同类项目（OceanBase 后端，四路检索 + Ebbinghaus）
- [[claude-context]] — 互补项目（代码语义检索 MCP）
- [[claude-code]] — 12 个 Hook 集成的主要 Agent
- [[mcp]] — 53 个 MCP tool 的协议基础
- [[hybrid-search-rrf]] — 三流 RRF 检索方法论
- [[event-driven-memory-pipeline]] — Hook → Compress → Index → Inject 闭环
- [[ebbinghaus-forgetting-curve]] — 强度衰减 + 周期 sweep 的理论基础
- [[ai-as-compressor]] — 与 agentmemory 默认零 LLM 压缩的取舍对照
- [[agent-memory]] — Agent 长期记忆领域综述
