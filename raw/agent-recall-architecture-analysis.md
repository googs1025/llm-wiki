# agent-recall 架构与设计思路分析

> 仓库：https://github.com/mnardit/agent-recall · 分析日期：2026-06-06 · 版本：main HEAD `dcf21b5`（2026-04-03）

## 一句话定位

agent-recall 是一个给 AI coding agents 使用的本地持久化记忆系统：它通过 MCP tools 让 Agent 主动保存 people / decisions / facts / context，通过 SQLite 保存结构化知识图谱，并在 session start 时把记忆压缩成 AI briefing 注入上下文。它的关键手段不是向量库或云服务，而是 scope hierarchy、bitemporal slots、MCPBridge 权限边界和可缓存的 LLM briefing。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Client surfaces                                                              │
│  MCP clients: Claude Code / Cursor / Windsurf / Cline                        │
│  CLI: agent-recall                                                           │
│  Hooks: agent-recall-session-start / agent-recall-post-tool-use              │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ tool calls / CLI commands / hook JSON
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Interface layer                                                              │
│  mcp_server.py: FastMCP tools + proactive memory instructions                │
│  cli.py: click commands for init, CRUD, search, briefing, status             │
│  hooks.py: Claude Code SessionStart and PostToolUse protocols                │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ normalized operations
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Policy / orchestration layer                                                 │
│  MCPBridge: input limits, protected types, scope read/write filtering         │
│  MemoryConfig: hierarchy, tiers, agent types, briefing and path resolution    │
│  ScopedView: local-over-parent slot inheritance for context assembly          │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ trusted store calls
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ State layer                                                                  │
│  MemoryStore: SQLite entities / slots / observations / relations / logs      │
│  FTS5 when available, LIKE fallback, WAL mode, schema migrations              │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ raw scoped graph
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Briefing layer                                                               │
│  context.py: budget-aware raw context assembly                               │
│  context_gen/: orchestrator/topic assembly, prompt templates, LLM caller      │
│  cache.py: per-agent markdown cache, stale markers, generation logs           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 外部接口层 | `agent_recall/mcp_server.py`, `agent_recall/cli.py`, `agent_recall/hooks.py` | 暴露 MCP tools、命令行和 Claude Code hook；把外部协议输入转成统一 store / bridge 操作。 |
| 配置与 scope 层 | `agent_recall/config.py`, `agent_recall/hierarchy.py` | 解析 `memory.yaml`、环境变量和默认路径；推导 agent scope chain、tier、agent type；提供 scope 继承视图。 |
| MCP 策略层 | `agent_recall/mcp_bridge.py` | 兼容 MCP memory protocol，同时做输入上限、写权限、读过滤和 protected type 防删。 |
| 持久化层 | `agent_recall/store.py`, `agent_recall/migrations.py` | 单 SQLite 文件管理 entities、slots、observations、relations、logs、documents；负责 FTS、WAL、迁移和 bitemporal slot。 |
| 原始上下文组装 | `agent_recall/context.py`, `agent_recall/context_helpers.py` | 从 store 读取 scope-filtered graph，按优先级和 budget 拼成原始 markdown context。 |
| AI briefing 生成 | `agent_recall/context_gen/*`, `templates/*.md` | 选择 agent 模板，拼 prompt，调用 Claude CLI 或 Anthropic API，缓存 briefing，维护 stale marker 和 generation log。 |
| 辅助工具 | `agent_recall/contrib/dedup.py`, `agent_recall/contrib/vault_gen.py` | 实体去重候选、Obsidian vault 页面生成和可选 git auto-commit。 |
| 测试与示例 | `tests/*`, `examples/*` | 覆盖 store、bridge、config、context、hooks、migrations、CLI、vault generation 和 MCP integration。 |

这个分层的关键约束是：`MemoryStore` 明确不做 scope enforcement，保持简单、可测试、可复用；所有 MCP 客户端可见的权限边界集中在 `MCPBridge`。CLI 直接访问 store，因此更像本机管理工具；MCP server 则是多 Agent 运行时的安全入口。

## 关键数据流

### MCP 写入 / 查询路径

