---
title: PowerMem 架构与设计思路分析
tags: [architecture, ai-infra, memory-layer, oceanbase, llm-agents, vector-search]
date: 2026-05-14
sources: [powermem-architecture-analysis.md]
related: [[powermem]], [[oceanbase]], [[ebbinghaus-forgetting-curve]], [[hybrid-search-rrf]], [[claude-code-plugin]], [[mcp]]
---

# PowerMem 架构与设计思路分析

> 原文：`raw/powermem-architecture-analysis.md` · 仓库：https://github.com/oceanbase/powermem · 分析版本 v1.1.1（commit `2c83b77`，2026-05-13）

## 一句话定位

[[powermem]] 是 [[oceanbase]] 团队开源的、面向 LLM agents/apps 的 **持久化记忆中间件**：把对话流水线压缩成可被语义检索的长期记忆。关键手段是 **向量 + 全文 + 稀疏向量 + 图谱** 四路混合检索（OceanBase 原生支持）+ **LLM 驱动的事实抽取/更新** + **[[ebbinghaus-forgetting-curve]] 衰减**。SDK / CLI（`pmem`）/ FastAPI 服务 + Dashboard / [[mcp]] 服务 / VS Code 扩展 / [[claude-code-plugin]] **共用同一份 `.env`**；默认后端是 OceanBase，也支持 pgvector / SQLite / 嵌入式 SeekDB。在 LOCOMO 长对话评测上比"塞满上下文"方案准确率 78.7% vs 52.9%、p95 1.44s vs 17.12s、token 0.9k vs 26k。

## 核心架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│  External Layer:  Multi-Agents · Human Users                        │
│                   (LangChain / LangGraph / Cursor / Claude Code …)  │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│  API Layer                                                          │
│  ┌────────────┐ ┌────────────┐ ┌──────────────┐ ┌────────────────┐ │
│  │ Python SDK │ │ CLI (pmem) │ │ HTTP /api/v1 │ │ MCP (sse/stdio)│ │
│  │ Memory()   │ │ memory add │ │  FastAPI     │ │  powermem-mcp  │ │
│  │ Async      │ │ search …   │ │ + Dashboard  │ │ HTTP/stream    │ │
│  └─────┬──────┘ └─────┬──────┘ └──────┬───────┘ └────────┬───────┘ │
│        └──────────────┴───────────────┴──────────────────┘         │
│                              ↓ 同一份 .env / MemoryConfig          │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Core Layer  (src/powermem/core/)                                   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Memory / AsyncMemory  (memory.py 2178 行,  CRUD 入口)        │  │
│  │   ├─ StorageAdapter / SubStorageAdapter  → routing            │  │
│  │   ├─ IntelligenceManager → IntelligentMemoryManager           │  │
│  │   │     ├─ ImportanceEvaluator (LLM 打分 0.0-1.0)             │  │
│  │   │     └─ EbbinghausAlgorithm  R = e^(-t/S)                  │  │
│  │   ├─ TelemetryManager · AuditLogger                            │  │
│  │   └─ MemoryOptimizer (后台衰减/晋升/清理)                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ↓                                      │
│  Agent Layer (src/powermem/agent/) ─ scope / permission / privacy   │
│  User-Memory (src/powermem/user_memory/) ─ profile + query_rewrite  │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Model Layer  (src/powermem/integrations/)                          │
│  ┌─────────────────┐  ┌────────────────────┐  ┌────────────────┐   │
│  │ LLMFactory      │  │ EmbedderFactory    │  │ RerankFactory  │   │
│  │ openai/anthro   │  │ openai/qwen/gemini │  │ qwen/jina/zai  │   │
│  │ pic/qwen/gemini │  │ huggingface/ollama │  │ generic        │   │
│  │ deepseek/zai/   │  │ azure_openai/bedr  │  │                │   │
│  │ siliconflow/vll │  │ ock/lmstudio/sili  │  │ + SparseEmb    │   │
│  │ m/ollama/lang…  │  │ conflow/together…  │  │ (qwen_sparse)  │   │
│  └─────────────────┘  └────────────────────┘  └────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────────────┐
│  Storage Layer  (src/powermem/storage/)                             │
│  ┌────────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │
│  │ OceanBase      │  │ pgvector    │  │ SQLite (sqlite_vector_   │ │
│  │ (default)      │  │ (PostgreSQL)│  │  store.py — file 单实例) │ │
│  │ + Embedded     │  │             │  │                          │ │
│  │   SeekDB       │  │             │  │                          │ │
│  │ + Graph Store  │  │             │  │                          │ │
│  │ (oceanbase_    │  │             │  │                          │ │
│  │  graph.py)     │  │             │  │                          │ │
│  └────────────────┘  └─────────────┘  └──────────────────────────┘ │
│        Vector (HNSW/HNSW_SQ/IVFFLAT/IVFSQ/IVFPQ)                    │
│        + Full-text (jieba/ngram/ngram2/ik/beng/space)               │
│        + Sparse Vector + Graph (3-hop traversal)                    │
└─────────────────────────────────────────────────────────────────────┘
```

### 记忆生命周期（沿用官方 docs/architecture/overview.md 原图）

```
        New Information Input
              ↓
        Temporary Storage
              ↓
         Working Memory
             ↓
    AI Intelligent Evaluation / Multi-dimensional Analysis
             ↓
    Periodicity Evaluation
             ↓
     Importance Evaluation
             ↓
    ┌────────┴──────────────────┐
    │                           │
