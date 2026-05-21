# agentmemory 架构与设计思路分析

> 仓库：https://github.com/rohitg00/agentmemory · 分析日期：2026-05-21 · 版本：v0.9.21

## 一句话定位

agentmemory 是为 AI 编码 Agent（Claude Code / Codex / Cursor / Gemini CLI / Hermes / OpenClaw / pi / OpenCode 及任何 MCP 客户端）提供**持久跨会话记忆**的本地服务：通过 Hook 抓取工具调用 → 零 LLM 启发式压缩 → 三流混合检索（BM25 + Vector + Knowledge Graph）→ MCP / REST / 12 个 Hook 把上下文回注 Agent。所有客户端共用同一个 `:3111` worker，状态落在 iii-engine 托管的 SQLite。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 引导层 | `src/index.ts` / `src/cli.ts` | 加载 config、连接 iii-engine、串起 50+ 函数注册、启动 viewer、安装定时器、绑定 SIGINT/SIGTERM |
| 触发层 | `src/triggers/api.ts` · `src/triggers/events.ts` · `src/mcp/server.ts` · `src/mcp/tools-registry.ts` | 124 REST endpoints + 53 MCP tools + 事件触发，所有都走 `sdk.registerFunction` + `sdk.registerTrigger({type:"http"})` |
| 业务函数层 | `src/functions/*.ts`（~60 文件） | 每个文件一组 `mem::xxx` 函数：observe/compress/search/remember/consolidate/graph/lessons/crystallize/… |
| 状态层 | `src/state/{kv,schema,search-index,vector-index,hybrid-search,index-persistence,keyed-mutex,reranker,stemmer,synonyms,cjk-segmenter,memory-utils}.ts` | KV scope 定义 + BM25 + Vector + Hybrid RRF + 周期持久化 + 重排器 |
| Provider 层 | `src/providers/{openai,anthropic,minimax,openrouter,noop,fallback-chain,circuit-breaker,resilient}.ts` + `src/providers/embedding/` | LLM 与嵌入抽象，带 fallback 链、断路器、resilient 包装 |
| Hooks（独立脚本） | `src/hooks/{post-tool-use,pre-tool-use,session-start,session-end,prompt-submit,stop,subagent-start,subagent-stop,task-completed,notification,pre-compact,post-commit,sdk-guard}.ts` | Claude Code 生命周期 Hook 脚本，**不导入 iii-sdk**，stdin 读 JSON → fetch POST → AbortSignal.timeout |
| Viewer | `src/viewer/{server,document}.ts` + `index.html` | 实时 WebSocket UI（`mem-live` stream），默认 `:3113` |
| CLI | `src/cli.ts` · `src/cli/{connect,onboarding,doctor-diagnostics,remove-plan,splash,preferences}.ts` | `agentmemory` / `agentmemory demo` / `agentmemory connect <agent>`，含 npm 全局/npx 路径处理与 iii-engine 自动安装 |
| Plugin | `plugin/.claude-plugin/plugin.json` · `plugin/.codex-plugin/plugin.json` · `plugin/opencode/` | 各 Agent 的原生插件清单（hooks + skills + MCP 接入） |
| Evals | `eval/`、`benchmark/`、`src/eval/` | LongMemEval / Coding-Life 评测脚本 + 内部 metrics-store + self-correct + validator |

分层关键约束（来自 `AGENTS.md`）：

- **iii-engine 是强制总线**：所有函数注册都走 `sdk.registerFunction` / `sdk.trigger`，禁止绕过 iii-sdk 用独立 SQLite 或进程内替代方案。
- **REST endpoint 必须白名单字段**：不要把 `req.body` 原样塞给 `sdk.trigger`，要显式挑选字段。
- **MCP tool 增删要同步 7 处**：`tools-registry.ts` / `mcp/server.ts` switch / `triggers/api.ts` REST / `index.ts` 注册 + 计数 / `test/mcp-standalone.test.ts` / `README.md` / `plugin/.claude-plugin/plugin.json`。这是公开维护成本。
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

### Recall（读路径，`memory_recall` MCP / `/agentmemory/search` REST）

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

