---
title: agent-recall 架构与设计思路分析
tags: [architecture, agent-memory, ai-agent, mcp, llm-infra]
date: 2026-06-06
sources: [agent-recall-architecture-analysis.md]
related: ["[[agent-recall]]", "[[mcp]]", "[[agent-memory]]", "[[claude-code]]", "[[claude-mem]]", "[[agentmemory]]", "[[powermem]]", "[[ai-as-compressor]]"]
---

# agent-recall 架构与设计思路分析

> 原文：`raw/agent-recall-architecture-analysis.md` · 仓库：[mnardit/agent-recall](https://github.com/mnardit/agent-recall) · 分析版本 main HEAD `dcf21b5`（2026-04-03）

## 一句话定位

[[agent-recall]] 是一个给 AI coding agents 使用的本地持久化记忆系统：它通过 [[mcp]] tools 让 Agent 主动保存 people / decisions / facts / context，通过 SQLite 保存结构化知识图谱，并在 session start 时把记忆压缩成 AI briefing 注入上下文。它和 [[claude-mem]]、[[agentmemory]]、[[powermem]] 同属 [[agent-memory]] 方向，但重点放在 scope hierarchy、MCP-native 写入和本地 SQLite。

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

| 层 / 模块 | 职责 |
|----------|------|
| 外部接口层 | 暴露 [[mcp]] tools、命令行和 [[claude-code]] hooks；把外部协议输入转成统一 store / bridge 操作。 |
| 配置与 scope 层 | 解析 `memory.yaml`、环境变量和默认路径；推导 agent scope chain、tier、agent type；提供 scope 继承视图。 |
| MCP 策略层 | 兼容 MCP memory protocol，同时做输入上限、写权限、读过滤和 protected type 防删。 |
| 持久化层 | 单 SQLite 文件管理 entities、slots、observations、relations、logs、documents；负责 FTS、WAL、迁移和 bitemporal slot。 |
| 原始上下文组装 | 从 store 读取 scope-filtered graph，按优先级和 budget 拼成原始 markdown context。 |
| AI briefing 生成 | 选择 agent 模板，拼 prompt，调用 Claude CLI 或 Anthropic API，缓存 briefing，维护 stale marker 和 generation log。 |
| 辅助工具 | 实体去重候选、Obsidian vault 页面生成和可选 git auto-commit。 |

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

- **本地优先，数据库极简**：默认一份 `~/.agent-recall/frames.db`，目录和 DB 权限收紧；运行时核心依赖只有 `pyyaml` + `click`，[[mcp]] 与 Anthropic SDK 都是 optional。
- **scope enforcement 放在 MCPBridge，不放在 Store**：store 是可信底层 API，MCPBridge 才是多 Agent 读写权限边界；这让本机 CLI 管理和 MCP 客户端访问有不同信任模型。
- **MCP-native 行为引导**：server instructions 明确要求 Agent 主动保存 people、decisions、facts、context，并先 search 再 create，记忆策略嵌进协议入口。
- **bitemporal slots + observations 分离**：结构化事实用 slots，旧值归档；自由文本用 observations，单独 FTS；适合同时表达稳定属性和会话记录。
- **AI briefing 是压缩层，不是存储层**：真相仍在 SQLite，LLM 只把 raw scoped context 压缩成启动 briefing；这和 [[ai-as-compressor]] 思路相近，但更强调 scope hierarchy。
- **Hook 只做轻量边界工作**：SessionStart 优先读 cache，PostToolUse 只做 memory write 后的 stale marker / vault regen，避免每次启动或写入都强制跑 LLM。

## 核心组件

### MemoryStore

`MemoryStore` 是单 SQLite 文件的 state layer。它创建 `entities`、`slots`、`observations`、`relations`、`log_entries`、`documents`，启用 WAL、foreign keys 和可选 FTS5。`slots` 通过 `valid_from / valid_to` 表达 bitemporal 旧值归档；`observations` 和 `relations` 通过 `archived_at` / `status` 软删除。它不关心调用者是谁，也不判断是否越权。

### MCPBridge

`MCPBridge` 是 agent-recall 的安全和协议语义中心。它把 MCP memory tools 映射到底层 store，同时限制输入规模。写路径通过实体已有的非 global scopes 判断是否可写；读路径通过 scope set 过滤 `search_nodes`、`open_nodes` 和 `read_graph`。orchestrator 可以关闭读过滤，普通 scoped agent 则只能看到自己 scope chain 内的数据。

### Context / Briefing

`context.py` 负责不调用 LLM 的 raw markdown 组装，`context_gen` 负责把 raw context 变成适合注入 session 的 AI briefing。生成器会根据 agent type 选择 orchestrator、topic 或默认 scoped context，再合并 extra context、context files 和自动发现的 `CLAUDE.md` / `README.md`，最后用模板和 LLM caller 写入 per-agent cache。

## 相关页面

- [[agent-recall]]
- [[agent-memory]]
- [[mcp]]
- [[claude-code]]
- [[claude-mem]]
- [[agentmemory]]
- [[powermem]]
- [[ai-as-compressor]]
