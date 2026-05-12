# claude-mem 架构与设计思路分析

> 项目仓库：[thedotmack/claude-mem](https://github.com/thedotmack/claude-mem)
> 分析版本：v13.1.0
> 分析日期：2026-05-12

## 一、项目定位与作用

**claude-mem** 是给 [Claude Code](https://claude.com/claude-code) 装上"长期记忆"的开源插件。

宿主 Claude Code 本身没有跨会话记忆——每次开新会话都是白板。claude-mem 通过 Claude Code 提供的 **6 个生命周期 hook**，无侵入地捕获每一次工具调用，用 Claude Agent SDK 异步压缩成结构化"观察 (observation)"，存进本地 SQLite + Chroma 向量库；下次开会话时自动检索相关历史并注入到上下文窗口。

一句话：**把每次会话里所有工具调用异步压缩成结构化"观察"，存进本地双索引（全文 + 向量），下次开会话时自动注入相关历史。**

### 核心价值

- **跨会话连续性**：用户问"上次怎么解决这个 bug"时，Agent 能真的检索到上次的解决步骤
- **本地优先**：所有记忆数据都存本地（`~/.claude-mem/`），开源核心可审计
- **无侵入采集**：通过宿主的 hook 接口工作，不修改 Claude Code 本身
- **多 profile 支持**：通过两个环境变量切换工作账号 / 私人账号

---

## 二、整体架构

```
┌─────────────────────────  CLAUDE CODE 运行时  ─────────────────────────┐
│                                                                          │
│  事件钩子（plugin/hooks/hooks.json 注册的 6 个 Lifecycle 钩子）           │
│  ┌────────────┐ ┌──────────────┐ ┌────────────────┐ ┌─────────────┐    │
│  │SessionStart│ │UserPromptSub │ │PreToolUse(Read)│ │PostToolUse  │    │
│  └─────┬──────┘ └──────┬───────┘ └────────┬───────┘ └──────┬──────┘    │
│        │               │                  │                │           │
│        ▼               ▼                  ▼                ▼           │
│   bun-runner.js（轻量 stdin 接力 → 派发 worker-service 子命令）           │
└─────────────────────────────┬───────────────────────────────────────────┘
                              │ HTTP / 进程派发
                              ▼
┌────────────────────  Worker Service (Express daemon)  ────────────────────┐
│  src/services/worker-service.ts                                            │
│  端口: 37700 + (uid % 100)  •  PID: ~/.claude-mem/worker.pid               │
│                                                                            │
│  路由层（7 组 Routes）                                                     │
│   /api/context/*   /api/sessions/*   /api/observations                     │
│   /api/search/*    /api/memory/save  /api/chroma/status   /v1/*            │
│                                                                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐    │
│  │ Providers        │  │ ResponseProcessor│  │ ChromaSync           │    │
│  │ Claude/Gemini/OR │→ │ XML→Observation  │→ │ 向量同步 + watermark │    │
│  │ (Agent SDK 调用) │  │ 事务批量入库     │  │ 回填                  │    │
│  └──────────────────┘  └────────┬─────────┘  └──────────┬───────────┘    │
└─────────────────────────────────┼────────────────────────┼────────────────┘
                                  ▼                        ▼
                       ┌────────────────────┐   ┌────────────────────┐
                       │ SQLite             │   │ Chroma 向量库      │
                       │ ~/.claude-mem/.db  │   │ ~/.claude-mem/chroma│
                       │ observations / FTS5│   │ 语义检索           │
                       │ sessions / prompts │   │                    │
                       └─────────┬──────────┘   └─────────┬──────────┘
                                 └─────────┬──────────────┘
                                           │
                          ┌────────────────┴────────────────┐
                          ▼                                 ▼
                ┌──────────────────┐               ┌──────────────────┐
                │ mem-search Skill │               │ Viewer UI (React)│
                │ 3 层搜索协议     │               │ SSE 流式渲染     │
                │ search→timeline  │               │ 时间线/观察列表  │
                │ →get_observations│               │                  │
                └──────────────────┘               └──────────────────┘
```

### 六个生命周期钩子

| 阶段                   | 触发条件                 | 处理器                | 作用                         |
| -------------------- | -------------------- | ------------------ | -------------------------- |
| **Setup**            | 插件初始化                | `version-check.js` | 版本兼容性检查                    |
| **SessionStart**     | 启动 / clear / compact | `context.ts`       | 启动 worker daemon + 注入历史上下文 |
| **UserPromptSubmit** | 用户提交 prompt          | `session-init.ts`  | 创建 session 记录 + 触发语义搜索     |
| **PreToolUse(Read)** | 读取文件前                | `file-context.ts`  | 查询当前文件相关 observation       |
| **PostToolUse**      | 任何工具调用后              | `observation.ts`   | 把工具调用入队等待压缩                |
| **Stop**             | 会话结束                 | `summarize.ts`     | 生成会话摘要                     |

---

## 三、核心工作流：从事件到记忆的 5 步闭环

### Step 1：捕获（边缘层）

Claude Code 触发 hook → `bun-runner.js` 收集 stdin → 派发到 `worker-service.cjs <subcommand>` → 调用对应 handler（如 `src/cli/handlers/observation.ts`）→ POST 给本地 worker。

**关键约束**：所有 hook 必须返回 exit 0（CLAUDE.md 明确：Windows Terminal 会因非零退出累积标签页），错误走 stderr 但不阻塞主流程。

### Step 2：入队（持久化层）

worker 把原始 event 写入 PostgreSQL outbox（server-beta 模式）或 SQLite 暂存，**BullMQ** 调度后台任务异步处理。这一步是设计上的精华——**用户交互路径上绝不做 AI 推理**。

### Step 3：AI 压缩（后台层）

`ProviderObservationGenerator` 从 outbox 取批 → 调用 Claude Agent SDK 的 `query()`（支持 Claude / Gemini / OpenRouter 三个 Provider）→ 用预设 prompt 把噪声大的 tool log 压成 XML 格式的结构化观察。

### Step 4：解析存储（双索引层）

`sdk/parser.ts` 把 XML 解析成 `MemoryItem` schema：

```typescript
{
  kind: 'observation' | 'summary' | 'prompt' | 'manual',
  type: string,
  title: string,
  narrative: string,       // 自然语言叙述
  facts: string[],         // 离散事实点
  concepts: string[],      // 抽象概念标签
  filesRead: string[],
  filesModified: string[]
}
```

事务化写入 SQLite（含 FTS5 全文索引）+ 异步推送 Chroma 向量库。

### Step 5：注入回流（消费层）

- **自动注入**：新会话 `SessionStart` 时，`ContextBuilder.generateContext()` 按项目路径 + 最近活跃概念预检索，渲染成 system 消息塞回 Claude 上下文窗口
- **按需查询**：用户问"我之前做过什么"时，注册的 `mem-search` Skill 自动触发，走三层搜索协议

---

## 四、关键设计模式

### 1. 三层搜索协议（防止上下文爆炸）

```
search(query)          → 返回 ID 列表 + 一句话摘要      (~50-100 tokens/result)
   ↓
timeline(anchor_id)    → 围绕锚点取上下文窗口
   ↓
get_observations(ids)  → 仅取筛选后的 ID 全文
```

**核心思想**：永远先返低 token 摘要，让模型筛选后再取详情。比一次性返回所有匹配结果省 10x token。

### 2. session_id 双轨制

- `contentSessionId`：当前对话会话 ID（短期）
- `memorySessionId`：跨 session 累积的记忆线 ID（长期）

**核心思想**：记忆的生命周期 ≠ 会话的生命周期，必须分两个 ID 才能跨 session 累积同一项工作的上下文。

### 3. Outbox + 内容哈希去重

- 原始 event 写入 outbox 表，AI 处理失败可重试不丢消息
- 生成的 observation 用内容哈希 + UNIQUE `generation_key` + `ON CONFLICT` 去重
- AI 生成是非确定的，没有去重策略一定会产生重复观察污染索引

### 4. 边缘剥离敏感数据

`<private>...</private>` 标签的剥离发生在 **hook 层（边缘）**，不是到 worker 之后才处理。代码在 `src/utils/tag-stripping.ts`。

**核心思想**：敏感数据零信任地处理——敏感内容在数据离开本地进程之前就被剥离，永不进入压缩管道。

### 5. 多 profile 通过环境变量隔离

```bash
export CLAUDE_MEM_DATA_DIR="$HOME/.claude-mem-work"
export CLAUDE_MEM_WORKER_PORT=37800
```

所有路径（DB、Chroma、日志、settings、PID）和默认端口（`37700 + uid % 100`）都从这两个 env 派生。

**核心思想**：不要用 CLI 子命令切账号，统一从 env var 派生，shell 级隔离最省心、最不出错。

### 6. AI 作为压缩器而非问答器

claude-mem 调用 LLM 的目的不是"回答用户"，而是把噪声大的工具调用日志压缩成结构化的"事实/概念/读写文件"等可索引字段。压缩用的 token 成本，换来的是后续每次会话的检索效率。

---

## 五、技术栈

| 类别 | 选型 | 用途 |
|------|------|------|
| 语言 | TypeScript (Bun runtime) | 全栈 |
| Worker 框架 | Express | HTTP API daemon |
| AI SDK | `@anthropic-ai/claude-agent-sdk` | 压缩 / 总结 |
| Multi-provider | Claude / Gemini / OpenRouter | AI 厂商解耦 |
| 任务队列 | BullMQ | 后台异步处理 |
| 关系数据 | better-sqlite3 + FTS5 | 主存储 + 全文检索 |
| 向量数据 | Chroma | 语义检索 |
| 进程管理 | 自研 Supervisor + ProcessManager | worker daemon 生命周期 |
| UI | React + SSE | Viewer 实时流式 |
| 协议 | MCP (Model Context Protocol) | Skill / 远程模式 |

---

## 六、近期演进方向（Git 信号）

近 30 天最活跃文件是 `plugin/scripts/worker-service.cjs`（88 次改动）和 `plugin/scripts/mcp-server.cjs`（75 次）。最大架构变更是 PR #2383：把 worker 重写为 **server-beta**——事件管道 + Postgres + MCP + Docker + 团队审计 + 可观测性。

**演进趋势**：从"单机插件"演化到"团队可共享的后台服务"，但通过 `runtime-selector.ts` 保留对单机 SQLite 模式的回退兼容。

---

## 七、如何抽取这套设计思路到其他 AI Agent

这套架构的精华是 **"事件采集 → AI 压缩 → 向量+全文双索引 → 反向注入"** 的闭环。下表把可移植的设计原则单独列出。

| 设计模式 | claude-mem 的做法 | 抽象后可用于任何 Agent |
|---------|------------------|----------------------|
| **生命周期钩子采集** | 6 个 Lifecycle hook 派发到 worker | 任何 Agent runtime 只要有 `before/after tool_use` 钩子就能挂采集器；OpenAI Assistants 用 step events，AutoGen 用 agent_event 回调，LangChain 用 callback handlers |
| **边缘轻量 + 后台 AI 重活** | hook 同步只走 stdin → HTTP，AI 压缩异步 BullMQ | 永远不要在用户交互路径上做 AI 推理；放队列、给个 outbox 表、worker 慢慢吃 |
| **三层数据结构** | 原始 event → 结构化 observation → 向量 embedding | 别只存"对话历史"，先压缩成"事实/概念/读写文件"等可索引字段；语义搜索叠在结构化层之上 |
| **AI 作为压缩器** | 用 Claude 把噪声大的 tool log 压成 5-10 个 fact bullet | 把 LLM 当"信息浓缩器"而不是"问答器"——压缩 token 成本换后续检索效率 |
| **Skill 作为反向调用入口** | 注册 `mem-search` Skill，用户问"上次怎么解决的"时 Agent 自己会搜 | 给 Agent 注册一个"查记忆"工具，提示词写清调用时机，模型自己学会触发 |
| **三层搜索协议** | search(ID 列表) → timeline(上下文) → get_observations(全文) | 永远先返低 token 摘要 + ID，让模型筛选后再取详情 |
| **本地优先 + 可选远程** | SQLite/Chroma 本地，Pro UI 远程外挂；endpoint 全开放 | 把存储和高级功能解耦，核心免费可审计，付费层只做体验增强 |
| **多 profile 通过 env var 隔离** | `CLAUDE_MEM_DATA_DIR` 派生所有路径 | 统一从 env var 派生数据/端口，shell 级隔离最省心 |
| **session_id 双轨制** | `contentSessionId` vs `memorySessionId` | 记忆生命周期 ≠ 会话生命周期，必须分两个 ID 才能跨 session 累积 |
| **Outbox + 哈希去重** | 内容哈希 + UNIQUE `generation_key` + `ON CONFLICT` | AI 生成是非确定的，任何"压缩入库"都必须有去重；outbox 让你能重试不丢消息 |
| **边缘剥离敏感数据** | `<private>` 标签在 hook 层就剥离 | 敏感数据处理要尽量靠近产生源头，零信任原则 |

### 最小可行落地（5 步抄作业）

如果要给某个 LangChain / AutoGen / OpenAI 自研 Agent 加记忆，最小可行套路：

1. **采集**：在 tool callback 里写一个 `record_event(event)` 把工具调用塞进本地 SQLite outbox 表
2. **压缩**：后台 cron / worker 跑 `compress_batch()`——拿 N 个 event 喂给一个便宜模型（Haiku / Gemini Flash），让它生成 `{title, narrative, facts[], concepts[]}` 的 JSON
3. **双索引**：入库 SQLite (FTS5 全文) + 算 embedding 存向量库
4. **注册搜索工具**：给 Agent 注册一个 `search_memory(query)` 工具，描述里写"当用户提到过去 / 上次 / 之前时调用"
5. **会话启动预检索**：新会话开启时跑一次基于"项目路径 + 最近活跃概念"的预检索，把 top-K 观察拼成 system prompt 前缀

照着这 5 步抄，就有了 claude-mem 的最小内核。

---

## 八、关键文件索引

| 关注点 | 文件路径 |
|--------|---------|
| 钩子注册表 | `plugin/hooks/hooks.json` |
| Hook 派发入口 | `plugin/scripts/bun-runner.js` |
| Worker daemon 入口 | `src/services/worker-service.ts` |
| Hook handler 集合 | `src/cli/handlers/{context,session-init,observation,file-context,summarize}.ts` |
| AI Provider 抽象 | `src/sdk/{ClaudeProvider,GeminiProvider,OpenRouterProvider}.ts` |
| XML 解析器 | `src/sdk/parser.ts` |
| 响应处理 / 入库 | `src/services/.../ResponseProcessor.ts` |
| 数据库 Schema | `src/services/sqlite/migrations.ts` |
| 向量同步 | `src/services/sync/ChromaSync.ts` |
| 上下文构建 | `src/services/context/ContextBuilder.ts` |
| 核心 Zod schemas | `src/core/schemas/{agent-event,memory-item,session}.ts` |
| 搜索 Skill | `plugin/skills/mem-search/SKILL.md` |
| Viewer UI | `src/ui/viewer/{index.tsx,App.tsx}` |

---

## 九、深入探索方向

1. **Prompt 模板**：`src/sdk/prompts.ts` 里的压缩 prompt 决定了观察质量，是这套系统效果好坏的核心
2. **server-beta 模式**：PostgreSQL + MCP + BullMQ 的团队共享后台是怎么和单机 SQLite 模式共存的（看 `runtime-selector.ts`）
3. **Skill 触发机制**：Claude 是怎么"自主决定"调用 mem-search 的——SKILL.md 的描述文案艺术
4. **Token 经济性**：`ContextBuilder` 怎么在有限的上下文窗口里选最相关的观察（`token-calculator.ts`）