### Boot 启动序列（src/index.ts:131-555）

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
- **错误传递**：顶层 `process.on("unhandledRejection")` 60s 节流后日志（src/index.ts:120-129），不让一次 timeout 杀掉长生命周期 worker。
- **回退路径**：embedding provider 缺失时退化为 BM25-only；vector 索引 search 失败 fallthrough 到 BM25-only；graph 检索失败被 best-effort try/catch 吞掉。

## 设计决策与哲学

- **iii-engine 作为强制总线**（`AGENTS.md` + `src/index.ts:166`）：所有 50+ 业务函数都走 `sdk.registerFunction` / `sdk.trigger`，不允许绕过。代价是引入外部 iii-engine 进程依赖（`src/cli.ts:74` 钉到 v0.11.2，因为 v0.11.6 的 `iii worker add` sandbox 模型与当前 worker 模型不兼容）。收益是统一审计 / WebSocket 重放 / 远端代理。

- **三流混合检索 + RRF**（`src/state/hybrid-search.ts:22-115`）：BM25 抓字面（文件名 / 命令）、Vector 抓语义、Graph 抓实体关系；RRF (K=60) 比加权求和更鲁棒——单流极值不会主导，每流贡献由排名决定。可选 Reranker 在融合后再校准。

- **零 LLM 压缩为默认**（`src/functions/compress-synthetic.ts:12-42` + `src/index.ts:246-253`，issue #138）：`inferType()` 用 toolName 正则启发式推断 ObservationType；`extractFiles()` 从 tool_input 抽路径。理由：默认开启 LLM 压缩 = 用户 API key 按工具调用频率持续烧 token。`AGENTMEMORY_AUTO_COMPRESS=true` 才进 LLM 路径。

- **Context injection 默认关**（`src/index.ts:256-264`，issue #143）：Hook 只抓不注入。"自动塞 4000 字记忆进 Claude" 对 Claude Pro 用户是 token 杀手——所以默认关，要 `AGENTMEMORY_INJECT_CONTEXT=true` 显式开启。这是项目对"成本可见性"的执着。

- **向量维度守卫**（`src/index.ts:368-410`）：持久化 vector index 维度与当前 embedding provider 不匹配时**拒绝启动**而不是 silently 让 cosineSimilarity 跨维度永远返回 0。可通过 `AGENTMEMORY_DROP_STALE_INDEX=true` 显式丢弃旧索引。"宁愿失败也不要静默错误"。

- **In-process BM25 + Vector**（`src/state/{search-index,vector-index}.ts`）：不依赖 Postgres / pgvector / Qdrant；BM25 用 Map<term, Set<obsId>> 倒排表 + termCount，Vector 用 Map<obsId, Float32Array> 暴力扫表 + cosine。极简实现，5 万条以内体感无延迟；超过则需要 ANN 替换 VectorIndex。

- **多层记忆模型**（`src/state/schema.ts:3-50`）：KV scope 用类型区分——episodic (`mem:obs:*`) → working (`mem:summaries`) → semantic (`mem:semantic`) / procedural (`mem:procedural`) → 知识图 (`mem:graph:nodes` / `mem:graph:edges`) → orchestration (`mem:actions` / `mem:routines` / `mem:leases` / `mem:signals` / `mem:checkpoints` / `mem:sketches` / `mem:facets` / `mem:sentinels` / `mem:crystals` / `mem:lessons` / `mem:insights`)。32+ 类记忆，每类一个 KV 命名空间。

- **强度衰减与遗忘**（`src/functions/consolidation-pipeline.ts:21-43` + 后台定时器）：`applyDecay()` 用 `strength * 0.9^periods` 指数衰减，配合 auto-forget (1h)、lesson-decay-sweep (24h)、insight-decay-sweep (24h)、consolidation (2h) 形成 Ebbinghaus 风格的"主动遗忘"机制——保留高强度记忆，旧低强度记忆自然淡出。

- **Hooks 与 SDK 解耦**：`src/hooks/*.ts` 是 standalone Node 脚本，**不导入 iii-sdk**，只通过 HTTP POST 到 REST API；用 `AbortSignal.timeout()` 包裹 fetch，全 try/catch 吞错。设计目标：Hook 失败绝不能阻塞 Agent 工具调用。

