# TencentDB-Agent-Memory 架构与设计思路分析

> 仓库：https://github.com/TencentCloud/TencentDB-Agent-Memory · 分析日期：2026-06-07 · 版本：v0.3.6 / HEAD `f92b102` (2026-06-04)

## 一句话定位

TencentDB-Agent-Memory 是腾讯云出品的 OpenClaw / Hermes Agent 记忆插件，npm 包名 `@tencentdb-agent-memory/memory-tencentdb`。它把长期记忆做成 L0 Conversation → L1 Atom → L2 Scenario → L3 Persona 的分层语义金字塔，同时把短期长任务日志做 context offload，压缩成可回溯的 Mermaid 符号画布。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| OpenClaw 插件入口 | `index.ts`, `openclaw.plugin.json` | 解析配置、注册工具、挂载 `before_prompt_build` / `agent_end` / `gateway_stop` 等 hook |
| Host-neutral core | `src/core/tdai-core.ts`, `src/core/types.ts`, `src/adapters/*` | 把 OpenClaw/Hermes/Gateway 的差异压到 `HostAdapter` 和 `LLMRunnerFactory`，核心只暴露 recall/capture/search/session flush |
| L0 捕获 | `src/core/hooks/auto-capture.ts`, `src/core/conversation/l0-recorder.ts`, `src/utils/checkpoint.ts` | 原子游标捕获新消息，写 conversations JSONL，并可写 L0 向量索引 |
| L1 结构化记忆 | `src/core/record/*`, `src/core/prompts/l1-*` | LLM 从 L0 提取 persona/episodic/instruction 记忆，去重/合并后写 records JSONL 和 store |
| L2 场景块 | `src/core/scene/*`, `src/core/prompts/scene-extraction.ts` | 用工具型 LLM 在 `scene_blocks/` 沙箱内维护场景 Markdown、索引和导航 |
| L3 用户画像 | `src/core/persona/*`, `src/core/prompts/persona-generation.ts` | 根据变更场景增量生成 `persona.md`，并附加 scene navigation |
| Pipeline 调度 | `src/utils/pipeline-manager.ts`, `src/utils/pipeline-factory.ts` | L1 阈值/idle/warmup，L2 downward-only timer，L3 全局串行队列 |
| 检索与存储 | `src/core/store/*`, `src/core/tools/*` | SQLite / TCVDB 后端抽象，FTS/BM25/vector/hybrid search，Agent 工具输出格式化 |
| Context offload | `src/offload/*` | 工具日志卸载、L1/L1.5/L2 Mermaid 画布、L3 压缩、MMD 注入和 token 预算控制 |
| Hermes / Gateway | `src/gateway/*`, `hermes-plugin/memory/memory_tencentdb/*`, `docker/opensource/*` | Node HTTP sidecar 暴露 TDAI Core；Python provider 管理 sidecar 生命周期并转发 Hermes prefetch/sync |
| 运维脚本 | `scripts/*`, `bin/*`, `src/cli/*` | seed、迁移 SQLite 到 TCVDB、导出 VDB、读取本地记忆、Hermes 安装和诊断 |

关键约束是“core 不绑定宿主”：`TdaiCore` 只依赖 `HostAdapter`、`LLMRunnerFactory`、`IMemoryStore` 这些接口；OpenClaw 插件、Hermes Provider、HTTP Gateway 只是不同外壳。这样同一套 L0→L3 pipeline 能在 in-process 插件和 sidecar 模式下复用。

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

`index.ts` 注册 `tdai_memory_search` / `tdai_conversation_search` 两个工具，并在 `before_prompt_build` 调 `core.handleBeforeRecall()`，在 `agent_end` 调 `core.handleTurnCommitted()`（`index.ts:349-757`）。auto-recall 把 L1 动态记忆放到 user prompt 前缀，把 L2 scene navigation、L3 persona、工具指南放到 system prompt 末尾，刻意分离动态/稳定内容以利于 prompt caching（`src/core/hooks/auto-recall.ts:186-218`）。

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

Pipeline manager 的注释直接定义了四层架构：L0 本地捕获，L1 threshold/idle 批处理，L2 per-session downward-only timer，L3 全局 mutex + pending flag（`src/utils/pipeline-manager.ts:1-76`）。L1 不是简单摘要，而是 scene segmentation + memory extraction + batch conflict detection；写入策略是 JSONL append-only + VectorStore 实时删除/更新（`src/core/record/l1-extractor.ts:1-35`, `src/core/record/l1-writer.ts:1-26`）。

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

`createStoreBundle()` 以 `storeBackend` 切分 SQLite 和 TCVDB。TCVDB 要求 url/apiKey/database，返回 `TcvdbMemoryStore` 和 `NoopEmbeddingService`，因为 embedding 由服务端做；SQLite 则创建本地 `vectors.db` 和可选 OpenAI-compatible embedding service（`src/core/store/factory.ts:41-127`）。auto-recall 在 TCVDB 支持 native hybrid 时走单次 hybridSearch，否则 SQLite 路径并行 FTS5 + embedding 后客户端 RRF（`src/core/hooks/auto-recall.ts:320-408`）。

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

