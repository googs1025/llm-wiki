# memsearch 架构与设计思路分析

> 仓库：https://github.com/zilliztech/memsearch · 分析日期：2026-06-07 · 版本：v0.4.6 / HEAD `018a85f` (2026-06-01)

## 一句话定位

memsearch 是 Zilliz 出品的跨平台 AI coding agent 语义记忆系统：Claude Code、Codex、OpenCode、OpenClaw 等平台通过 hook/skill 捕获会话摘要，写入 `.memsearch/memory/*.md`，再由 Python core 把 Markdown 切块后索引到 Milvus / Milvus Lite / Zilliz Cloud。

它的关键设计不是把记忆藏进某个私有数据库，而是让 Markdown 成为 source of truth，Milvus 只做可重建的 shadow index。查询时走 dense embedding + BM25 sparse hybrid search + RRF，之后用 `expand` 和 transcript anchor 做渐进式回溯。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 用户入口 | `src/memsearch/cli.py`, `src/memsearch/__main__.py` | `memsearch index/search/expand/watch/compact/config` 等命令入口，解析 CLI overrides 后调用 core |
| 平台插件 | `plugins/claude-code`, `plugins/codex`, `plugins/opencode`, `plugins/openclaw` | 宿主特定 hook、transcript parser、skill、install 脚本；负责捕获对话和注入 recall 提示 |
| 编排核心 | `src/memsearch/core.py` | `MemSearch` 高层 API：扫描、切块、增量索引、搜索、压缩、watch |
| Markdown 处理 | `src/memsearch/scanner.py`, `src/memsearch/chunker.py` | 发现 Markdown 文件，按 heading/paragraph/line/sentence 切 chunk，生成内容 hash 和 line range |
| Embedding 抽象 | `src/memsearch/embeddings/*` | 统一 `EmbeddingProvider` protocol，动态加载 OpenAI/Google/Voyage/Jina/Mistral/Ollama/local/ONNX |
| 存储检索 | `src/memsearch/store.py` | MilvusClient wrapper，创建 collection schema、BM25 Function、dense/sparse index、hybrid search |
| 记忆压缩 | `src/memsearch/compact.py`, `src/memsearch/maintenance.py`, `src/memsearch/prompts/*` | 把 chunk 压缩回 daily memory，按输入 digest 维护 PROJECT/USER 长期摘要 |
| 配置 | `src/memsearch/config.py` | defaults → global config → project config → CLI flags，支持 `env:VAR` secret reference |
| 文档/测试 | `docs/*`, `tests/*` | 平台安装、架构、CLI/Python API、故障排查和核心行为测试 |

分层约束很明显：Python core 不理解某个 agent 宿主的 transcript 格式，宿主插件也不直接实现向量检索。宿主侧只负责把会话变成 Markdown 和 anchor；core 只负责 Markdown → chunks → Milvus → search/expand。

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

`MemSearch.index()` 先扫描路径，再逐文件 `_index_file()`；每个 chunk 的 ID 包含 source、line range、content hash 和 embedding model，因此同一段文本换模型后会得到不同主键。旧 source 已不存在时，`indexed_sources()` + `delete_by_source()` 会清理 shadow index（`src/memsearch/core.py:87-159`）。

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

`MemSearch.search()` 负责 query embedding、source prefix 过滤和可选 reranker；MilvusStore 用两个 `AnnSearchRequest` 做 dense + BM25，并用 `RRFRanker(k=60)` 融合结果（`src/memsearch/core.py:200-238`, `src/memsearch/store.py:159-210`）。CLI 的 `expand` 是 L2：它用 `chunk_hash` 查询 metadata，再回读原始 Markdown 文件，按 heading 边界扩展上下文（`src/memsearch/cli.py:297-359`）。

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

Codex 的 `session-start.sh` 能看到产品默认体验：如果本机没有 `memsearch`，会用 `uvx --from memsearch[onnx]` 预热；第一次配置时把 embedding provider 设置成 `onnx`；Milvus Lite 因文件锁不启用 watch，而是在后台做一次性 index（`plugins/codex/hooks/session-start.sh:11-137`）。维护任务按输入目录 digest 判断是否需要重写 `.memsearch/PROJECT.md` 和 `.memsearch/USER.md`（`src/memsearch/maintenance.py:55-146`）。

