# PowerMem 架构与设计思路分析

> 仓库：https://github.com/oceanbase/powermem · 分析日期：2026-05-14 · 版本：v1.1.1（commit `2c83b77`，2026-05-13）

## 一句话定位

PowerMem 是 OceanBase 团队开源的、面向 LLM agents/apps 的 **持久化记忆中间件**：把对话流水线压缩成可被语义检索的长期记忆。关键手段是 **向量 + 全文 + 稀疏向量 + 图谱** 四路混合检索（OceanBase 原生支持）+ **LLM 驱动的事实抽取/更新** + **艾宾浩斯遗忘曲线衰减**。SDK / CLI（`pmem`）/ FastAPI 服务 + Dashboard / MCP 服务 / VS Code 扩展 / Claude Code 插件 **共用同一份 `.env`**；默认后端是 OceanBase，也支持 pgvector / SQLite / 嵌入式 SeekDB。在 LOCOMO 长对话评测上比"塞满上下文"方案准确率 78.7% vs 52.9%、p95 1.44s vs 17.12s、token 0.9k vs 26k。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| **API · Python SDK** | `src/powermem/__init__.py`, `core/memory.py` (2178 行), `core/async_memory.py`, `core/base.py` | 公开 `Memory` / `AsyncMemory` / `create_memory(auto_config())`；CRUD 主循环；装配所有子组件 |
| **API · CLI** | `src/powermem/cli/main.py` | `pmem memory add/search/list/delete`、`pmem config init`、`pmem shell` REPL（Click 框架） |
| **API · HTTP Server** | `src/server/main.py`, `src/server/api/v1/{memories,search,agents,users,system}.py`, `services/`, `middleware/{auth,rate_limit,logging,error_handler}.py` | FastAPI；启动期 lifespan 初始化 `MemoryService/SearchService/UserService/AgentService` 单例；CORS / 限流 / API key |
| **API · MCP** | 独立包 `powermem-mcp`（`uvx powermem-mcp sse`），仓库本体不含源码（独立发布） | sse / stdio / streamable-http 三种 transport |
| **Core · Memory Engine** | `src/powermem/core/{memory,async_memory,base,setup,telemetry,audit}.py` | 配置归一化（兼容旧 `database`/`embedding` 字段）；模块级 `_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=3)` 跑后台任务 |
| **Core · Intelligence** | `src/powermem/intelligence/{intelligent_memory_manager,importance_evaluator,ebbinghaus_algorithm,memory_optimizer,plugin,manager}.py` | LLM 重要性打分（0.0-1.0）；Ebbinghaus 衰减（`R = e^(-t/S)`，阈值 0.3/0.6/0.8）；离线晋升 / 清理；`IntelligentMemoryPlugin` / `EbbinghausIntelligencePlugin` 插件点 |
| **Core · Agent 多租户** | `src/powermem/agent/{abstract,components,factories,implementations,wrappers,types.py}` | 5 种 scope（private/agent_group/user_group/public/restricted）；scope/permission/privacy/collaboration 4 个 Controller；3 种 implementation（multi_agent / multi_user / hybrid） |
| **Core · User Memory** | `src/powermem/user_memory/{user_memory,query_rewrite/rewriter,storage/user_profile*}.py` | 用户档案抽取；基于档案的查询改写（profile-based query rewrite） |
| **Prompts** | `src/powermem/prompts/{intelligent_memory_prompts,importance_evaluation,user_profile_prompts,query_rewrite_prompts,graph,templates,optimization_prompts}.py` | 集中托管所有 LLM prompt；支持 `custom_*_prompt` 配置覆盖（v0.x → v1.1+ 演进重点） |
| **Model · LLM** | `src/powermem/integrations/llm/` — 12 provider | openai / anthropic / qwen / gemini / deepseek / ollama / vllm / langchain / azure / siliconflow / zai / qwen_asr |
| **Model · Embedder** | `src/powermem/integrations/embeddings/` — 15 provider + sparse | openai / qwen / gemini / vertexai / huggingface / ollama / azure_openai / aws_bedrock / lmstudio / langchain / together / siliconflow / zai / mock + sparse(qwen_sparse) |
| **Model · Rerank** | `src/powermem/integrations/rerank/` — 4 provider | qwen / jina / zai / generic |
| **Storage · 适配层** | `src/powermem/storage/{adapter,factory,base,migration_manager}.py` | `VectorStoreBase` 抽象接口；`StorageAdapter` / `SubStorageAdapter`（sub-store 路由）；`VectorStoreFactory` / `GraphStoreFactory` |
| **Storage · OceanBase** | `src/powermem/storage/oceanbase/{oceanbase,oceanbase_graph,models,constants}.py` (oceanbase.py 2424 行) | 5 种向量索引（HNSW/HNSW_SQ/IVFFLAT/IVFSQ/IVFPQ）；5 种 FTS parser（jieba/ngram/ngram2/ik/beng/space）；RRF 融合；Snowflake ID；REPLACE INTO upsert；3-hop graph |
| **Storage · pgvector** | `src/powermem/storage/pgvector/pgvector.py` | PostgreSQL + pgvector；HNSW / DiskANN；开发/中型部署 |
| **Storage · SQLite** | `src/powermem/storage/sqlite/{sqlite,sqlite_vector_store}.py` | 单机文件部署；WAL；开发/测试默认 |
| **Apps · Claude Code 插件** | `apps/claude-code-plugin/` Go 二进制 `powermem-hook` + bash/PowerShell wrapper + `hooks.json` + `skills/{remember,recall}/SKILL.md` | HTTP 模式默认（`POST /api/v1/memories`）；MCP 模式可选；`UserPromptSubmit` hook 自动检索注入 `additionalContext` |
| **Apps · VS Code 扩展** | `apps/vscode-extension/src/{extension,chat/participant,writers/{cursor,claude,copilot,codex,windsurf},panels/DashboardPanel}.ts` | "Link to AI tools" 把 PowerMem 接到 5 种 IDE/Agent 工具链 |
| **Dashboard** | `dashboard/` (React 19 + TanStack Router + Tailwind 4 + Radix UI + i18next + recharts) routes: `index/memories/settings/user-profile` | Web UI；构建产物嵌入 server package（`pyproject.toml` `[tool.setuptools.package-data] server = ["dashboard/**"]`），FastAPI 挂载到 `/dashboard/` |
| **Benchmark** | `benchmark/locomo/{evals,run_experiments,generate_scores,prompts,run.sh}` + `methods/` + `metrics/` + `dataset/` | LOCOMO 长对话评测；`benchmark/server` 评测服务 |
| **Examples** | `examples/{go,langchain,langgraph,moonbit}` | 跨语言/跨框架接入示例（医疗 chatbot、客服 bot 等） |