offload 是独立开关，不影响 L0→L3 长期记忆。它的目标是长任务内的短期上下文压力：原始工具输出放 `refs/*.md`，上下文只保留可读的 Mermaid 任务图和 node_id。README 给出的评测声称 OpenClaw 集成后最高节省 61.38% token，WideSearch 通过率相对提升 51.52%，PersonaMem 准确率从 48% 到 76%。

## 设计决策与哲学

- **宿主中立 core，宿主适配器外置**：`TdaiCore` 文档明确它同时服务 OpenClaw 和 Hermes/Gateway，依赖抽象接口而不是具体宿主（`src/core/tdai-core.ts:1-20`）。这解释了为什么 OpenClaw 插件是 `index.ts`，Hermes 是 Python provider + Node Gateway，但核心方法仍是同一组。
- **长期记忆不是平铺向量，而是 L0→L3 金字塔**：L0 保留原始对话，L1 提取结构化 atom，L2 场景块提供中层组织，L3 persona 提供高层用户画像。低层保留证据，高层保留结构。
- **动态记忆和稳定上下文拆开注入**：L1 搜索结果是 `prependContext`，L2/L3/工具指南是 `appendSystemContext`，降低动态记忆对 system prompt cache 的破坏（`src/core/hooks/auto-recall.ts:186-218`）。
- **捕获走原子 checkpoint，避免重复写 L0**：auto-capture 把“读游标 → recordConversation → advance cursor”包进 `checkpoint.captureAtomically()`，用于防并发 `agent_end` 读到同一个旧游标导致重复记录（`src/core/hooks/auto-capture.ts:87-133`）。
- **pipeline 用时间语义解决长会话节奏**：L1 有 threshold / idle / flush 三条触发路径，warmup 从 1→2→4 逐步放缓；L2 用 downward-only timer，能提前但不推迟，兼顾响应速度和 max interval（`src/utils/pipeline-manager.ts:42-73`）。
- **JSONL 是备份/恢复事实，VectorStore 是检索引擎**：L1 writer 注释说明 records JSONL append-only，VectorStore 是 retrieval engine；update/merge 时实时删除旧向量，但 JSONL 旧行保留到 cleaner 周期处理（`src/core/record/l1-writer.ts:1-26`）。
- **存储后端 capability-based degradation**：`IMemoryStore` 用 capability flags 表达 vector/FTS/native hybrid/sparse 能力；调用方根据能力降级，而不是假定某个后端全能（`src/core/store/types.ts:144-171`）。
- **TCVDB 路径强调服务端 embedding + native hybrid**：TCVDB 后端用服务端 dense embedding、客户端 BM25 sparse vector、native hybridSearch，避免 SQLite 路径的本地 embedding 和双路请求开销（`src/core/store/tcvdb.ts:1-8`）。
- **Gateway 安全默认兼容旧行为，但显式告警**：`/health` 总是开放，其他接口可用 Bearer auth；apiKey 未配置时保持开放，但启动日志会对非回环地址 + 无 auth 大声 WARN（`src/gateway/server.ts:167-213`, `src/gateway/server.ts:289-315`）。
- **LLM 工具写文件必须沙箱化**：L2 SceneExtractor 让 LLM 只在 `scene_blocks/` 工作区读写；失败时从 backup 恢复，避免半写入清空场景（`src/core/scene/scene-extractor.ts:1-22`）。

## 关键组件深入解读

### `TdaiCore`（`src/core/tdai-core.ts`）

`TdaiCore` 是整个项目的门面。`initialize()` 创建数据目录、异步初始化 store，并在 extraction enabled 时创建 pipeline manager；store 初始化失败也会 wiring runners，让系统降级为 JSONL fallback。`handleBeforeRecall()` 调 auto-recall，`handleTurnCommitted()` 先确保 scheduler 已启动，再调 auto-capture。

工程上最值得注意的是两个并发防线。第一，`schedulerStartPromise` 把 scheduler start 做成 one-shot promise gate，避免 Gateway 多个 `/capture` 并发时有请求在 checkpoint restore 完成前修改 scheduler state。第二，`bgTasks` 追踪 fire-and-forget 的 L0 embedding 后台任务，`destroy()` 会在关闭 store 前最多等 5 秒，减少 late write 打到已关闭 DB 的概率（`src/core/tdai-core.ts:88-123`, `src/core/tdai-core.ts:169-233`）。

### `MemoryPipelineManager`（`src/utils/pipeline-manager.ts`）