## 设计决策与哲学

- **Markdown 是 source of truth，Milvus 是 shadow index**：`compact()` 也把摘要写回 `memory/YYYY-MM-DD.md`，再立即索引该文件；这意味着索引可删可重建，长期记忆仍在可读 Markdown 中（`src/memsearch/core.py:244-299`）。
- **chunk 主键绑定 source、line range、content、model**：`compute_chunk_id()` 使用 `markdown:{source}:{start}:{end}:{content_hash}:{model}`，既支持增量跳过未变 chunk，也避免 embedding model 维度或语义变化污染旧索引（`src/memsearch/chunker.py:65-77`）。
- **检索由 Milvus 同时承担 dense 和 BM25**：collection schema 把 `content` 开启 analyzer，并用 BM25 Function 自动生成 `sparse_vector`；检索时 dense 和 sparse 两个请求走 `hybrid_search` + RRF（`src/memsearch/store.py:82-108`, `src/memsearch/store.py:159-210`）。
- **平台插件捕获，核心只处理 Markdown**：Codex/Claude/OpenCode/OpenClaw 各自解析 transcript、管理 hook 生命周期和 native LLM summarization；Python core 只关心 Markdown chunk。这样一个 package 能跨宿主复用。
- **渐进式上下文控制**：search 只返回片段，超过 500 字会提示 `expand`；expand 再回源文件取完整 heading section，避免一开始就把历史 transcript 塞进上下文（`src/memsearch/cli.py:274-286`, `src/memsearch/cli.py:330-335`）。
- **本地优先但不封闭**：默认 Milvus URI 是 `~/.memsearch/milvus.db`，但 `MemSearch` 和 config 同时支持 Milvus Server / Zilliz Cloud token。插件安装路径默认 ONNX，本体 config dataclass 默认 provider 是 OpenAI；这是代码与安装体验之间需要区分的细节（`src/memsearch/config.py:33-47`, `plugins/codex/hooks/session-start.sh:22-26`）。
- **secret 不强写入配置**：`env:VAR` 由 config 层解析，named LLM providers 的 env refs 还会延迟到选中时再解析，避免未使用 provider 破坏普通 config 命令（`src/memsearch/config.py:200-246`）。
- **维护任务有输入 digest 和只读 drill-down 工具**：project/user profile 任务只在输入变化且到期时跑；LLM 可调用受限的 `memsearch expand/transcript/find/grep`，命令校验禁止 shell metacharacter 和越权路径（`src/memsearch/maintenance.py:28-31`, `src/memsearch/maintenance.py:383-424`）。

## 关键组件深入解读

### `MemSearch` 编排器（`src/memsearch/core.py`）

`MemSearch.__init__()` 同时创建 embedding provider 和 `MilvusStore`，并把 provider dimension 传入 store 做 collection dimension 守卫。`index()` 是核心写路径：扫描 Markdown、逐文件切块、计算新旧 chunk ID 差集、删除 stale chunk、仅 embedding 新 chunk。`_embed_and_store()` 有一个细节：发送给 embedding model 的内容会先去掉 HTML comments，避免 session UUID、turn id、transcript path 污染向量；但写入 Milvus 的 `content` 仍保留原文，以便 expand 和 transcript anchor 可用。

`search()` 的职责刻意很薄：构造 source prefix filter、embedding query、调用 store hybrid search、可选 reranker。`compact()` 则从 store query chunk，调用 LLM 摘要，追加到 daily markdown，并立刻 index 新文件。这个设计让“压缩记忆”和“保存记忆”走同一份 Markdown 管道，而不是新增一张 summary 表。

### `MilvusStore`（`src/memsearch/store.py`）

`MilvusStore` 是 pymilvus client wrapper。初始化时根据 URI 判断 local/remote：非 `http`/`tcp` 是 Milvus Lite，会创建父目录；Windows 上 Milvus Lite 无 wheel，直接给出错误和替代方案。collection 已存在时检查 embedding dimension，不存在且有 dimension 时创建。

