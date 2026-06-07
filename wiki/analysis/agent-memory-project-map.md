---
title: Agent Memory 项目地图
tags: [agent-memory, project-map, ai-agent, llm-infra]
date: 2026-06-07
sources: [src-claude-mem-architecture, src-powermem-architecture, src-agentmemory-architecture, src-agent-recall-architecture, src-memsearch-architecture, src-tencentdb-agent-memory-architecture]
related: [[agent-memory]], [[claude-mem]], [[powermem]], [[agentmemory]], [[agent-recall]], [[memsearch]], [[tencentdb-agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[hybrid-search-rrf]], [[ai-as-compressor]]
---

# Agent Memory 项目地图

这页把当前已摄入的 memory 相关项目横向整理。核心结论：这些项目不是在做同一件事，而是在同一个问题空间里选择了不同的事实源、宿主入口、压缩成本和检索治理边界。

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
| 事实源 | SQLite observations | SQLite entities/slots/relations | iii-engine SQLite KV | OceanBase / SeekDB / pgvector / SQLite | `.memsearch/*.md` Markdown | JSONL records + SQLite/TCVDB |
| 采集方式 | lifecycle hooks 自动采集 tool log | MCP tools 主动写入 + hooks | hooks/REST/MCP 统一进 worker | app 调用 `Memory.add()` 或插件 hook | 平台插件写 Markdown | before/after hook + sidecar |
| 压缩策略 | 后台 LLM 压成 structured observations | raw context → AI briefing cache | 默认零 LLM 启发式，可选 LLM 压缩 | LLM fact extraction + importance eval | daily/PROJECT/USER maintenance | L0→L1→L2→L3 多级 LLM 管线 |
| 检索 | SQLite FTS5 + Chroma vector | SQLite FTS5/LIKE + scope filter | BM25 + Vector + Graph + RRF | Vector + FTS + sparse + graph + RRF | Milvus dense + BM25 + RRF | SQLite FTS/vector/RRF 或 TCVDB hybrid |
| 注入方式 | SessionStart auto context + mem-search skill | SessionStart AI briefing | context injection 可配置 + MCP tools | API/search 返回给应用或插件注入 | search → expand → transcript | prepend L1 + append L2/L3 + tool search |
| 主要强项 | Claude Code 集成自然，模式清晰 | scope hierarchy 和 bitemporal facts | 多入口、多工具、viewer、零 LLM 默认 | 后端/provider/部署形态最完整 | Markdown 可审计，可重建索引 | 分层记忆 + context offload 合一 |
| 主要代价 | 生态偏 Claude Code | 向量/语义能力较轻 | iii-engine 依赖和工具面较大 | 部署/配置复杂度更高 | 依赖 Milvus 路径和索引维护 | 管线复杂、宿主偏 OpenClaw/Hermes |

## 设计轴

### 1. 事实源：谁是 source of truth

- [[memsearch]] 的真相是 Markdown，Milvus 只是可重建 shadow index。这个模式最适合“人也要能直接审计/编辑记忆”的 coding agent 场景。
- [[agent-recall]] 和 [[claude-mem]] 的真相是本地 SQLite，前者偏结构化 graph/fact，后者偏压缩后的 observations。
- [[powermem]] 的真相在可替换存储后端，默认走 OceanBase/SeekDB，目标是中间件化而不是单插件。
- [[tencentdb-agent-memory]] 把 JSONL 当恢复材料，把 SQLite/TCVDB 当检索引擎；这种“双轨”比单纯向量库更抗数据损坏。

### 2. 写入：自动捕获还是主动记忆

- 自动捕获：[[claude-mem]]、[[agentmemory]]、[[memsearch]]、[[tencentdb-agent-memory]] 都依赖宿主 hook，把 tool log / transcript 变成记忆材料。
- 主动写入：[[agent-recall]] 更强调 MCP tools 和 server instructions，让 Agent 主动保存 people、decisions、facts、context。
- 应用写入：[[powermem]] 更像 SDK/API 中间件，应用明确调用 add/search/list/delete。

结论：自动捕获适合 coding agent；主动写入适合长期知识图谱；应用写入适合产品化 LLM app。

### 3. 压缩：LLM 成本怎么处理

- [[claude-mem]] 和 [[powermem]] 典型体现 [[ai-as-compressor]]：先花一次便宜模型成本，把噪声日志压成 facts/concepts，后续检索持续受益。
- [[agentmemory]] 反向选择“零 LLM 默认”，用启发式压缩降低用户不可见成本；LLM 压缩变成显式开关。
- [[agent-recall]] 把 AI 用在 briefing cache，不把 LLM 输出当真相层。
- [[tencentdb-agent-memory]] 是最激进的多级压缩：L1 atom、L2 scenario、L3 persona，再叠加 context offload。

### 4. 检索：单一路径已经不够

这些项目共同收敛到 [[hybrid-search-rrf]]：关键词/BM25 抓文件名、命令、专有名词；dense vector 抓语义；graph/scope/time metadata 负责结构约束。差异在于后端：

- 轻量本地：SQLite FTS5、内存 vector、sqlite-vec。
- 本地但可扩展：Milvus Lite / Server。
- 企业/云端：OceanBase、Tencent Cloud VectorDB、Zilliz Cloud。

### 5. 返回上下文：先摘要，再下钻

[[three-tier-search-protocol]] 是共同方向：

- [[claude-mem]]：search → timeline → get_observations。
- [[memsearch]]：search snippets → expand full section → transcript anchor。
- [[tencentdb-agent-memory]]：L3/L2 给导航，L1 给相关 atom，原始 L0 可用 conversation search 下钻。

这比“top-K 全文一次塞进 prompt”稳定得多。

## 选型建议

| 你的目标 | 优先看 |
|----------|--------|
| 只想给 Claude Code 加个人长期记忆 | [[claude-mem]] |
| 想要最清晰的本地 SQLite + MCP 结构化记忆 | [[agent-recall]] |
| 想让多个 Agent 共用本地服务，并有 REST/MCP/viewer | [[agentmemory]] |
| 想把 memory 做成应用中间件或企业服务 | [[powermem]] |
| 想保留 Markdown 事实源，并用 Milvus 做可重建索引 | [[memsearch]] |
| 想研究 OpenClaw/Hermes 的分层记忆和 context offload | [[tencentdb-agent-memory]] |

## 当前知识库缺口

- 还缺少一篇“[[agent-memory]] 2026 项目分型”概念扩展，把以上项目抽象成 taxonomy。
- 还缺少 openclaw / Hermes / OpenCode 的实体页，否则 [[tencentdb-agent-memory]] 和 [[memsearch]] 的宿主生态关系还不完整。
- 可以补一篇“memory system evaluation”分析页，对比 LOCOMO、LongMemEval、Coding-Life 等评测口径。
- 可以补一篇“memory 安全与隐私”分析页，专门整理 scope enforcement、PII stripping、API auth、prompt injection 边界。

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