Pipeline manager 是长期记忆节奏控制器。它维护 per-session state、timers、message buffer，并用 L1/L2/L3 三个 `SerialQueue` 串行化同层任务。L1 的 warmup 让新 session 第一轮就能提取记忆，随后阈值翻倍直到 steady state；L2 的 downward-only timer 在 L1 完成后可以把下一次场景抽取提前，但不会往后推迟，避免持续对话让场景归纳永远等不到。

`flushSession()` 和 `destroy()` 被明确区分：session end 只 flush 某个 session，不能销毁全局 scheduler；gateway stop 才是全局 teardown。这是面向 Hermes/Gateway 并发会话的关键语义。

### Gateway / Hermes sidecar

`src/gateway/server.ts` 用 Node 原生 `http` 实现 sidecar，不依赖 Express/Fastify。它把 `/recall`、`/capture`、`/search/memories`、`/search/conversations`、`/session/end`、`/seed` 都转成 `TdaiCore` 方法。Hermes Python provider 通过 `MemoryTencentdbSdkClient` 调这些接口，并由 `GatewaySupervisor` 管理 sidecar 进程、health check、日志文件和崩溃重启。

这个设计的取舍是：OpenClaw 可以 in-process 直接挂 hook，Hermes 则通过 HTTP sidecar 接入同一套 core。安全上，Gateway 支持可选 Bearer token 和 CORS allow-list，但 auth 默认关闭以兼容旧部署，因此文档和启动日志都强调不要把无鉴权端口暴露到非回环网络。

## 与同类对比

| 维度 | TencentDB-Agent-Memory | agentmemory | memsearch | PowerMem |
|------|------------------------|-------------|-----------|----------|
| 主形态 | OpenClaw 插件 + Hermes sidecar | 跨 Agent worker / MCP / REST | 多平台 coding agent memory CLI/plugin | 记忆中间件 / SDK / API / MCP |
| 长期记忆层次 | L0 Conversation → L1 Atom → L2 Scenario → L3 Persona | 多层记忆 + graph/vector/BM25 | Markdown memory + Milvus shadow index | working/short/long + 衰减 |
| 短期上下文 | Context offload + Mermaid MMD + node_id 回溯 | context injection 可配置 | search/expand/transcript | 偏长期记忆和应用层 |
| 存储 | SQLite + sqlite-vec/FTS5 或 Tencent Cloud VectorDB | SQLite | Markdown + Milvus | OceanBase / SeekDB 等 |
| 检索 | FTS5 / vector / hybrid RRF；TCVDB native hybrid | BM25 + vector + graph RRF | Milvus dense + BM25 RRF | 向量+全文+稀疏+图 |
| AI 用法 | L1/L2/L3 抽取和 offload 都深度依赖 LLM | 默认零 LLM，启发式优先 | 摘要/compact 可 LLM | LLM 抽取/优化较深 |

这个项目最有辨识度的地方是把“长期个性化记忆”和“短期任务上下文卸载”合并到同一个插件，而不是只做 recall。它和 memsearch 都强调可回溯，但 memsearch 的 source of truth 是 Markdown journal；TencentDB-Agent-Memory 的长期事实以 JSONL/store/scene Markdown/persona Markdown 共同组成分层系统。

## 性能 / 资源开销

未做本地 benchmark。源码和 README 可确认的性能策略包括：

- README 报告：OpenClaw 集成后 WideSearch token 从 221.31M 降到 85.64M，SWE-bench token 从 3474.1M 降到 2375.4M，AA-LCR token 从 112.0M 降到 77.3M。
- auto-recall 默认 5000ms 总超时，超时跳过记忆注入，避免用户等待被 store/embedding 卡住。
- SQLite 支持 deferred embedding：先写 L0 metadata + FTS，embedding 后台更新；destroy 会 drain 后台任务。
- TCVDB native hybrid 避免 SQLite 路径的 keyword + embedding 双路请求。
- offload 的 L3 compression 有 fast-token-estimate、boundary cache、aggressive/emergency fallback，避免长上下文每轮全量 tiktoken。
- L1/L2/L3 使用 SerialQueue 限制同层并发，换取一致性和较低资源尖峰。

## 安全模型

- OpenClaw hook 会 strip `<relevant-memories>`，避免召回内容污染历史 transcript（`index.ts:615-651`）。
- L2 LLM 只在 `scene_blocks/` workspace 内操作，失败后从 backup 恢复，降低 LLM 半写入破坏状态的风险。
- Gateway auth 是 opt-in：设置 `TDAI_GATEWAY_API_KEY` 后非 `/health` 路由需要 Bearer token，并用 `timingSafeEqual` 比较；未设置时保持开放但输出告警。
- CORS 默认不发 header；`"*"` 需要显式配置，启动日志会警告。
- Hermes supervisor 不把 client-side api_key 自动注入 Gateway 子进程环境，避免误以为一端配置会自动打开另一端鉴权。
- TCVDB apiKey、embedding apiKey、LLM apiKey 都是配置层输入；仓库代码没有把它们硬编码进插件。