**分层关键约束**：

- **API 层不持状态**：所有 service 在 lifespan 起点初始化为 `app.state.*_service` 单例（`server/main.py:34-55`）；HTTP / CLI / SDK 都最终经过同一个 `Memory` 实例。
- **Core 与 Storage 通过 Adapter 隔离**：`StorageAdapter` 持有 `vector_store + embedding_service + sparse_embedder_service`；Core 不直接调用 OceanBase SDK。新增后端只需实现 `VectorStoreBase`。
- **Intelligence 不直接改库**：Ebbinghaus 把 `importance_score / retention_strength / next_review` 写进 metadata JSON 列；`MemoryOptimizer` 离线扫描决定晋升/清理。
- **Prompts 集中托管**：所有提示词在 `src/powermem/prompts/`，运行时可通过 `custom_fact_extraction_prompt` / `custom_update_memory_prompt` / `custom_importance_evaluation_prompt` 覆盖（v1.1.1 commit `c99430a` 加了 env var 支持）。

## 关键数据流

### `memory.add()` → `memory.search()` 端到端

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

### 错误传递 / 回退路径

- **Embedder 失败**：`StorageAdapter.add_memory:73-81` 退化到 `[0.1] * 1536` mock 向量 + warning log（生产环境需自行加告警）。
- **LLM 抽取失败**：`utils.utils.llm_json_text_with_fallback` + `parse_fact_extraction_json` 容错；解析失败则跳过该条 fact，整个 add 调用不抛错（保证后台 hook 流不阻断主流程）。
- **Reranker 配置失败**：`core/memory.py:200-214` catch 后置 `reranker = None`；search 退化为纯 RRF 排序。
- **Storage service 启动失败**：FastAPI lifespan 把 `app.state.memory_service = None`，每个 API route 检查后抛 `503` `ErrorCode.INTERNAL_ERROR`（`api/v1/memories.py:34-44`），不让请求卡死。
- **Sub-stores 配置但非 OceanBase**：`core/memory.py:307-309` warning + 退化为基本 `StorageAdapter`。

