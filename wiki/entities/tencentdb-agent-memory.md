---
title: TencentDB-Agent-Memory
tags: [agent-memory, ai-agent, llm-infra, open-source, tencent-cloud]
date: 2026-06-07
sources: [src-tencentdb-agent-memory-architecture]
related: [[agent-memory]], [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[hybrid-search-rrf]], [[agentmemory]], [[memsearch]], [[powermem]]
---

# TencentDB-Agent-Memory

TencentDB-Agent-Memory 是腾讯云开源的 OpenClaw / Hermes Agent 记忆插件（仓库 `TencentCloud/TencentDB-Agent-Memory`，npm 包 `@tencentdb-agent-memory/memory-tencentdb`，分析版本 v0.3.6 / HEAD `f92b102`）。它同时处理长期个性化记忆和短期上下文卸载。

## 解决什么

长程 Agent 有两类不同的“记忆”压力：

- **跨会话长期记忆**：用户偏好、SOP、历史事件和项目背景不能每次重讲。
- **单次长任务上下文压力**：工具输出、报错、搜索结果会快速挤满 context window。

TencentDB-Agent-Memory 用 L0→L1→L2→L3 处理长期记忆，用 context offload + Mermaid MMD 处理短期任务日志。

## 核心特征

- **四层长期记忆**：L0 Conversation、L1 Atom、L2 Scenario、L3 Persona。
- **OpenClaw hook 集成**：`before_prompt_build` 做 auto-recall，`agent_end` 做 auto-capture。
- **Agent 工具**：注册 `tdai_memory_search` 和 `tdai_conversation_search` 让 Agent 主动下钻。
- **双存储后端**：默认 SQLite + sqlite-vec + FTS5，也支持 Tencent Cloud VectorDB。
- **混合检索**：keyword / embedding / hybrid RRF；TCVDB 路径支持 native hybridSearch。
- **Context offload**：工具日志写入 `refs/*.md`，上下文注入 Mermaid 任务画布和 node_id。
- **Hermes sidecar**：Node Gateway 暴露 `/recall`、`/capture`、`/search/*`、`/session/end`、`/seed`，Python provider 管理进程。

## 架构骨架

| 层 | 组件 | 职责 |
|----|------|------|
| Host | OpenClaw plugin / Hermes provider / Gateway | 捕获宿主事件，转成 core 调用 |
| Core | `TdaiCore` | recall、capture、search、session flush |
| Pipeline | `MemoryPipelineManager` | L1/L2/L3 调度和恢复 |
| Store | SQLite / TCVDB | L0/L1 检索和 profile sync |
| Offload | `src/offload/*` | 长任务日志卸载、MMD 生成、L3 压缩 |

完整分析见 [[src-tencentdb-agent-memory-architecture]]。

## 与同类关系

和 [[agentmemory]] 相比，它更深度绑定 OpenClaw/Hermes 的 hook/context engine 体验；和 [[memsearch]] 相比，它不是 Markdown journal + Milvus shadow index，而是 JSONL/store/scene Markdown/persona Markdown 的分层组合；和 [[powermem]] 相比，它更偏 Agent 插件和上下文工程，而不是通用记忆中间件。

## 相关页面

- [[src-tencentdb-agent-memory-architecture]]
- [[agent-memory]]
- [[event-driven-memory-pipeline]]
- [[three-tier-search-protocol]]
- [[hybrid-search-rrf]]
- [[agentmemory]]
- [[memsearch]]
- [[powermem]]