┌───┴──────┐  ┌────────-─┐  ┌──────────┐
│ Medium   │  │   High   │  │   Low    │
│Importance│  │Importance│  │Importance│
└───┬──────┘  └───┬─-──-─┘  └────┬─────┘
    │             │              │
    │      ┌──────┴──────┐       │
    │      │Reinforcement│       │
    │      │  Learning   │       │
    │      └──────┬──────┘       │
    │      ┌──────┴──────┐       │
    │      │ Importance  │       │
    │      │  Increase   │       │
    │      └──────┬──────┘       │
    │      ┌──────┴──────┐       │
    │      │Long-term    │       │
    │      │   Memory    │       │
    │      └──────┬──────┘       │
    │      ┌──────┴──────┐       │
    │      │  Permanent  │       │
    │      │   Storage   │       │
    │      └──────┬──────┘       │
    │      ┌──────┴──────┐       │
    │      │ Knowledge   │       │
    │      │    Base     │       │
    │      └─────────────┘       │
    │                  ┌─────────┴─────────┐
    │                  │  Forgetting Decay │
    │                  └─────────┬─────────┘
    │                  ┌─────────┴─────────┐
    │                  │  Importance       │
    │                  │   Decrease        │
    │                  └─────────┬─────────┘
    │                  ┌─────────┴─────────┐
    │                  │  Automatic        │
    │                  │    Cleanup        │
    │                  └───────────────────┘
┌───┴─────-─────────┐
│  Short-term       │
│    Memory         │
└───────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| **API · Python SDK** | 公开 `Memory` / `AsyncMemory` / `create_memory(auto_config())`；CRUD 主循环；装配所有子组件 |
| **API · CLI (`pmem`)** | `pmem memory add/search/list/delete`、`pmem config init`、`pmem shell` REPL |
| **API · HTTP Server** | FastAPI；启动期 lifespan 初始化 service 单例；CORS / 限流 / API key |
| **API · [[mcp]]** | 独立包 `powermem-mcp`（`uvx powermem-mcp sse`），sse/stdio/streamable-http 三种 transport |
| **Core · Memory Engine** | 配置归一化；模块级 3-worker 线程池跑后台任务 |
| **Core · Intelligence** | LLM 重要性打分；[[ebbinghaus-forgetting-curve]] 衰减（`R = e^(-t/S)`，阈值 0.3/0.6/0.8）；离线晋升/清理；插件点 |
| **Core · Agent 多租户** | 5 种 scope；scope/permission/privacy/collaboration 4 个 Controller；3 种 implementation |
| **Core · User Memory** | 用户档案抽取；基于档案的查询改写 |
| **Prompts** | 集中托管所有 LLM prompt；支持 `custom_*_prompt` 配置覆盖 |
| **Model · LLM** | 12 provider：openai / anthropic / qwen / gemini / deepseek / ollama / vllm / langchain / azure / siliconflow / zai / qwen_asr |
| **Model · Embedder** | 15 provider + sparse：openai / qwen / gemini / vertexai / huggingface / ollama / azure_openai / aws_bedrock / lmstudio / langchain / together / siliconflow / zai / mock + sparse(qwen_sparse) |
| **Model · Rerank** | 4 provider：qwen / jina / zai / generic |
| **Storage · 适配层** | `VectorStoreBase` 抽象；`StorageAdapter` / `SubStorageAdapter`（sub-store 路由）；Factory 创建后端 |
| **Storage · [[oceanbase]]** | 5 种向量索引（HNSW/HNSW_SQ/IVFFLAT/IVFSQ/IVFPQ）；5 种 FTS parser；[[hybrid-search-rrf]]；Snowflake ID；REPLACE INTO upsert；3-hop graph |
| **Storage · pgvector / SQLite** | PostgreSQL 中型部署 / 单机文件部署（开发测试默认） |
| **Apps · [[claude-code-plugin]]** | Go 二进制 `powermem-hook` + bash/PowerShell wrapper + `hooks.json`；HTTP 模式默认；`UserPromptSubmit` hook 自动检索注入 |
| **Apps · VS Code 扩展** | "Link to AI tools" 把 PowerMem 接到 Cursor / Claude / Codex / Copilot / Windsurf |
| **Dashboard** | React 19 + TanStack Router + Tailwind 4 + Radix UI；构建产物嵌入 server wheel，挂载到 `/dashboard/` |
| **Benchmark** | LOCOMO 长对话评测；`benchmark/server` 评测服务 |
| **Examples** | go / langchain / langgraph / moonbit 跨语言跨框架接入示例 |