- **Bearer auth 可选**（`src/triggers/api.ts:35-48` + `src/auth.ts:timingSafeCompare`）：`AGENTMEMORY_SECRET` 配置后，所有 endpoint 走 `Bearer <secret>` 校验，用 timing-safe compare 防计时攻击。默认关，因为大多数用例是 localhost-only。

- **MCP "默认 8 / 全量 53" 双轨**（`src/index.ts:486-488` + `tools-registry.getVisibleTools()`）：53 个 MCP tools 是完整能力面，但默认只暴露 8 个核心工具（recall / save / compress_file / 等）给 Agent，避免选项过多让模型迷失；`AGENTMEMORY_TOOLS=all` 全量暴露给高级用户。

- **fire-and-forget rebuild**（`src/index.ts:412-432`）：首次启动若索引为空，`rebuildIndex` 可能耗时数小时（每条 observation 一次 embedding 调用，受限于云端速率），所以**绝不 await**——不阻塞 viewer 端口绑定与服务可用。索引边用边补，搜索质量随时间收敛。

## 关键组件深入解读

### `src/functions/observe.ts` — 写路径入口

`registerObserveFunction(sdk, kv, dedupMap, maxObservationsPerSession)` 注册 `mem::observe` 函数。流程（src/functions/observe.ts:42-120）：

1. **严格校验** `payload.sessionId / hookType / timestamp`，缺一即返回 `{success: false, error: ...}`，不抛异常（Hook 调用方需要明确响应而不是连接断）。
2. **去重**：若传入 `DedupMap`，用 `sessionId + toolName + tool_input` 计算 hash，命中则返回 `{deduplicated: true}` 直接退出。
3. **脱敏**：`stripPrivateData()` 对整个 payload.data 跑正则脱敏（API key / token / 邮箱 / 私钥指纹）。失败时降级为字符串脱敏。
4. **多模态识别**：`extractImage()` 递归扫 payload，识别 `data:image/*`、PNG/JPEG base64 头（`iVBORw0KGgo` / `/9j/`），或 `image_data`/`image_path` 字段；命中则把 modality 标 `image` 或 `mixed`。
5. **结构化字段**：按 hookType 抽 toolName / toolInput / toolOutput（post_tool_use）或 userPrompt（prompt_submit），存入 `RawObservation`。

### `src/state/hybrid-search.ts` — 检索核心

`HybridSearch.tripleStreamSearch(query, limit, entityHints?)`（src/state/hybrid-search.ts:77-160）：

- 三流并行：BM25 同步取 `limit * 2`；Vector 异步 `embed(query)` 失败则降级 BM25-only；Graph 用 `extractEntitiesFromQuery` 或传入 `entityHints`，BFS 深度 2。
- 顶 5 个 vector 结果做 "expansion search"（用 obsId 做相似度扩散，找邻居）。
- `searchWithExpansion(query, limit, expansion)`（src/state/hybrid-search.ts:42-75）把 query reformulations × 三流并行做 `Promise.all`，再用 `combinedScore` 去重最大值。

### `src/state/schema.ts` — KV scope 总线

`KV` 是 `const` 对象（src/state/schema.ts:3-50），既有固定 key（`mem:sessions` / `mem:memories` / `mem:audit`）又有函数形式（`observations(sessionId)` / `teamShared(teamId)` / `embeddings(obsId)`）。这种"函数化 key"模式让一个 KV scope 能横向分片到 sessionId / teamId / userId，避免单 scope 无限增长。

`generateId(prefix)` 用 `ts.toString(36) + uuid.slice(0,12)` 生成时间排序友好的 ID；`fingerprintId(prefix, content)` 用 sha256 前 16 字符做内容寻址（content-addressable dedup）；`jaccardSimilarity()` 给 dedup 提供回退方案（embedding 不可用时）。

### `src/index.ts` 注册仪式

`main()` 函数 425 行，其中 200+ 行全是 `registerXxxFunction(sdk, kv, ...)` 调用（src/index.ts:204-303）。这种"扁平注册"暴露了一个问题：每加一个 mem::xxx 都要在 `index.ts` 加一行，加一个 import；`AGENTS.md` 列出添加 MCP tool 需同步 7 处更新——这是项目当前最高的耦合点，未来重构方向应该是模块自注册（如装饰器或 module manifest）。

## 与同类对比