```
┌──────────────────────┐
│ MCP-compatible agent │
│ create_entities      │
│ add_observations     │
│ search_nodes         │
└──────────┬───────────┘
           │ stdio MCP tool call
           ▼
┌────────────────────────────────────────────────────────────────────┐
│ mcp_server.py                                                       │
│  1. FastMCP exposes 9 memory tools                                  │
│  2. _bridge() loads memory.yaml                                     │
│  3. slug = AGENT_RECALL_SLUG or cwd name                            │
│  4. config.get_agent(slug) derives scope chain and agent type       │
└──────────┬─────────────────────────────────────────────────────────┘
           │ JSON-like dict/list payload
           ▼
┌────────────────────────────────────────────────────────────────────┐
│ MCPBridge                                                          │
│  1. cap item count, text length, query length, relation count       │
│  2. compute allowed scopes = chain + local children                 │
│  3. writes: _entity_writable() checks entity non-global scopes      │
│  4. reads: _read_scope_set() and _entity_visible() filter results   │
└──────────┬─────────────────────────────────────────────────────────┘
           │ trusted operations
           ▼
┌────────────────────────────────────────────────────────────────────┐
│ MemoryStore                                                        │
│  resolve_entity / add_observation / add_relation / search          │
│  SQLite tables + FTS5 triggers + WAL + migrations                  │
└──────────┬─────────────────────────────────────────────────────────┘
           │ result dict
           ▼
┌──────────────────────┐
│ JSON string to agent │
└──────────────────────┘
```

错误与回退路径：MCPBridge 对单次调用做截断和 blocked list，而不是直接抛出所有错误；FTS5 初始化失败时 store 记录 `_has_fts=False` 并回退到 LIKE 搜索；MCP server 如果缺少 `mcp` extra 会在导入阶段抛出明确安装提示。

### SessionStart briefing 路径

```
┌──────────────────────────────┐
│ Claude Code SessionStart hook│
└──────────────┬───────────────┘
               │ JSON stdout protocol
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ hooks.session_start_hook                                           │
│  1. slug = AGENT_RECALL_SLUG or cwd                                │
│  2. load_config() and get_agent(slug)                              │
│  3. tier0 / empty chain / missing DB => return silently             │
│  4. stale cache + adaptive => attempt generate_briefing(force=True) │
│  5. fresh cache => additionalContext = Agent Briefing               │
└──────────────┬─────────────────────────────────────────────────────┘
               │ cache miss
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Raw context fallback                                               │
│  MemoryStore(config.db_path)                                       │
│  assemble_context(store, chain, tier, vault tasks)                 │
└──────────────┬─────────────────────────────────────────────────────┘
               │ context string
               ▼
┌────────────────────────────────────────────────────────────────────┐
│ Claude receives additionalContext                                  │
│  cached AI briefing, raw memory context, or cold-start instructions │
└────────────────────────────────────────────────────────────────────┘
```

### AI briefing generation path

```
┌──────────────────────────┐
│ generate_briefing(slug)  │
└────────────┬─────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│ Config + cache gate                                            │
│  enabled? tier0? cache fresh? per-agent briefing overrides?    │
└────────────┬──────────────────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│ Raw context source selection                                   │
│  orchestrator -> _assemble_orchestrator_context(all scopes)    │
│  topic        -> _assemble_topic_context(topic + parent scope) │
│  default      -> assemble_context(scope chain + tier)          │
└────────────┬──────────────────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│ Prompt enrichment                                              │
│  extra_context + configured context_files + auto-discovered    │
│  CLAUDE.md / README sections, bounded by allowed base dirs     │
└────────────┬──────────────────────────────────────────────────┘
             │
             ▼
┌───────────────────────────────────────────────────────────────┐
│ Template + LLM caller                                          │
│  builtin or custom template -> Claude CLI / Anthropic API      │
│  write cache markdown + generation log + clear stale marker    │
└───────────────────────────────────────────────────────────────┘
```

## 设计决策与哲学

