---
title: claude-mem 架构与设计思路分析
tags: [agent-memory, claude-code, architecture, llm-infra]
date: 2026-05-12
sources: [claude-mem-architecture-analysis.md]
related: [[claude-mem]], [[claude-code]], [[claude-agent-sdk]], [[agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[ai-as-compressor]]
---

# claude-mem 架构与设计思路分析

> 原文：`raw/claude-mem-architecture-analysis.md` · 仓库：[thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) · 分析版本 v13.1.0

## 一句话定位

[[claude-mem]] 是给 [[claude-code]] 装上"长期记忆"的开源插件——通过宿主的 6 个 Lifecycle Hook **无侵入采集**工具调用，用 [[claude-agent-sdk]] 异步压缩成结构化"观察 (observation)"，存进本地 SQLite + Chroma 双索引；下次开会话时自动检索相关历史并注入上下文。

## 核心架构（三层）

| 层 | 组件 | 职责 |
|---|------|------|
| **边缘层** | `bun-runner.js` + 6 个 hook handler | 轻量 stdin 接力，**禁止做 AI 推理** |
| **后台层** | Worker Service (Express daemon, 端口 `37700 + uid%100`) + BullMQ | 异步压缩、入库、向量同步 |
| **存储层** | SQLite (FTS5 全文) + Chroma (向量) | 双索引 |

详见 [[event-driven-memory-pipeline]]。

## 六个生命周期钩子

| 阶段 | 触发 | Handler | 作用 |
|------|------|---------|------|
| Setup | 插件初始化 | `version-check.js` | 版本兼容性 |
| **SessionStart** | 启动/clear/compact | `context.ts` | 启 worker + **注入历史上下文** |
| **UserPromptSubmit** | 用户提交 prompt | `session-init.ts` | 创建 session + 触发语义搜索 |
| PreToolUse(Read) | 读文件前 | `file-context.ts` | 查当前文件相关观察 |
| **PostToolUse** | 任何工具调用后 | `observation.ts` | 入队等待压缩 |
| Stop | 会话结束 | `summarize.ts` | 生成会话摘要 |

## 五步闭环

1. **捕获**：Hook → `bun-runner.js` → worker handler → POST 给本地 worker
2. **入队**：写 outbox（Postgres）或 SQLite 暂存，BullMQ 调度
3. **AI 压缩**：`ProviderObservationGenerator` 调 Agent SDK，把 tool log 压成 XML 观察
4. **解析存储**：`sdk/parser.ts` → `MemoryItem` schema → 事务写入 SQLite + 异步推 Chroma
5. **注入回流**：`SessionStart` 预检索 → system 消息；或 `mem-search` Skill 按需查询

## 六大可移植设计模式

1. **生命周期钩子采集** — 任何有 before/after tool_use 钩子的 runtime 都能挂
2. **边缘轻量 + 后台 AI 重活** — 用户交互路径上绝不做 AI 推理
3. **三层搜索协议** — `search → timeline → get_observations`，详见 [[three-tier-search-protocol]]
4. **AI 作为压缩器** — 详见 [[ai-as-compressor]]
5. **session_id 双轨制** — `contentSessionId`（会话）vs `memorySessionId`（记忆线）
6. **Outbox + 内容哈希去重** — AI 生成非确定，必须去重；outbox 让重试不丢消息

## MemoryItem Schema

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

> [!note] 关键洞察
> 别只存"对话历史"，先压缩成"事实/概念/读写文件"等可索引字段；语义搜索叠在结构化层之上。

## 多 Profile 隔离

```bash
export CLAUDE_MEM_DATA_DIR="$HOME/.claude-mem-work"
export CLAUDE_MEM_WORKER_PORT=37800
```

所有路径（DB、Chroma、日志、PID）从 env 派生，shell 级隔离。

## 演进信号

近 30 天最活跃：`worker-service.cjs`（88 次）、`mcp-server.cjs`（75 次）。PR #2383 把 worker 重写为 **server-beta**：事件管道 + Postgres + MCP + Docker + 团队审计。趋势是从「单机插件」→「团队后台服务」，但 `runtime-selector.ts` 保留单机 SQLite 回退。

## 关键文件索引

| 关注点 | 路径 |
|--------|------|
| 钩子注册 | `plugin/hooks/hooks.json` |
| Hook 派发 | `plugin/scripts/bun-runner.js` |
| Worker 入口 | `src/services/worker-service.ts` |
| Provider 抽象 | `src/sdk/{Claude,Gemini,OpenRouter}Provider.ts` |
| XML 解析 | `src/sdk/parser.ts` |
| 上下文构建 | `src/services/context/ContextBuilder.ts` |
| 压缩 Prompt | `src/sdk/prompts.ts` |
| 搜索 Skill | `plugin/skills/mem-search/SKILL.md` |

## 最小可行落地（抄作业 5 步）

给任何 Agent 加记忆的最小套路：

1. **采集**：tool callback 里 `record_event(event)` 塞 SQLite outbox
2. **压缩**：cron/worker 跑 `compress_batch()`，喂给便宜模型（Haiku / Gemini Flash）输出 `{title, narrative, facts[], concepts[]}` JSON
3. **双索引**：SQLite FTS5 + 向量库
4. **注册搜索工具**：`search_memory(query)`，描述写"用户提到过去/上次时调用"
5. **会话启动预检索**：基于"项目路径 + 最近活跃概念"拼 system prompt 前缀