| 维度 | agentmemory | mem0 | letta (MemGPT) | claude-mem |
|------|-------------|------|----------------|------------|
| 部署形态 | 本地 Node + iii-engine + SQLite | Python 库 + 可选云 / Qdrant | Python 服务 + Postgres | TS CLI + 本地 chroma |
| 多 Agent 共享 | ✅ 同一 :3111 worker | ⚠️ 每应用一套 | ⚠️ 每用户一套 | ❌ 单 Agent |
| 检索栈 | BM25 + Vector + Graph (RRF) | Vector + Graph (Mem0 OSS 没有 BM25) | Vector (pgvector) | Vector (chroma) |
| 记忆层级 | 32+ KV scope (episodic / semantic / procedural / orchestration / graph / lessons / crystals / …) | episodic + semantic + procedural | core / archival / recall | episodic + compressed |
| Hook 集成 | 12 个 Claude Code hooks + 多 Agent 原生插件 | 无（被动 API） | 无 | 4 hooks |
| LLM 用量 | **默认零 LLM**（启发式压缩） | LLM 必需 | LLM 必需 | LLM 必需 |
| 知识图 | LLM 离线抽取 + 在线 BFS | LLM 抽取 + Neo4j 可选 | 无 | 无 |
| 评测 | LongMemEval + Coding-Life 内置 | LoCoMo benchmark | 内部 evals | 无 |
| 开源协议 | Apache-2.0 | Apache-2.0 | Apache-2.0 | MIT |

## 性能 / 资源开销

- **冷启动**：~2-3s（不算 iii-engine 启动 + 索引加载），boot log 显示分阶段就绪。
- **首次 rebuild**：fire-and-forget，可能数小时（受 embedding API 速率限制）；期间搜索质量从 BM25-only 渐变到三流满血。
- **稳态内存**：BM25 倒排表 + termFreq 大约 200-500 字节/observation；Vector 索引按 dim×4 字节（OpenAI text-embedding-3-small 1536 dim ≈ 6 KB/obs，Xenova all-MiniLM-L6 384 dim ≈ 1.5 KB/obs）。10 万 observation 总内存 ~600 MB-1.5 GB（含 KV 缓存）。
- **写延迟**：observe 端到端 5-30 ms（不含 LLM 压缩）；启用 `AGENTMEMORY_AUTO_COMPRESS=true` 后每次 observe 触发一次 LLM call，延迟受 provider 速率限制。
- **读延迟**：HybridSearch 单 query 内存扫表 + embedding 1 次 + graph BFS，典型 20-100 ms（10 万 vector 量级）；超过此规模需替换 VectorIndex 为 ANN（HNSW / FAISS / pgvector）。
- **未测**：实际 RAM 占用峰值、SQLite 单库膨胀曲线、多 worker 并发限制。

## 安全模型

- **信任边界**：localhost-only 是默认假设；端口 `:3111` / `:3113` 绑定 0.0.0.0 vs 127.0.0.1 由 iii-engine 决定。
- **认证**：`AGENTMEMORY_SECRET` 启用 Bearer token，所有 REST + MCP endpoint 走 `timingSafeCompare`（src/auth.ts）。默认关，因为 localhost 用例不需要。
- **脱敏**：`src/functions/privacy.ts:stripPrivateData()` 对所有 observe payload 跑正则脱敏 PII / 密钥；落库前已脱敏（src/functions/observe.ts:79-86）。
- **REST 白名单**：`AGENTS.md` 强制——REST endpoint 必须显式挑字段，不能把 `req.body` 原样塞给 `sdk.trigger`，避免攻击者注入未知函数参数。
- **审计**：`recordAudit()`（src/functions/audit.ts）记录所有状态变更操作到 `mem:audit` KV scope，含 operation 类型 + timestamp + 操作内容指纹。
- **已知风险**：
  - `unhandledRejection` 顶层吞 + 60s 节流（src/index.ts:120-129）可能掩盖真正的 bug；
  - Hook 脚本是 standalone Node 进程，运行时凭证（环境变量）继承自父 Agent，需注意 hook 脚本被恶意替换的风险；
  - 默认无 secret = 任何能访问 localhost:3111 的本机进程都能读写记忆（包括其他用户应用）。