**分层关键约束**：

- **API 层不持状态**：所有 service 在 lifespan 起点初始化为 `app.state.*_service` 单例；HTTP / CLI / SDK 都最终经过同一个 `Memory` 实例。
- **Core 与 Storage 通过 Adapter 隔离**：`StorageAdapter` 持有 `vector_store + embedding_service + sparse_embedder_service`；Core 不直接调用 OceanBase SDK。新增后端只需实现 `VectorStoreBase`。
- **Intelligence 不直接改库**：[[ebbinghaus-forgetting-curve]] 把 `importance_score / retention_strength / next_review` 写进 metadata JSON 列；`MemoryOptimizer` 离线扫描决定晋升/清理。
- **Prompts 集中托管**：运行时可通过 `custom_fact_extraction_prompt` / `custom_update_memory_prompt` / `custom_importance_evaluation_prompt` 覆盖。

## 关键数据流

```
┌──────────────┐         (1) prompt + user_id/agent_id/run_id
│ Agent/User   │ ───────────────────────────────┐
└──────────────┘                                ↓
                                      ┌──────────────────────┐
                                      │   Memory.add()       │
                                      │ core/memory.py       │
                                      └──────┬───────────────┘
                                             │ (2) FACT_EXTRACTION_PROMPT
                                             ↓
                                      ┌──────────────────────┐
                                      │  LLM (factory)       │  ← integrations/llm
                                      │  抽取事实条目 list   │
                                      └──────┬───────────────┘
                                             │ (3) facts[]
                                             ↓
                                      ┌──────────────────────┐
                                      │ IntelligenceManager  │
                                      │  ImportanceEvaluator │  → 0.0~1.0
                                      │  EbbinghausAlgorithm │  → memory_type
                                      └──────┬───────────────┘
                                             │ (4) enriched metadata
                                             ↓
                                      ┌──────────────────────┐
                                      │ Embedder.embed()     │  dense
                                      │ SparseEmbedder.…()   │  sparse (optional)
                                      └──────┬───────────────┘
                                             │ (5) vector(s)
                                             ↓
                                      ┌──────────────────────┐
                                      │ StorageAdapter       │
                                      │  _route_to_store()   │  ← sub_stores
                                      └──────┬───────────────┘
                                             │ (6) REPLACE INTO (upsert)
                                             ↓                Snowflake ID
                                  ┌─────────────────────────┐
                                  │  OceanBase VectorStore  │
                                  │  (+ Graph: 实体/关系)   │
                                  └─────────────────────────┘

╭────────────────── 检索路径 (memory.search) ────────────────────╮
                                                                 │
   query ──► (1) UserMemory.query_rewrite (LLM 改写)             │
              ↓                                                  │
   ┌──── 并发三路 (ThreadPoolExecutor) ────┐                     │
   │                                       │                     │
   ▼                                       ▼                     ▼
 Vector search          Full-text search (FTS)          Sparse vector
 (HNSW/IVFFLAT)         (jieba/ngram/ik …)              (qwen_sparse)
   │                                       │                     │
   └──────────────┬────────────────────────┴─────────────────────┘
                  ↓
         RRF (Reciprocal Rank Fusion, k=60)
         score = Σ weight_i * 1/(k + rank_i)
         + Adaptive Weight Normalization (混合状态公平性修正)
                  ↓
         Ebbinghaus 衰减系数加权
                  ↓
         Reranker (optional, qwen/jina/zai)
                  ↓
         Top-K (heap-based, threshold filter)
                  ↓
         返回 results + scores + metadata
```

