---
title: mem0
tags: [entity, agent-memory, memory-layer, ai-agent, python]
date: 2026-06-12
sources: [mem0-architecture-analysis.md]
related: [[agent-memory]], [[agent-memory-selection-matrix]], [[powermem]], [[agentmemory]], [[memsearch]]
---

# mem0

通用 AI memory layer，面向应用和 Agent 提供长期记忆 API、SDK、OpenMemory、自托管服务和 MCP/CLI/agent plugins。详见 [[src-mem0-architecture]]。

## 架构边界

mem0 更像产品化 memory service / SDK，不是单个 coding agent 插件。它与 [[powermem]]、[[agentmemory]]、[[memsearch]] 的区别在于：mem0 更偏通用应用记忆和生态接入，PowerMem 偏数据库级混合检索与衰减模型，agentmemory 偏本地跨 agent memory bus，memsearch 偏 Markdown truth + Milvus hybrid search。

## 选型判断

| 需求 | 更适合 |
|---|---|
| 应用内用户记忆、SDK 接入 | mem0 |
| 数据库/企业级混合检索记忆 | [[powermem]] |
| 本地 agent 间共享记忆 | [[agentmemory]] |
| 代码/对话 Markdown 语义记忆 | [[memsearch]] |

## 相关源码页

- [[src-mem0-architecture]]
- [[agent-memory-selection-matrix]]