- **本地优先，数据库极简**：`MemoryStore` 默认写到 `~/.agent-recall/frames.db`，创建目录权限 `0700`、DB 权限 `0600`，启用 SQLite WAL 和 foreign keys；依赖只要求 `pyyaml` + `click`，MCP 和 Anthropic 都是 optional extras（`store.py:56-70`, `pyproject.toml`）。
- **scope enforcement 放在 MCPBridge，不放在 Store**：`docs/architecture.md` 明确说明 store 不做 scope enforcement；源码中 `MCPBridge.__init__()` 计算 `_allowed_scopes`，`_entity_writable()` 用 entity 的非 global scopes 判断写权限，读路径用 `_read_scope_set()` 和 `_entity_visible()` 过滤（`mcp_bridge.py:51-105`, `mcp_bridge.py:293-366`）。
- **MCP-native 行为引导**：`mcp_server.py` 不只是暴露工具，还在 FastMCP instructions 里要求 Agent 主动保存 people、decisions、facts、context，并在创建实体前先 `search_nodes` 去重；这把“记忆写入策略”作为 MCP server 的协议语义交给客户端（`mcp_server.py:45-67`）。
- **bitemporal slots + observations 分离**：slots 是 key-value、scope-aware、旧值归档到 `valid_to`；observations 是自由文本，单独表和 FTS；这让“角色/邮箱/状态”与“讨论记录/偏好/背景”分别建模（`store.py:89-114`, `store.py:408-532`）。
- **AI briefing 是压缩层，不是存储层**：`generate_briefing()` 先从 SQLite 组装 raw context，再按 agent type 选择模板和 LLM caller，结果写 cache；数据真相仍在 SQLite，cache 只是启动上下文优化（`context_gen/generator.py:45-205`）。
- **Hook 只做轻量边界工作**：SessionStart 优先读 cache，失败才拼 raw context；PostToolUse 只对 memory write tools 做 adaptive invalidation 和可选 vault regen，并用文件锁 + 5 分钟 rate limit 避免频繁重生成（`hooks.py:29-176`）。
- **配置推导承载组织结构**：`MemoryConfig.get_agent()` 从 explicit `scope_chain`、orchestrator、tiers、system agents、hierarchy children/parents 到 fallback slug 逐级推导 chain；agent type 又决定 briefing 模板（`config.py:47-153`）。
- **安全选择偏保守但边界清楚**：MCPBridge 限制 entity name、observation text、items per call、query length、relation count，并保护 `agent/section/config` 类型不被 MCP 删除；但 CLI / Python API 直接调用 store 时绕过 MCP scope 边界，这是显式信任模型。

## 关键组件深入解读

### MemoryStore（agent_recall/store.py）

`MemoryStore` 是单 SQLite 文件的 state layer。初始化时创建父目录、设置 DB 文件权限、打开 sqlite connection、启用 WAL 和 foreign keys，然后执行 `_init_tables()` 与 `run_migrations()`。表结构包括 `entities`、`slots`、`observations`、`relations`、`log_entries`、`documents`，其中 `slots` 用 `(entity_id, key, scope, valid_from)` 做主键，当前值用 `valid_to IS NULL` 判断；`observations` 和 `relations` 用 `archived_at` / `status` 表示软删除。FTS5 虚拟表和触发器在 `_init_fts()` 中创建，如果 SQLite build 不支持 FTS5，就设置 `_has_fts=False`，搜索层可降级。

Store 的设计重点是“可信底层 API”：`resolve_entity()` 幂等创建实体，`set_slot()` 先把当前 slot 归档再插入新值，`get_slot()` 用 reversed scope chain 实现 local-over-global，`get_entity_scopes()` 汇总 slots / observations 的非 global scope 给 MCPBridge 做权限判断。它不关心调用者是谁，也不判断是否越权。

### MCPBridge（agent_recall/mcp_bridge.py）

`MCPBridge` 是 agent-recall 的安全和协议语义中心。它把 MCP server-memory 风格的 `create_entities` / `create_relations` / `add_observations` / `search_nodes` / `open_nodes` 映射到底层 store，同时限制输入规模。初始化时从 agent scope chain 计算 allowed scopes：当前 chain 加上本地 scope 的 children；chain 长度大于 1 时才启用 enforcement，orchestrator / tier0 这类单 scope 或空 chain agent 会跳过。

写路径通过 `_entity_writable(entity_id)` 判断实体是否有非 global scope；没有 specific scope 的实体被视为 global-only / bootstrap，可写；如果实体已有某些非 global scope，则必须与 agent 的 allowed non-global scopes 有交集。读路径通过 `_read_scope_set()` 生成 scope filter，`search_nodes()` over-fetch 后再过滤，`open_nodes()` 和 `read_graph()` 也按 entity visibility 裁剪 observations。

### Context / Briefing（agent_recall/context.py, agent_recall/context_gen/*）

briefing 体系分两层：`context.py` 负责不调用 LLM 的 raw markdown 组装，`context_gen` 负责把 raw context 变成适合注入 session 的 AI briefing。`assemble_context()` 用 `ScopedView` 读取 chain 中可见的数据，并把 People、Current Tasks、Topics、Parent Context、Project Context、Clients/Agencies/Projects、Logs 等 section 按 priority 组装，最后 `apply_budget()` 截断。