## 设计决策与哲学

- **"持久记忆"做成跨形态统一中间件**：一个 `.env`、一个 `MemoryConfig` 同时供 SDK / CLI / FastAPI Server / MCP Server / Dashboard / Claude Code 插件 / VS Code 扩展使用（`pyproject.toml:104-107` 注册了 `powermem-server` 和 `pmem` 两个 entry point；Claude plugin 直接 `POST /api/v1/memories`）。不复制一份配置/状态给每个客户端 —— 这是它能同时铺到 SDK / IDE / Agent 框架的关键。

- **认知科学抽象（working / short_term / long_term）+ Ebbinghaus 数学公式**：`R = e^(-t/S)` 实现在 `intelligence/ebbinghaus_algorithm.py:31-43`，暴露 `decay_rate=0.1` / `reinforcement_factor=0.3` / 三阈值 `0.3 / 0.6 / 0.8`。**Intelligence 与 Storage 解耦** —— Ebbinghaus 不直接改库，只在 metadata 里写 `intelligence.importance_score / next_review / retention_strength`，`MemoryOptimizer` 离线扫描决定晋升/清理。这避免了"每次写入都触发昂贵的 LLM 调用"。

- **OceanBase 优先但绝不绑死**：`VectorStoreFactory + StorageAdapter` 是关键解耦点。OceanBase 后端集中了 5 种向量索引、5 种 FTS parser、稀疏向量、3-hop 图遍历（`storage/oceanbase/oceanbase.py:43-77`）。SQLite/pgvector 后端只覆盖基础向量搜索，是开发/测试退路。**v1.1.0 引入嵌入式 SeekDB（`pyseekdb` 依赖）**，让用户用 OceanBase 语义但不部署 OceanBase 服务 —— 这是把"企业级"产品下放到"零依赖 pip install"的关键一步。

- **RRF + 自适应权重是检索的灵魂**：3 路（向量/全文/稀疏）并发后用 RRF 融合 `score = w_i × 1/(60 + rank_i)`（`oceanbase.py:1633-1701`）。更妙的是 `_normalize_weights_adaptively`：当某条 doc 只被部分路径命中时，按实际参与路径重新归一化权重，避免"全命中的 doc 因为权重总和大而占优"的不公平。这是 LOCOMO 78.7% 准确率的核心算法贡献。

- **后台线程池是 perf 关键**：模块级 `_BACKGROUND_EXECUTOR = ThreadPoolExecutor(max_workers=3)`（`core/memory.py:51`）。LLM 抽取/重要性评估在前台同步等，但 telemetry/audit/optimization/异步写入辅路在后台跑 —— 这解释了 LOCOMO p95 = 1.44s（vs baseline 17.12s 的 11.8 倍提速），同时 token 用量从 ~26k 降到 ~0.9k（28 倍）。

- **插件式 Provider 矩阵 + pydantic-settings 同名 env**：15 个 embedder、12 个 LLM、4 个 reranker，每个 provider 一个文件 + 一个 config 类（`integrations/llm/config/*.py`）。新增 provider 只要继承 base + 注册到 factory；用户切换只改 `.env` 里的 `LLM_PROVIDER=qwen`。这是它在国内能跑通"Qwen + DashScope + OceanBase 全栈国产化"路径的工程基础。

- **Multi-agent 不是注解级别，是组件级别**：`agent/abstract/{scope,permission,privacy,collaboration}.py` + 3 种 implementation。`Memory` 接收 `agent_id` 后所有读写都过 `ScopeController` / `PermissionController`，是 enterprise tenant isolation 的基建。

- **Dashboard 打包进 Python wheel**：`pyproject.toml` `[tool.setuptools.package-data] server = ["dashboard/**"]`；FastAPI lifespan 用 `StaticFiles` 挂载 `/dashboard/`（`server/main.py:90-98`）。这意味着 `pip install powermem` + `powermem-server` 一条命令就有完整 Web UI，无需单独部署前端 —— 显著降低用户上手摩擦。

- **Claude Code 插件用 Go 二进制做 hook**：`apps/claude-code-plugin/cmd/powermem-hook/` 编译出 `powermem-hook-{darwin,linux,windows}-{amd64,arm64}`，配合 bash/PowerShell wrapper 注册到 `hooks.json`。默认 HTTP 模式（hooks 直接 `POST /api/v1/memories`）；MCP 模式可选。**`UserPromptSubmit` hook 自动检索注入 `additionalContext`**（`POWERMEM_PROMPT_SEARCH=0` 关闭）—— 让 Claude Code 用户"不需要写 prompt 也能用上长期记忆"。