schema 里 `chunk_hash` 是 primary key，`embedding` 是 dense vector，`content` 是启用 analyzer 的 VARCHAR，`sparse_vector` 由 BM25 Function 从 content 自动生成。检索时先检查 empty collection，避免 BM25 avgdl=0 崩溃；然后构造 dense 和 BM25 两个请求，用 RRF 融合，最后按理论最大 RRF 分数归一化。这让调用方看到的是一个普通 `score`，而不是 Milvus 内部 distance。

### 平台插件与 Codex hook

Codex 插件的 `common.sh` 做了几个关键工程处理：从 hook JSON 或当前目录解析 project root；优先用 git root；如果用户显式设置 `MEMSEARCH_DIR` 就进入 global scope，否则按项目隔离；collection name 由项目目录或 memsearch dir 派生。`session-start.sh` 负责 bootstrap 和注入：缺 `memsearch` 时尝试安装/预热 `uvx`，首次默认 ONNX，检查 provider API key，启动 watch 或 one-shot index，再在 systemMessage 里提示可用历史记忆。

Stop hook 则异步把会话片段交给 worker，优先用配置的 plugin summarize provider，或用宿主 native LLM，总结失败时降级成简单的 user question / last message 摘要。它最后追加 Markdown 并触发维护任务。这说明 memsearch 把“写入记忆”当成边缘 hook 任务，把“检索记忆”当成显式 skill/tool 调用，避免每轮都自动注入大量历史。

## 与同类对比

| 维度 | memsearch | Claude Context | agent-recall | agentmemory / PowerMem |
|------|-----------|----------------|--------------|------------------------|
| 主要对象 | AI coding agent 会话记忆 Markdown | 代码库语义检索 | MCP-native 实体/关系/观察 | 跨 Agent 记忆服务 / 中间件 |
| source of truth | `.memsearch/*.md` | indexed codebase files | SQLite database | SQLite / OceanBase / service storage |
| 协议入口 | CLI + platform hooks + skills | MCP server + extensions | MCP server + CLI + hooks | MCP / REST / SDK / hooks |
| 检索 | Milvus dense + BM25 + RRF | Milvus dense/sparse + RRF | SQLite/FTS + scope | BM25/vector/graph 或多路混合 |
| 上下文控制 | search → expand → transcript | search code chunks | briefing cache + open/search | viewer/context injection/tools |
| 默认部署感 | local-first Milvus Lite + ONNX plugin path | MCP plugin | local SQLite | service/worker/middleware |

memsearch 和 Claude Context 都来自 Zilliz，并共享 Milvus hybrid retrieval 的品味，但目标不同：Claude Context 是“让 Agent 看懂当前代码库”，memsearch 是“让 Agent 记住过去会话”。agent-recall 更偏 MCP knowledge graph / scoped facts；agentmemory 和 PowerMem 更像常驻记忆服务或数据库中间件。

## 性能 / 资源开销

未做本地 benchmark。源码层可确认的资源策略包括：

- 增量索引跳过已存在 chunk，避免重复 embedding。
- Milvus Lite 默认本地 `.db`，适合个人项目；Server/Zilliz 路径适合共享或远端。
- 插件在 Milvus Lite 模式不启动长期 watch，避免本地 DB 文件锁冲突；改为 session start 后台 one-shot index。
- BM25 sparse vector 由 Milvus Function 生成，不需要额外 Python 稀疏索引。
- 可选 reranker 会把 fetch_k 扩到 `top_k * 3`，提高精排输入但增加模型开销。

## 安全模型

memsearch 的核心安全边界是本地文件和配置：

- 长期记忆以 Markdown 存在项目 `.memsearch` 或显式 `MEMSEARCH_DIR`，用户可直接审计。
- API key 可以通过环境变量或 `env:VAR` 引用，不要求明文写入 TOML。
- 平台插件在缺 API key 时会提前提示并禁用记忆搜索，避免半失败状态。
- 维护任务给 LLM 的 drill-down 命令是受限命令集，禁止 shell metacharacter，路径必须在 project/memory roots 内。
- transcript anchor 会暴露原始 transcript path；这是 L3 回溯能力的代价，适合本地优先使用，团队共享时需要注意路径和会话内容敏感性。