`generate_briefing()` 在 cache gate 之后判断 agent type：orchestrator 读取全局全量概要，topic 读取 topic entity + related entities + parent scope，默认 agent 走 scope chain context。随后合并 extra context、显式 context files、自动发现的 `CLAUDE.md` / `README.md`，再用内置或自定义模板构造 prompt。自定义模板不用 `str.format()`，而是手工替换 `{slug}`、`{raw_context}`、`{budget}`，避免配置模板造成 format-string attribute access。

### Hooks（agent_recall/hooks.py）

hooks 是 Claude Code 集成的自动化边界。SessionStart hook 用 JSON stdout 返回 `additionalContext`：先检查 stale marker 和 adaptive regeneration，再读 cache；cache miss 时直接调用 `assemble_context()` 返回 raw memory；如果 DB 存在但没有上下文，则返回冷启动说明。PostToolUse hook 只响应 memory write tools：adaptive 模式下根据 tool input 和当前 agent scope invalidates affected agents；如果配置了 Obsidian vault，则用锁和 rate limit 触发 vault regeneration，并可选执行 git auto-commit。

## 与同类对比

| 维度 | agent-recall | claude-mem | agentmemory | PowerMem |
|------|--------------|------------|-------------|----------|
| 部署形态 | Python package + SQLite + optional MCP server | Claude Code plugin + daemon | Node/iii-engine worker + SQLite | 数据库/服务层 memory middleware |
| 客户端入口 | MCP clients、CLI、Claude hooks | Claude Code hooks / MCP beta | 多 Agent hooks + MCP + REST | SDK / API / MCP / Dashboard |
| 记忆模型 | entities + scoped slots + observations + relations | 压缩 observation + 检索 | 多 scope KV + BM25/vector/graph | working/short/long + OceanBase |
| 组织隔离 | scope hierarchy + MCPBridge enforcement | profile/workspace 为主 | 多 Agent 共享服务，scope 更扁平 | 应用侧决定租户边界 |
| AI 使用 | session briefing 压缩，可 cache | LLM 压缩是核心 | 默认零 LLM，可选压缩 | LLM 抽取/优化更深 |
| 依赖重量 | 极轻：pyyaml/click，MCP optional | Node + queue/vector deps | Node + iii-engine | DB / provider 矩阵更重 |

## 性能 / 资源开销

- **冷启动**：MCP server 首次 `_bridge()` 会 load config、derive agent、打开 SQLite；没有后台 daemon 常驻要求。未测具体耗时。
- **稳态存储**：单 SQLite 文件 + WAL，FTS5 triggers 自动维护实体名和 observations 全文索引；适合个人/小团队本地规模。
- **briefing 成本**：raw context 默认 budget 50,000 chars，output budget 默认 8,000 chars；cache 默认 24h fresh，adaptive 模式下使用 stale marker + min_cache_age 减少 LLM 调用。
- **潜在瓶颈**：`search_nodes()` scope filter 会 over-fetch `limit * 5` 再过滤；大库下 FTS fallback 到 LIKE 会退化。项目没有内置向量检索，因此语义召回能力取决于文字匹配和 LLM briefing，而不是 embedding。

## 安全模型

agent-recall 的安全模型是“本机信任 + MCP scope boundary”：

- **本机数据保护**：默认 DB 在 `~/.agent-recall/frames.db`，目录 `0700`、DB `0600`；无云同步默认路径。
- **MCP 写边界**：MCPBridge 按 scope chain 控制写入；关系创建只要求 source entity 可写；`agent/section/config` 类型不能通过 MCP 删除。
- **MCP 读边界**：普通 scoped agent 的 search/open/read_graph 会按 scope 过滤；orchestrator 可设置 `scope_reads=False` 读取全量。
- **配置边界**：`strict_scopes` 可要求 scope 在 known scopes 中；默认没有强制，未知 slug 会 fallback 到 `["global", slug]` 并警告。
- **模板安全**：custom inline template 不走 `str.format()`，避免格式字符串访问对象属性。
- **信任限制**：直接 CLI / Python API 调用 store 可绕过 MCPBridge；Obsidian vault auto-commit 运行本机 git；briefing backend 调 Claude CLI 或 Anthropic API 时 raw context 会进入模型调用路径。