## 关键组件深入解读

### `core/memory.py` 的 `Memory` 类装配过程

`Memory.__init__` 接收 dict 或 `MemoryConfig`（pydantic），`_auto_convert_config:54-102` 兼容旧 `database`/`embedding` 字段（从早期 mem0 fork 演化而来）。装配步骤：

1. 通过 `VectorStoreFactory.create(storage_type, vector_store_config)` 拿到 vector store 实例（`memory.py:217-224`）；
2. 如果 `enable_graph` → `GraphStoreFactory.create(provider, config)` 拿到 graph store（默认 OceanBase）；
3. `LLMFactory.create(llm_provider, llm_config)` + 可选 `audio_llm`（多模态音频转录用，独立配置）；
4. `EmbedderFactory.create` 传入 `vector_store_config` 以便 mock embedder 推断维度；
5. 如果 `include_sparse=True` 且后端是 OceanBase → 创建 `SparseEmbedder`（仅 OceanBase 支持稀疏向量）；
6. 根据 `sub_stores` 配置选 `StorageAdapter` 或 `SubStorageAdapter`（`memory.py:299-310`）；
7. 创建 `IntelligenceManager(self.config)` → 内部根据 `intelligent_memory.enabled` 决定是否初始化 `IntelligentMemoryManager`（默认 `False`，向后兼容）；
8. `TelemetryManager` / `AuditLogger` 在线程池里跑（不阻塞主流程）。

### `storage/oceanbase/oceanbase.py` 的 RRF 融合

`_reciprocal_rank_fusion`（`oceanbase.py:1626-1740`）的核心：

```python
# 三路 RRF 累加（k=60）
for rank, result in enumerate(vector_results, 1):
    rrf_score = vector_w * (1.0 / (k + rank))
    all_docs[result.id] = {... 'rrf_score': rrf_score}

# FTS / Sparse 路径如果命中已有 doc，累加 rrf_score；
# 没命中则新增 doc，rrf_score = 单路得分

# 关键修正：自适应权重归一化
all_docs = self._normalize_weights_adaptively(
    all_docs, vector_w, fts_w, sparse_w, k)

# 用 heap 维护 Top-K（避免 O(n log n) 全排序）
heap = []
for doc_id, doc_data in all_docs.items():
    if len(heap) < limit:
        heapq.heappush(heap, (doc_data['rrf_score'], safe_id, doc_data))
    elif doc_data['rrf_score'] > heap[0][0]:
        heapq.heapreplace(heap, (doc_data['rrf_score'], safe_id, doc_data))
```

最后还会计算 `_calculate_quality_score` 用 raw similarity（vector_similarity / fts_score / sparse_similarity）做阈值过滤，避免 RRF 排名高但绝对相似度低的"长尾噪声"。

### `apps/claude-code-plugin/` 工程化

- `cmd/powermem-hook/main.go` + `detach_unix.go` / `detach_windows.go` / `poll.go` —— 跨平台原生二进制，无 Python 依赖；
- `scripts/build-hook-binaries.sh` 用 Go 1.22+ 交叉编译 `darwin/{amd64,arm64}` / `linux/{amd64,arm64}` / `windows/amd64`；
- `hooks/run-hook.sh`（POSIX sh）或 `run-hook.ps1`（PowerShell）按平台选二进制；
- `hooks.json` 注册 4 个 hook event：`UserPromptSubmit`（自动检索注入 `additionalContext`）、Stop（保存对话）、PreCompact（压缩前保存）、PostToolUse（捕获工具调用结果）；
- `make package-claude-plugin` 打成 zip，可离线分发；
- `config/{http-mode,mcp-mode}.mcp.json` 两份 `.mcp.json` 模板，`apply-connection-mode.sh` 一键切换。

## 性能 / 资源开销

| 指标 | PowerMem | "塞满上下文" baseline | 倍数 |
|------|----------|----------------------|------|
| LOCOMO 准确率 | 78.70% | 52.9% | +25.8 pp |
| Retrieval p95 latency | 1.44s | 17.12s | 11.9× faster |
| Tokens / query | ~0.9k | ~26k | 28.9× less |

性能关键路径：

