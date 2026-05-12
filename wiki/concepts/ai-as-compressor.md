---
title: AI 作为压缩器
tags: [agent-memory, design-pattern, llm-infra, token-economy]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[agent-memory]], [[event-driven-memory-pipeline]], [[claude-mem]], [[claude-agent-sdk]]
---

# AI 作为压缩器

> 把 LLM 当"信息浓缩器"而不是"问答器"——压缩 token 成本换后续检索效率。

由 [[claude-mem]] 的架构验证的核心设计哲学。

## 反直觉之处

大多数 AI 应用把 LLM 当作**问答接口**——用户提问 → LLM 直接回答。

[[claude-mem]] 反过来用：LLM 不面向用户，而是**后台默默地把噪声日志压成结构化事实**。

```
噪声大的 tool log（数千 token）
   ↓ LLM 压缩（一次性成本）
结构化 Observation（百级 token）
{
  facts: ["修复了 ingest workflow 中的 wikilink 漏抽问题"],
  concepts: ["wiki maintenance", "link integrity"],
  filesModified: ["wiki/concepts/xxx.md"]
}
   ↓
向量库 + FTS5 双索引
   ↓
后续 N 次会话检索（持续收益）
```

## 经济学逻辑

| 维度 | 不压缩 | 压缩后 |
|------|-------|-------|
| 一次性成本 | 0 | 一次 LLM 调用（~$0.001 用 Haiku） |
| 每次检索 token | 数千（全文） | 数百（结构化摘要） |
| 检索精度 | 低（关键词匹配噪声） | 高（concepts 字段） |
| 跨会话复用 | 难（全文太长） | 易（短小可拼） |

**核心洞察**：压缩是一次性付费、永久收益的操作。每多一次检索，回报就翻一倍。

## 为什么便宜模型够用

压缩任务的特点：

- 输入是结构化的 tool log（不需要复杂推理）
- 输出是预定义 schema（不需要创造性）
- 错误可以通过 outbox 重试（不需要一次到位）

→ Claude Haiku / Gemini Flash 完全胜任，成本可压到主模型的 1/10。

[[claude-agent-sdk]] 的 multi-provider 抽象就是为此而生。

## 输出 Schema 设计

不要让 LLM 自由发挥，必须给定 schema：

```typescript
{
  title: string,              // 一句话标题（用于 search 摘要层）
  narrative: string,          // 叙述（用于详情层）
  facts: string[],            // 离散事实（可索引）
  concepts: string[],         // 抽象标签（用于预检索）
  filesRead: string[],
  filesModified: string[]
}
```

每个字段都对应某一层检索使用——schema 设计直接决定后续检索能力。

## 可迁移性

任何"AI Agent + 长期存储"场景都该考虑：

- 不只是对话历史，而是工具调用、API 响应、错误日志
- 不只是聊天 Agent，运维 Agent（压缩告警）、代码 Agent（压缩 PR diff）同样适用
- 与 [[event-driven-memory-pipeline]] 配合形成完整闭环

## 参考

- [[src-claude-mem-architecture]]
