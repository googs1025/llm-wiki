---
title: 事件驱动的记忆管道
tags: [agent-memory, architecture, design-pattern, llm-infra]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[agent-memory]], [[ai-as-compressor]], [[three-tier-search-protocol]], [[claude-mem]]
---

# 事件驱动的记忆管道

给 AI Agent 加长期记忆的核心架构模式：**「事件采集 → AI 压缩 → 双索引存储 → 反向注入」** 的闭环。

由 [[claude-mem]] 实践验证，可移植到任何有生命周期 hook 的 Agent runtime。

## 五步闭环

```
Hook 事件
   ↓ (1) 捕获（边缘层）
原始 event (JSON)
   ↓ (2) 入队（持久化层）
Outbox 表
   ↓ (3) AI 压缩（后台层）
结构化 Observation (XML)
   ↓ (4) 解析双索引（存储层）
SQLite (FTS5) + 向量库
   ↓ (5) 注入回流（消费层）
新会话 system prompt / Skill 检索
```

### Step 1：捕获（边缘层）

Hook 触发 → 轻量 runner（如 bun-runner.js）收集 stdin → 派发到 handler → POST 给本地 worker。

> [!warning] 边缘层禁止做 AI 推理
> 用户交互路径上必须是同步、毫秒级、零网络依赖。AI 调用全部异步化。

### Step 2：入队（持久化层）

worker 把原始 event 写入 outbox 表（Postgres 的 `LISTEN/NOTIFY` 或 SQLite 暂存），BullMQ 等队列调度后台任务异步处理。

**为什么必须 outbox**：AI 生成是非确定的，失败必须能重试；同步处理会阻塞用户。

### Step 3：AI 压缩（后台层）

调用 [[ai-as-compressor|压缩器]] 把噪声大的 tool log 压成结构化 `{title, narrative, facts[], concepts[], filesRead[], filesModified[]}`。

claude-mem 用 XML 输出格式 + Zod schema 校验，便宜模型（Haiku / Gemini Flash）足够。

### Step 4：解析存储（双索引层）

事务化写入：

- **SQLite + FTS5**：主存储 + 全文检索
- **Chroma 向量库**：语义检索（异步推送 + watermark 回填）

去重策略：内容哈希 + UNIQUE `generation_key` + `ON CONFLICT`。

### Step 5：注入回流（消费层）

- **自动注入**：`SessionStart` 时按"项目路径 + 最近活跃概念"预检索，渲染成 system 消息塞回上下文窗口
- **按需查询**：用户问"上次怎么做的"时，[[three-tier-search-protocol|三层搜索协议]] 通过注册的 Skill 自动触发

## 关键设计原则

| 原则 | 含义 |
|------|------|
| **边缘轻量 + 后台 AI 重活** | hook 同步只走 stdin → HTTP，AI 压缩异步 |
| **Outbox 模式** | 失败可重试，不丢消息 |
| **内容哈希去重** | AI 输出非确定，避免重复污染索引 |
| **三层数据** | 原始 event → 结构化观察 → 向量 embedding |
| **session_id 双轨** | 记忆生命周期 ≠ 会话生命周期 |
| **边缘剥离敏感数据** | `<private>` 标签在 hook 层剥离，零信任 |

## 可迁移到的 Runtime

任何有 before/after tool_use 钩子的 Agent runtime：

- Claude Code Lifecycle Hooks
- OpenAI Assistants 的 step events
- AutoGen 的 agent_event 回调
- LangChain 的 callback handlers

## 参考

- [[src-claude-mem-architecture]]