**回退路径**：embedder 失败 → mock `[0.1] * 1536` 向量；LLM 抽取失败 → 容错跳过单条 fact；reranker 配置失败 → 退化为纯 RRF；storage service 启动失败 → API route 抛 503。

## 设计决策与哲学

- **持久记忆做成跨形态统一中间件**：一个 `.env` 同时供 SDK / CLI / FastAPI / [[mcp]] / Dashboard / [[claude-code-plugin]] / VS Code 扩展使用 —— 不复制状态给每个客户端，这是它能同时铺到 SDK / IDE / Agent 框架的关键。
- **认知科学抽象 + 数学公式解耦存储**：working / short_term / long_term 三层 + [[ebbinghaus-forgetting-curve]] `R = e^(-t/S)`。Intelligence 不直接改库，只在 metadata 写分数，`MemoryOptimizer` 离线扫描 —— 避免"每次写入都触发昂贵 LLM 调用"。
- **[[oceanbase]] 优先但绝不绑死**：`VectorStoreFactory + StorageAdapter` 是关键解耦点；v1.1.0 引入嵌入式 SeekDB（`pyseekdb`）让用户用 OceanBase 语义但零部署。
- **[[hybrid-search-rrf]] + 自适应权重是检索灵魂**：3 路（向量/全文/稀疏）并发，`score = Σ w_i × 1/(60 + rank_i)`，`_normalize_weights_adaptively` 按实际命中路径重新归一权重，避免"全命中 doc 因权重总和大而占优"的不公平 —— 这是 LOCOMO 78.7% 准确率的算法贡献。
- **后台线程池是 perf 关键**：模块级 `_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=3)`；LLM 抽取前台同步，telemetry/audit/optimization 后台跑 —— 解释了 p95 = 1.44s（vs baseline 17.12s 的 11.8 倍提速）。
- **插件式 Provider 矩阵 + pydantic-settings**：15 embedder + 12 LLM + 4 reranker；用户切换只改 `.env` 里的 provider —— 是它能跑通"Qwen + DashScope + OceanBase 全栈国产化"路径的工程基础。
- **Multi-agent 是组件级别**：`scope/permission/privacy/collaboration` 4 个 Controller；5 种 scope（private/agent_group/user_group/public/restricted）—— 是 enterprise tenant isolation 的基建。
- **Dashboard 打包进 Python wheel**：`pip install powermem` + `powermem-server` 一条命令就有完整 Web UI，无需单独部署前端。
- **[[claude-code-plugin]] 用 Go 二进制做 hook**：跨平台原生编译，无 Python 依赖；`UserPromptSubmit` hook 自动检索注入 `additionalContext` —— 让 Claude Code 用户"不需要写 prompt 也能用上长期记忆"。

## 关键组件深入解读

### `storage/oceanbase/oceanbase.py` 的 [[hybrid-search-rrf]] 融合

`_reciprocal_rank_fusion`（`oceanbase.py:1626-1740`）三路 RRF 累加（k=60）：

- 命中已有 doc → 累加 `rrf_score`；只命中单路 → 单路得分新增 doc；
- `_normalize_weights_adaptively` 按实际参与路径重新归一化权重；
- 用 `heap` 维护 Top-K（避免全排序）；
- `_calculate_quality_score` 用原始 similarity 做阈值过滤，避免 RRF 排名高但绝对相似度低的长尾噪声。

## 相关页面

- [[powermem]]
- [[oceanbase]]
- [[ebbinghaus-forgetting-curve]]
- [[hybrid-search-rrf]]
- [[claude-code-plugin]]
- [[mcp]]
