---
title: Agent Memory 项目地图
tags: [agent-memory, project-map, ai-agent, llm-infra]
date: 2026-06-09
sources: [src-claude-mem-architecture, src-powermem-architecture, src-agentmemory-architecture, src-agent-recall-architecture, src-memsearch-architecture, src-tencentdb-agent-memory-architecture]
related: [[agent-memory]], [[claude-mem]], [[powermem]], [[agentmemory]], [[agent-recall]], [[memsearch]], [[tencentdb-agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[hybrid-search-rrf]], [[ai-as-compressor]]
---

# Agent Memory 项目地图

这页把当前已摄入的 memory 相关项目横向整理。核心结论：这些项目不是在做同一件事，而是在同一个问题空间里选择了不同的事实源、宿主入口、压缩成本、检索治理边界和上下文注入策略。

从工程架构看，Agent Memory 不是一个“向量库 + top-k 搜索”的问题，而是一条完整的数据管线：

```
Agent runtime event / explicit memory call / app SDK call
        ↓
capture boundary: hook / MCP tool / REST / SDK / Markdown append
        ↓
write policy: dedup / scope / privacy / conflict / budget / queue
        ↓
compression: none / heuristic / LLM facts / scene/persona hierarchy
        ↓
truth store: SQLite / Markdown / JSONL / OceanBase / KV bus
        ↓
shadow index: FTS / BM25 / dense vector / sparse vector / graph
        ↓
recall: auto injection / search tool / briefing / progressive drill-down
        ↓
context governance: token budget / prompt cache / evidence trace / scope
```

真正的架构分歧主要发生在三个地方：

- **写入边界**：谁决定“这值得记住”。
- **真相层**：系统崩溃、索引损坏、模型更换后，应该从哪里恢复事实。
- **注入边界**：什么内容可以自动进入 prompt，什么内容必须让 Agent 主动搜索下钻。

## 一句话分层

| 项目 | 一句话定位 | 最适合的问题 |
|------|------------|--------------|
| [[claude-mem]] | Claude Code 专用长期记忆插件，hook 采集 + worker 异步压缩 + SQLite/Chroma 双索引 | 给 Claude Code 单机用户加跨会话记忆 |
| [[agent-recall]] | 本地优先的 MCP-native 结构化记忆库，SQLite + scope hierarchy + AI briefing | 多项目/多客户场景下保存实体、关系、决策和 scoped facts |
| [[agentmemory]] | 跨 Agent 本地记忆服务，REST/MCP/hooks + iii-engine + BM25/vector/graph 三流检索 | 多个 coding agent 共用一个本地 memory worker 和 viewer |
| [[powermem]] | 应用级记忆中间件，SDK/CLI/API/MCP/Dashboard 多入口 + OceanBase/SeekDB 后端 | 把 LLM app / agent framework 的记忆做成可部署服务 |
| [[memsearch]] | 跨平台 coding agent 语义记忆，Markdown source-of-truth + Milvus shadow index | 让 Codex/Claude/OpenCode/OpenClaw 从历史会话 Markdown 里渐进式回溯 |
| [[tencentdb-agent-memory]] | OpenClaw/Hermes 记忆插件，L0→L3 分层长期记忆 + context offload | 同时处理长期 persona/scene memory 和短期工具日志压缩 |

## 横向对比

| 维度 | [[claude-mem]] | [[agent-recall]] | [[agentmemory]] | [[powermem]] | [[memsearch]] | [[tencentdb-agent-memory]] |
|------|----------------|------------------|-----------------|--------------|---------------|----------------------------|
| 主宿主 | Claude Code | MCP clients / CLI / Claude hooks | Claude Code / Codex / Cursor / MCP clients | SDK / CLI / API / MCP / IDE 插件 | Claude Code / Codex / OpenCode / OpenClaw | OpenClaw / Hermes / Gateway |
| 主形态 | 宿主插件 + 本地 worker | MCP-native 结构化记忆库 | 本地常驻服务 + MCP/REST/viewer | 应用中间件 / 服务化 memory layer | CLI/plugin + Markdown 记忆库 | 插件/sidecar + 分层 pipeline |
| 写入口 | lifecycle hooks | MCP memory tools / CLI | hooks / REST / MCP | `Memory.add()` / HTTP / MCP / plugin hook | 平台 hook append Markdown | before/after hook + tool/offload |
| 写入语义 | 捕获 tool event，再由后台判断 | Agent 主动声明 entity/fact/relation | 观察事件 + remember/save API | 应用显式提交 memory item | 追加可审计会话摘要 | 捕获 L0，再抽 L1/L2/L3 |
| 事实源 | SQLite observations | SQLite entities/slots/relations | iii-engine SQLite KV | OceanBase / SeekDB / pgvector / SQLite | `.memsearch/*.md` Markdown | JSONL records + scene/persona files |
| 索引层 | SQLite FTS5 + Chroma | SQLite FTS5/LIKE | in-process BM25 + vector + graph | vector + FTS + sparse + graph | Milvus dense + BM25 sparse | SQLite FTS/vector 或 TCVDB hybrid |
| 压缩策略 | 后台 LLM 压成 structured observations | raw graph → AI briefing cache | 默认零 LLM 启发式，可选 LLM | LLM fact extraction + importance eval | daily/PROJECT/USER maintenance | L0→L1→L2→L3 多级 LLM 管线 |
| 权限/隔离 | profile/env/path 隔离为主 | MCPBridge scope enforcement | API/MCP 暴露面 + privacy filter | 多租户 scope/permission/privacy controllers | 项目目录 + collection 隔离 | host config + store backend + pipeline scope |
| 注入方式 | SessionStart auto context + mem-search skill | SessionStart AI briefing | context injection 可配置 + MCP tools | API/search 返回给应用或插件注入 | 启动提示 + `$memory-recall` 下钻 | prepend L1 + append L2/L3 + tools |
| 恢复模型 | outbox / SQLite / Chroma watermark | SQLite truth + cache 可重建 | KV truth + index persistence/rebuild | 后端 DB truth + optimizer metadata | Markdown truth，Milvus 可重建 | JSONL/files truth，store 可重建 |
| 主要强项 | Claude Code 集成自然，模式清晰 | scope hierarchy 和 bitemporal facts | 多入口、多工具、viewer、零 LLM 默认 | 后端/provider/部署形态最完整 | Markdown 可审计，可重建索引 | 分层记忆 + context offload 合一 |
| 主要代价 | 生态偏 Claude Code | 向量/语义能力较轻 | iii-engine 依赖和工具面较大 | 部署/配置复杂度更高 | 依赖 Milvus 路径和索引维护 | 管线复杂、宿主偏 OpenClaw/Hermes |

## 架构交叉矩阵

这些项目经常“看起来不同，底层同构”。真正可复用的是工程模式，而不是某个具体后端。

| 交叉模式 | 采用项目 | 工程含义 |
|----------|----------|----------|
| [[event-driven-memory-pipeline|Hook → worker → store]] | [[claude-mem]], [[agentmemory]], [[memsearch]], [[tencentdb-agent-memory]], [[powermem]] Claude 插件 | Hook 只做捕获和转发，AI 压缩、embedding、索引重建都放到后台；关键是失败不能阻塞 Agent 主流程 |
| MCP memory tools | [[agent-recall]], [[agentmemory]], [[powermem]], [[tencentdb-agent-memory]] | 把“记住/查询/删除/展开”变成 Agent 可调用协议；写入质量取决于 tool instructions 和模型是否愿意主动保存 |
| SQLite 本地事实层 | [[claude-mem]], [[agent-recall]], [[agentmemory]], [[tencentdb-agent-memory]] SQLite 模式 | 单机部署简单，事务/WAL/FTS 成熟；难点是多进程锁、索引重建和 scope enforcement |
| Markdown / JSONL 可审计真相 | [[memsearch]], [[tencentdb-agent-memory]] | 人类可读、可 diff、可备份，索引可重建；代价是需要额外处理 chunk ID、行号 anchor、文件一致性 |
| [[hybrid-search-rrf|Hybrid + RRF]] | [[agentmemory]], [[powermem]], [[memsearch]], [[tencentdb-agent-memory]] | BM25/FTS 抓字面，vector 抓语义，graph/scope/time 做约束；RRF 比单一相似度更稳 |
| 三层/渐进式召回 | [[claude-mem]], [[memsearch]], [[tencentdb-agent-memory]], [[agent-recall]] | 先给摘要/片段，再按需展开原文，避免 top-k 原文直接撑爆 prompt |
| AI 压缩层与真相层分离 | [[claude-mem]], [[agent-recall]], [[powermem]], [[tencentdb-agent-memory]] | LLM 输出是压缩视图，不应该成为唯一证据；否则 hallucinated memory 会永久化 |
| 显式成本控制 | [[agentmemory]], [[agent-recall]], [[memsearch]], [[tencentdb-agent-memory]] | 默认不自动塞大量上下文，或者只注入轻量 hint/briefing；用户需要时再 search/expand |

### 交叉 1：Hook 插件和后台服务的边界

[[claude-mem]]、[[agentmemory]]、[[tencentdb-agent-memory]] 都把 hook 设计得很薄：

```
hook receives stdin JSON
        ↓
normalize minimal payload
        ↓
HTTP/process handoff with timeout
        ↓
swallow errors or return lightweight context
```

这条边界的关键不是“怎么调用 HTTP”，而是 **hook 不能把 Agent 运行时变成 memory 系统的人质**。工具执行后的 hook 如果同步做 LLM 压缩或 embedding，一次 provider 慢请求就会把用户的 coding agent 卡住。所以这些项目都倾向于：

- `PostToolUse` / `agent_end` 捕获事件后异步处理。
- SessionStart / before_prompt_build 只读 cache 或做轻量检索。
- worker 崩溃时降级为无记忆，而不是阻断宿主。

差异在于后台服务形态：[[claude-mem]] 内置 worker + BullMQ/SQLite/Chroma；[[agentmemory]] 外置 iii-engine 作为函数总线；[[tencentdb-agent-memory]] 把核心封装成 `TdaiCore`，在 OpenClaw in-process 和 Hermes sidecar 之间复用。

### 交叉 2：MCP 是工具入口，不等于存储模型

[[agent-recall]]、[[agentmemory]]、[[powermem]] 都支持 MCP，但 MCP 在三个项目里的角色不同：

- [[agent-recall]]：MCP 是主入口。它用 server instructions 要求 Agent 主动保存 people、decisions、facts、context，并在 `MCPBridge` 做 scope 读写过滤。
- [[agentmemory]]：MCP 是完整能力面之一。真实业务函数在 worker/iii-engine 里，MCP tools 只是和 REST/hook 并列的触发层。
- [[powermem]]：MCP 是中间件接入形态之一。核心仍是 `Memory`/`AsyncMemory` SDK 和存储适配层。

所以“是否支持 MCP”不是关键问题；关键问题是 **MCP tool call 是否承载写入语义、权限边界和行为引导**。[[agent-recall]] 的工程亮点就在这里：它把主动记忆策略嵌进 MCP server instructions，并把权限 enforcement 放在 bridge，而不是底层 store。

### 交叉 3：Source-of-truth 和 shadow index 的分离

Agent Memory 系统迟早会遇到索引损坏、embedding model 更换、chunk 切分规则变化、vector dimension mismatch、LLM 压缩失败等问题。因此成熟设计都会区分：

- **事实真相层**：SQLite rows、Markdown、JSONL、scene blocks、persona file、OceanBase records。
- **可重建索引层**：FTS table、Chroma collection、Milvus collection、in-memory BM25/vector、TCVDB hybrid collection。

[[memsearch]] 把这个边界做得最清楚：Markdown 是 truth，Milvus 是 shadow index；chunk ID 绑定 source/line/content/model，模型切换不会污染旧索引。[[tencentdb-agent-memory]] 也类似：JSONL/scene/persona 是恢复材料，SQLite/TCVDB 是检索引擎。[[agentmemory]] 的难点在 index persistence：BM25/vector 会周期性落回 KV，维度不匹配时拒绝启动，防止静默错误。

### 交叉 4：混合检索不是“加一个向量库”

这六个项目里，纯向量 top-k 基本不是最终形态。原因很实际：

- coding agent 的记忆常包含文件名、命令、函数名、issue id、路径、专有名词；这些更适合 BM25/FTS。
- 用户常问“上次那个设计”“之前某个客户约束”；这些更适合 dense vector。
- 多项目/多客户/多人场景需要 scope、time、entity graph；这些不是相似度能自然解决的。

[[powermem]] 是最企业化的检索栈：vector + FTS + sparse + graph，再做 RRF、衰减加权、rerank。[[agentmemory]] 是本地轻量版本：in-process BM25 + Float32Array vector + graph BFS。[[memsearch]] 把 dense 和 BM25 都放进 Milvus。[[tencentdb-agent-memory]] 在 SQLite 路径用 FTS/vector/RRF，在 TCVDB 路径用 native hybridSearch。

## Memory 写入方式的区别

写入方式决定了 memory 的质量上限。检索再强，也救不了错误写入、噪声写入和越权写入。

| 写入类型 | 代表项目 | 写入动作 | 优点 | 主要风险 |
|----------|----------|----------|------|----------|
| 被动事件捕获 | [[claude-mem]], [[agentmemory]], [[tencentdb-agent-memory]] | hook 捕获 prompt/tool/session event | 用户无感，覆盖率高 | 噪声多、需要强 dedup/压缩 |
| 主动工具写入 | [[agent-recall]], [[agentmemory]] | Agent 调 MCP tools 保存实体/事实/关系 | 语义清楚，结构化强 | 依赖模型自觉，容易漏记 |
| 应用 SDK 写入 | [[powermem]] | app 调 `Memory.add()` | 产品可控，能结合业务 schema | 对 coding agent 无法完全无侵入 |
| Markdown append | [[memsearch]] | hook/skill 追加 daily/PROJECT/USER Markdown | 可审计、可手改、可重建 | 需要维护 chunk/anchor/index 一致性 |
| 分层管线写入 | [[tencentdb-agent-memory]] | L0 捕获 → L1 atom → L2 scenario → L3 persona | 长短期结构清楚，注入层次自然 | pipeline 调度、冲突、半写入复杂 |
| Briefing/cache 写入 | [[agent-recall]] | raw context → AI briefing cache | 启动快，scope-aware | cache 不是 truth，staleness 要治理 |
| Context offload 写入 | [[tencentdb-agent-memory]] | 工具日志写 refs，MMD 节点进上下文 | 解决短期上下文爆炸 | node_id、原文、摘要必须能互相追踪 |

### 1. 被动事件捕获：覆盖率高，治理成本也高

[[claude-mem]] 的写路径是典型模式：

```
PostToolUse / UserPromptSubmit / Stop
        ↓
bun-runner lightweight handoff
        ↓
worker outbox / queue
        ↓
LLM observation generation
        ↓
SQLite transaction + Chroma sync
```

这类系统的优势是用户不用记得“保存记忆”。coding agent 的重要事实往往来自工具执行：读了哪个文件、改了哪个模块、发现了什么失败路径、最后怎么修复。被动捕获能把这些都送进候选集。

代价是治理困难：

- 工具结果常有大量临时输出，直接入库会污染检索。
- 同一个事实会被多次触发，需要 content hash、时间窗或语义 dedup。
- Hook 必须短超时、吞错、降级，不能影响用户主流程。
- LLM 压缩如果异步失败，需要重试和 outbox，否则事件会丢。

[[agentmemory]] 对这个问题的取舍更激进：默认不调用 LLM，而是 `buildSyntheticCompression()` 做启发式压缩，保护用户 API token；LLM 自动压缩要显式打开。它牺牲一部分语义质量，换来默认成本可控。

### 2. 主动工具写入：结构清楚，但依赖 Agent 行为

[[agent-recall]] 的主路径不是“抓所有工具日志”，而是让 Agent 主动调用 MCP memory tools：

```
create_entities / add_observations / add_relations
        ↓
MCPBridge input limits + scope filtering
        ↓
MemoryStore SQLite entities / slots / observations / relations
        ↓
context_gen generates scoped AI briefing
```

这个模式适合 people、organizations、project decisions、customer-specific facts 这类结构化长期知识。它的关键设计是把语义边界前移：写入时就知道这是 entity、slot、relation 还是 observation。

但它有两个工程难点：

- Agent 可能忘记写，或者把临时判断写成长期事实。
- 权限不能靠 store 自觉。[[agent-recall]] 明确让 `MemoryStore` 不做 scope enforcement，而把 MCP 可见边界集中在 `MCPBridge`，这是更清晰的信任模型。

### 3. 应用 SDK 写入：适合产品，不一定适合 terminal agent

[[powermem]] 的写路径更像一个 LLM app memory middleware：

```
Memory.add(prompt, user_id, agent_id, run_id)
        ↓
LLM fact extraction
        ↓
ImportanceEvaluator + Ebbinghaus metadata
        ↓
embedding / sparse embedding
        ↓
StorageAdapter route to OceanBase / SeekDB / pgvector / SQLite
```

它的优势是应用拥有调用点，可以在业务语义最清楚的地方写入。比如客服、教育、CRM、个人助手可以把 user_id、agent_id、run_id、scope、permission 都作为一等参数传入。

它不一定适合纯 coding agent 插件的原因是：terminal agent 的事实来源经常分散在工具调用和文件读写里，应用层没有一个干净的 `add()` 边界。因此 PowerMem 也提供 Claude Code plugin / MCP / IDE 扩展，但它的架构核心仍是服务化 memory layer。

### 4. Markdown append：可审计性优先

[[memsearch]] 的写入不是直接进 DB，而是先写 Markdown：

```
platform hook parses transcript
        ↓
append .memsearch/memory/YYYY-MM-DD.md
        ↓
scanner/chunker computes stable chunk_id
        ↓
Milvus dense + BM25 sparse index
```

这个模式的工程价值很大：memory 可以被人类 review、diff、迁移、手改；Milvus 坏了可以重建；embedding model 切换可以重新生成 collection。

代价也很明确：

- Markdown 结构必须足够稳定，否则 heading/line anchor 会漂移。
- chunk ID 要绑定 content/model/source，否则增量索引会脏。
- hook 生成的摘要质量会直接影响后续检索。
- 需要 `search → expand → transcript` 的渐进式协议，否则单个 chunk 太短容易断章取义。

### 5. 分层写入：把“记忆”拆成证据、事实、场景、画像

[[tencentdb-agent-memory]] 是这组里写入管线最复杂的：

```
L0 Conversation JSONL
        ↓
L1 Atom records: persona / episodic / instruction memory
        ↓
L2 Scenario scene_blocks/*.md
        ↓
L3 Persona persona.md + scene navigation
```

这不是单纯“多摘要几次”，而是在解决不同注入层的稳定性问题：

- L0 是证据，不适合直接注入。
- L1 是可检索事实，适合 prepend 动态召回。
- L2 是场景导航，适合 append 到 system context。
- L3 是用户画像，变化慢，适合长期稳定注入。

这条路的难点是 pipeline consistency：L1 有 threshold/idle/flush 三种触发，L2 用 downward-only timer，L3 要全局串行避免并发改 persona。LLM 还会被允许改写 `scene_blocks/`，因此必须有沙箱、备份和恢复逻辑，防止半写入破坏状态。

## 项目工程剖面

### [[claude-mem]]：最标准的事件驱动闭环

[[claude-mem]] 的价值在于把 Claude Code 插件 memory 的最小闭环打穿：

```
Lifecycle hooks
  → worker queue
  → LLM observation generation
  → SQLite/FTS + Chroma
  → SessionStart injection + mem-search skill
```

它的工程核心是 **边缘轻、后台重**。Hook 负责接力，worker 负责 AI 压缩、解析、事务写入和 Chroma 同步。MemoryItem schema 把自然语言 narrative、facts、concepts、filesRead、filesModified 拆开，说明它不是把 transcript 原文塞进向量库，而是先变成可索引观察。

适合借鉴的点：

- PostToolUse 不直接做 LLM。
- outbox / hash / retry 处理 AI 非确定输出和失败。
- `search → timeline → get_observations` 防止一次塞太多上下文。

主要风险：

- 宿主强绑定 Claude Code。
- 如果 observation 压缩 prompt 质量不稳，会把噪声永久化。
- Chroma 与 SQLite 的双写一致性需要 watermark/同步治理。

### [[agent-recall]]：结构化事实和 scope governance 优先

[[agent-recall]] 更像“给 Agent 的本地知识图谱”，而不是“会话日志搜索”。它把 people、decisions、facts、context 作为主动写入对象，底层 SQLite 维护 entities、slots、observations、relations。

它最重要的工程边界是：

```
MCP client
  → MCPBridge: limits + scope read/write filter
  → MemoryStore: trusted SQLite operations
  → context/briefing: scoped context assembly
```

`MemoryStore` 不做 scope enforcement 不是缺陷，而是明确把底层 store 定义成可信 API；面向多 Agent 的 MCP 入口才是权限边界。这个设计比“每层都检查一点权限”更容易审计。

适合借鉴的点：

- scope hierarchy + local-over-parent inheritance。
- bitemporal slots 表达事实更新，而不是覆盖丢历史。
- AI briefing 是 cache，不是 truth。

主要风险：

- 主动写入依赖模型行为，漏记问题不可避免。
- 语义检索能力较轻，复杂回忆可能需要结合外部 vector layer。
- CLI 和 MCP 的信任模型不同，需要文档非常清楚。

### [[agentmemory]]：跨 Agent worker 和成本可见性

[[agentmemory]] 的架构很宽：hooks、REST、MCP、viewer、iii-engine、50+ functions、32+ KV scopes。它的核心取舍不是“最简单”，而是让多个 Agent 共用一个本地记忆服务。

写路径和检索路径都体现了成本控制：

- Hook standalone，不导入 iii-sdk，只 HTTP POST。
- 默认零 LLM 压缩，避免每个 tool call 都烧 token。
- Context injection 默认关，避免自动注入 4000 字记忆击穿用户预算。
- Embedding provider 缺失时退化 BM25-only。

它的检索是本地轻量混合检索：

```
BM25 inverted index
  + VectorIndex Float32Array cosine
  + GraphRetrieval BFS
  → RRF + optional rerank
```

适合借鉴的点：

- 默认安全/低成本，重功能显式开启。
- 向量维度不匹配直接失败，避免 silent bad search。
- fire-and-forget rebuild，让服务先可用，索引质量逐步收敛。

主要风险：

- iii-engine 是强依赖，部署和调试复杂度更高。
- MCP tool 面太大，默认只暴露 8 个核心工具是必要收敛。
- 业务函数数量多，接口同步和回归测试成本高。

### [[powermem]]：把 memory 做成中间件

[[powermem]] 的工程目标和 coding-agent 插件不同。它不是只服务某个 terminal agent，而是把 memory layer 做成 SDK/CLI/API/MCP/Dashboard/IDE plugin 共用的基础设施。

核心路径是：

```
Memory.add()
  → LLM fact extraction
  → importance / retention metadata
  → dense + sparse embedding
  → StorageAdapter
  → OceanBase / SeekDB / pgvector / SQLite
```

它的关键抽象是 `StorageAdapter` 和 provider factories。Core 不直接绑 OceanBase SDK，LLM/embedder/reranker 也通过 factory 切换。这让 PowerMem 可以走“本地 SQLite/SeekDB”到“企业 OceanBase”的连续部署路径。

适合借鉴的点：

- memory_type / importance_score / retention_strength / next_review 都是 metadata，Intelligence 不直接改库。
- hybrid retrieval 做 adaptive weight normalization，避免多路命中文档天然占优。
- scope/permission/privacy/collaboration 作为组件，而不是后补字段。

主要风险：

- LLM fact extraction 在写入链路前台发生，provider 延迟和失败会影响 add 的体验。
- 配置矩阵大，用户需要理解 provider/storage/rerank/sparse 组合。
- 企业级能力带来更高部署成本。

### [[memsearch]]：Markdown truth + Milvus shadow index

[[memsearch]] 的架构重点是可审计和可重建。它不把 Milvus 当 truth，而是把 `.memsearch/*.md` 作为事实源。

```
hook summary
  → Markdown append
  → scanner/chunker
  → chunk_id(source,line,content,model)
  → Milvus dense + BM25
  → search / expand / transcript
```

这特别适合 coding agent 记忆，因为很多记忆需要人类能看见和修正：之前的设计讨论、踩坑记录、项目约束、用户偏好。Markdown 让 memory 变成 repo-local artifact，而不是黑盒数据库。

适合借鉴的点：

- HTML comments 从 embedding 内容剥离，但原文保留，避免 metadata 污染语义。
- `search → expand → transcript` 保持证据链。
- chunk ID 绑定 embedding model，模型切换不污染旧索引。

主要风险：

- Markdown 结构漂移会影响 anchor 和 expand。
- Milvus/Milvus Lite 仍是额外运行时依赖。
- 自动摘要如果写得太粗，后续检索只能找到粗粒度结论。

### [[tencentdb-agent-memory]]：长期记忆和短期 offload 合并

[[tencentdb-agent-memory]] 最有辨识度的是同时处理两类“记忆”：

- 长期语义记忆：L0/L1/L2/L3。
- 短期任务上下文：tool result offload + Mermaid MMD。

它把召回分成不同注入位置：

```
before_prompt_build
  → L1 dynamic recall as prependContext
  → L2 scene navigation / L3 persona as appendSystemContext
  → memory tools for active drill-down
```

这个设计很工程化：动态 L1 经常变，如果放进 system 前缀容易击穿 prompt cache；L2/L3 更稳定，适合系统上下文。Context offload 则把大工具日志从 prompt 里挪到 `refs/*.md`，只注入 MMD 节点和摘要，让 Agent 需要时按 node_id 下钻。

适合借鉴的点：

- `TdaiCore` host-neutral，OpenClaw 插件和 Hermes sidecar 复用同一管线。
- L0 证据、L1 atom、L2 scene、L3 persona 分层明确。
- pipeline manager 用 threshold/idle/flush/downward-only/global-serial 控制节奏。

主要风险：

- LLM 参与文件改写，必须处理沙箱、备份、半写入恢复。
- L1/L2/L3 多层一致性和 stale propagation 很复杂。
- 宿主生态偏 OpenClaw/Hermes，迁移到其他 agent runtime 需要适配 hook/context 协议。

## 核心难点

### 1. 写入质量：不是所有上下文都值得记住

Agent 的原始上下文充满噪声：命令输出、临时错误、重复尝试、token 统计、日志片段、无效搜索结果。如果系统把这些都写入长期 memory，检索层会被污染。

工程上常见解法：

- [[claude-mem]]：用 LLM observation schema 压缩，只保留 facts/concepts/files。
- [[agentmemory]]：默认启发式压缩 + dedup + privacy stripping。
- [[powermem]]：fact extraction + importance evaluation。
- [[tencentdb-agent-memory]]：L1 batch dedup/update/merge/skip。
- [[memsearch]]：把会话摘要写 Markdown，再通过 maintenance 维护 PROJECT/USER 摘要。

核心判断：memory write 应该是一个 **filtering boundary**，不是日志落盘。

### 2. 延迟隔离：记忆系统不能阻塞 Agent

所有成熟设计都在保护 Agent 主路径：

- Hook 只做轻量接力。
- LLM 压缩、embedding、索引重建放后台。
- search/injection 失败时降级为空记忆。
- rebuild 不阻塞服务启动。
- cache stale 时可以先返回旧 briefing 或 raw context。

如果 memory 系统把每次 tool call 都变成同步 LLM 请求，用户会把它关掉。这也是 [[agentmemory]] 默认零 LLM、context injection 默认关的根本原因。

### 3. 真相与索引一致性：索引必须可丢弃

Memory 系统经常要面对：

- embedding provider 切换导致维度变化。
- chunker 规则变化导致 chunk id 变化。
- LLM 压缩失败或输出格式漂移。
- vector DB 写入成功但 SQLite 写入失败，或反过来。
- watcher/indexer 中途退出。

比较稳的设计是：truth store 明确、index 可重建。[[memsearch]] 的 Markdown truth、[[tencentdb-agent-memory]] 的 JSONL/files truth、[[agent-recall]] 的 SQLite truth 都是这个方向。[[claude-mem]] 的双索引则需要 watermark 和同步状态治理。

### 4. 冲突和时间：长期事实会变

Agent memory 里最危险的是“曾经正确的事实”。例如客户偏好、项目架构、API 版本、负责人、部署路径都会变化。

不同项目的处理方式：

- [[agent-recall]]：bitemporal slots，用 valid_from / valid_to 保存事实历史。
- [[powermem]]：importance/retention/next_review + optimizer 做衰减和晋升。
- [[agentmemory]]：strength decay、auto-forget、consolidation。
- [[tencentdb-agent-memory]]：L1 batch conflict detection + L2/L3 增量改写。

纯向量库很难表达“旧事实已被新事实覆盖”。这就是结构化 metadata、时间字段、scope 和 conflict handling 必须进入核心模型的原因。

### 5. Scope 和权限：多 Agent 不是多一个 user_id

多项目、多客户、多 Agent 的 memory 不能只靠 `user_id` 分库。真实问题包括：

- 一个 entity 在不同 scope 下有不同 facts。
- parent scope 的默认事实可以被 local scope override。
- orchestrator 能看全局，普通 topic agent 只能看局部。
- CLI 管理员和 MCP client 不是同一信任级别。

[[agent-recall]] 的 `MCPBridge` 是最清晰的参考：底层 store 不做权限，MCP 边界做读写过滤。[[powermem]] 则把 scope/permission/privacy/collaboration 做成组件级控制器，更适合企业服务。

### 6. 上下文注入：召回成功不等于应该自动塞进 prompt

自动注入最容易引发三个问题：

- token 成本不可见。
- prompt cache 被动态上下文击穿。
- 旧记忆抢占当前任务注意力。

项目里的几种策略：

- [[agentmemory]]：context injection 默认关。
- [[memsearch]]：启动只提示使用 `$memory-recall`，查询后再 expand。
- [[agent-recall]]：SessionStart 注入 scoped AI briefing，而不是所有 raw facts。
- [[tencentdb-agent-memory]]：L1 动态 prepend，L2/L3 稳定 append，conversation search 主动下钻。
- [[claude-mem]]：auto context + mem-search skill 双轨。

工程判断：默认注入应该短、稳定、可解释；深层证据应该工具化。

### 7. 检索融合：RRF 权重和过滤比模型更难调

Hybrid search 的难点不是“同时跑两路”，而是结果融合后的质量治理：

- BM25 和 vector 分数不可直接比较。
- 有些 query 只有字面命中，有些 query 只有语义命中。
- graph/scope/time 命中应该是过滤、加权还是 rerank。
- reranker 成本和延迟是否值得。
- top-k 长尾是否有足够绝对相似度。

[[powermem]] 的 adaptive weight normalization 是值得注意的细节：按实际命中路径重新归一化权重，避免多路都有结果的文档天然占优。[[agentmemory]] 的 BM25/vector/graph RRF 更轻量，适合本地规模。[[memsearch]] 把 dense/BM25 放到 Milvus hybrid_search，适合把检索复杂度外包给向量数据库。

### 8. 可观测和可恢复：memory 系统需要自己的运维面

一旦 memory 常驻后台，就会出现普通插件没有的问题：

- worker 是否启动。
- queue 是否积压。
- index 是否 stale。
- embedding 维度是否匹配。
- cache 是否过期。
- LLM 压缩失败率如何。
- 哪条记忆被注入了 prompt。
- 某条错误记忆从哪里来。

[[agentmemory]] 的 viewer、metrics、index persistence，[[powermem]] 的 Dashboard/audit/telemetry，[[claude-mem]] 的 worker service/viewer，都是在补这个运维面。Agent Memory 如果没有可观测性，很快会变成“模型偶尔想起一些不知道哪里来的东西”。

## 设计分型

| 分型 | 代表项目 | 架构重心 | 适合场景 |
|------|----------|----------|----------|
| 宿主插件型 | [[claude-mem]], [[tencentdb-agent-memory]] OpenClaw 插件 | hook 生命周期、自动注入、宿主协议 | 给单个 agent runtime 加强记忆 |
| MCP 结构化记忆型 | [[agent-recall]] | tool semantics、scope、entity graph | 多项目/多客户知识保存 |
| 本地常驻 worker 型 | [[agentmemory]] | 多入口、统一服务、viewer、低成本默认 | 多个 coding agent 共享记忆 |
| 应用中间件型 | [[powermem]] | SDK/API、多后端、多租户、provider matrix | 产品化 LLM app / 企业 memory service |
| Markdown truth 型 | [[memsearch]] | 可审计 source-of-truth、可重建索引 | coding agent 历史会话回溯 |
| 分层语义金字塔型 | [[tencentdb-agent-memory]] | L0 证据 → L1 事实 → L2 场景 → L3 画像 | 长期 persona + 短期 offload 合一 |

这些分型可以组合。例如一个理想的 coding agent memory 可能采用：

- [[memsearch]] 的 Markdown truth 和 progressive recall。
- [[agent-recall]] 的 scope/permission 模型。
- [[claude-mem]] 的 hook-worker 异步闭环。
- [[agentmemory]] 的成本默认和本地 viewer。
- [[tencentdb-agent-memory]] 的 context offload。
- [[powermem]] 的 provider/storage adapter 思路。

但不要一开始就把所有能力塞进一个系统。memory 架构最怕的是“写入太宽、检索太黑、注入太猛”。更稳的落地顺序是：

1. 明确 truth store。
2. 做轻量写入和可审计日志。
3. 加 BM25/FTS 搜索。
4. 再加 vector/hybrid。
5. 最后做自动注入和 LLM 压缩。

## 选型建议

| 你的目标 | 优先看 | 工程关注点 |
|----------|--------|------------|
| 只想给 Claude Code 加个人长期记忆 | [[claude-mem]] | hook-worker 边界、SQLite/Chroma 同步、SessionStart 注入 |
| 想要最清晰的本地 SQLite + MCP 结构化记忆 | [[agent-recall]] | scope hierarchy、MCPBridge、bitemporal slots |
| 想让多个 Agent 共用本地服务，并有 REST/MCP/viewer | [[agentmemory]] | iii-engine 总线、默认零 LLM、三流 RRF、index persistence |
| 想把 memory 做成应用中间件或企业服务 | [[powermem]] | StorageAdapter、provider matrix、多租户 controller、hybrid/RRF |
| 想保留 Markdown 事实源，并用 Milvus 做可重建索引 | [[memsearch]] | chunk ID、Markdown anchor、Milvus dense/BM25、expand |
| 想研究 OpenClaw/Hermes 的分层记忆和 context offload | [[tencentdb-agent-memory]] | L0-L3 pipeline、offload refs/MMD、prompt cache 分层注入 |

## 当前知识库缺口

- 还缺少一篇“[[agent-memory]] 2026 项目分型”概念扩展，把以上项目抽象成 taxonomy。
- 还缺少 openclaw / Hermes / OpenCode 的实体页，否则 [[tencentdb-agent-memory]] 和 [[memsearch]] 的宿主生态关系还不完整。
- 可以补一篇“memory system evaluation”分析页，对比 LOCOMO、LongMemEval、Coding-Life 等评测口径。
- 可以补一篇“memory 安全与隐私”分析页，专门整理 scope enforcement、PII stripping、API auth、prompt injection 边界。
- 可以补一篇“memory write semantics”概念页，专门展开自动捕获、主动写入、SDK 写入、Markdown append、分层写入的设计边界。

## 相关页面

- [[agent-memory]]
- [[event-driven-memory-pipeline]]
- [[three-tier-search-protocol]]
- [[ai-as-compressor]]
- [[hybrid-search-rrf]]
- [[claude-mem]]
- [[agent-recall]]
- [[agentmemory]]
- [[powermem]]
- [[memsearch]]
- [[tencentdb-agent-memory]]