- **向量索引选型**：HNSW / HNSW_SQ / IVFFLAT / IVFSQ / IVFPQ 五种自动配置；`ob_vector_memory_limit_percentage=30` 自动设置（OceanBase 向量内存上限）；
- **三路并发检索**：vector + FTS + sparse 用 `ThreadPoolExecutor` 并发（`oceanbase.py` 内部线程池）；
- **后台异步写**：LLM 抽取在前台等，telemetry/audit/optimization 在 `_BACKGROUND_EXECUTOR`（3 worker）跑；
- **Snowflake ID**：避免 auto-increment 的多实例冲突，时间有序便于按时段范围查询；
- **REPLACE INTO upsert**：单次原子操作完成 insert/update，减少 round-trips；
- **3-hop 图遍历**：早停（满足 limit 即停）、防环、`max_edges_per_hop` 控制扇出。

冷启动开销：FastAPI lifespan 初始化 4 个 service 单例；首次 add 时 `create_col` 按实际 vector size 建表（lazy schema）。

## 安全模型

- **API key 鉴权**：`server/middleware/auth.py verify_api_key` 作为 FastAPI Depends 注入到每个 v1 路由；通过 env / `.env` 配置。
- **限流**：`slowapi` `Limiter`（基于 IP，`get_remote_address`）；可按端点配置 rate limit string。
- **CORS**：默认关闭，开启后通过 `cors_origins` 配置白名单。
- **SQL 注入防护**：v1.1.1 commit `720e37b` "Fix SQLite filters key SQLi by parameterizing JSON path" —— filter parser 已使用参数化查询（`pyobvector.bindparam`）。
- **审计**：`AuditLogger` 落 `./logs/audit.log`，可配置 `retention_days=90`；合规场景必备。
- **多租户隔离**：`agent/components/{scope,permission,privacy}_controller.py` 三道关卡 —— scope 决定能看到哪条数据；permission 决定能做什么操作（read/write/delete/admin）；privacy 决定哪些字段对该调用者可见。
- **凭证存储**：所有 LLM / DB / embedding 凭证走 `.env`；server config 用 pydantic-settings 加载；二进制 hook 不持久化凭证（每次走 HTTP）。
- **已知风险**：
  - Mock 向量退路（`StorageAdapter:78` 用 `[0.1] * 1536`）在 embedder 失败时悄悄注入伪向量；生产需配置告警，否则会污染索引。
  - Telemetry endpoint 默认 `https://telemetry.powermem.ai`（虽默认 `enable_telemetry=False`），合规场景务必显式关闭。
  - Dashboard 静态资源默认无单独 auth gate，部署在公网时需在 reverse proxy 层加密码保护。

## Git 背景与版本演进

| 版本 | 日期 | 关键变更 |
|------|------|----------|
| 0.1.0 | 2025-11-14 | 核心 memory + 混合检索；LLM 抽取；遗忘曲线；多 agent；OceanBase/PostgreSQL/SQLite；graph search |
| 0.2.0 | 2025-12-16 | 高级 profiles；多模态（text/image/audio） |
| 0.3.0 | 2026-01-09 | 生产级 HTTP API Server；Docker |
| 0.4.0 | 2026-01-20 | 稀疏向量做混合检索；profile-based query rewrite；schema 升级 & 迁移工具 |
| 0.5.0 | 2026-02-06 | 统一 SDK/API 配置（pydantic-settings）；OceanBase 原生混合搜索；memory 查询/列表排序；用户档案语言定制 |
| 1.0.0 | 2026-03-16 | CLI `pmem`（memory ops / config / backup-restore-migrate / shell / completions）；Web Dashboard |
| 1.1.0 | 2026-04-02 | 嵌入式 SeekDB（OceanBase 存储无需独立 DB 服务）；IDE 集成（VS Code 扩展、Claude Code 插件） |
| 1.1.1 | 2026-04-? | bug fix release（GraphStoreFactory 配置兼容、sparse_embedder provider 解析、custom prompt env var 支持、i18n 补齐） |

最近 commits（截至 2026-05-13）集中在：
- Dashboard regression cases（#909）；
- i18n 翻译补齐 zh-CN（#918, #916）；
- GraphStoreFactory 接受完整 config 对象时的 TypeError 修复（#919）；
- `sparse_embedder` provider 从 dict 解析（#917）；
- `custom_extraction/update/importance_prompt` 支持 env var（#911）；
- SQLite filters key SQLi 修复（#899, #720b）。

整体处于"成熟稳定 + 小规模 patch"阶段，主线功能已经齐备。
