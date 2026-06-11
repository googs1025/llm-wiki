---
title: Agent Memory 细分选型矩阵
tags: [agent-memory, project-map, selection, ai-agent]
date: 2026-06-11
sources: [src-claude-mem-architecture, src-agent-recall-architecture, src-agentmemory-architecture, src-powermem-architecture, src-memsearch-architecture, src-tencentdb-agent-memory-architecture]
related: [[agent-memory]], [[claude-mem]], [[agent-recall]], [[agentmemory]], [[powermem]], [[memsearch]], [[tencentdb-agent-memory]], [[hybrid-search-rrf]]
---

# Agent Memory 细分选型矩阵

已有 [[agent-memory-project-map]] 做了完整横向地图。这页进一步按“选型问题”拆：你要给 coding agent、产品应用、企业平台还是可审计知识库加记忆。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 当前信号 |
|------|------|-----------|-------|--------|----------|
| [[claude-mem]] | https://github.com/thedotmack/claude-mem | 2026-06-11 | 81k | JavaScript | 从 Claude Code 扩展到多 Agent 的 persistent context |
| [[agent-recall]] | https://github.com/mnardit/agent-recall | 2026-04-03 | 12 | Python | 小而专注，SQLite + MCP scope memory |
| [[agentmemory]] | https://github.com/rohitg00/agentmemory | 2026-06-10 | 22k | TypeScript | 跨 coding agent，本地 worker + MCP/REST |
| [[powermem]] | https://github.com/oceanbase/powermem | 2026-06-10 | 703 | Python | 应用级 memory middleware，OceanBase/SeekDB 路线 |
| [[memsearch]] | https://github.com/zilliztech/memsearch | 2026-06-01 | 1.9k | Python | Markdown truth + Milvus shadow index |
| [[tencentdb-agent-memory]] | https://github.com/TencentCloud/TencentDB-Agent-Memory | 2026-06-04 | 5.2k | TypeScript | OpenClaw/Hermes 本地分层记忆 |

## 按需求选

| 需求 | 推荐 | 为什么 |
|------|------|--------|
| Claude Code 用户马上要跨会话记忆 | [[claude-mem]] | hook 接入自然，自动采集和注入路径成熟 |
| 多个 coding agent 共用本地记忆 | [[agentmemory]] 或 [[memsearch]] | agentmemory 偏服务/工具面，memsearch 偏 Markdown 可审计 |
| 多项目/多客户 scoped facts | [[agent-recall]] | scope hierarchy、bitemporal slots、MCP instructions 更明确 |
| 产品应用内用户记忆 | [[powermem]] | SDK/API/MCP/Dashboard、provider 和存储适配完整 |
| OpenClaw/Hermes 长任务和 persona | [[tencentdb-agent-memory]] | L0→L3 语义金字塔 + context offload |
| 人类要能 review/修正记忆 | [[memsearch]] | Markdown source-of-truth，索引可重建 |

## 架构差异

| 维度 | [[claude-mem]] | [[agent-recall]] | [[agentmemory]] | [[powermem]] | [[memsearch]] | [[tencentdb-agent-memory]] |
|------|----------------|------------------|-----------------|--------------|---------------|----------------------------|
| 写入边界 | hook 被动采集 | Agent 主动 MCP 写入 | hooks/REST/MCP 多入口 | SDK/API 显式写入 | hook 追加 Markdown | hook 捕获 + 分层 pipeline |
| 真相层 | SQLite observations | SQLite graph/slots | iii-engine SQLite KV | OceanBase/SeekDB/PG/SQLite | Markdown files | JSONL/files + SQLite/TCVDB |
| 索引层 | FTS5 + Chroma | FTS5/LIKE | BM25 + vector + graph | vector + FTS + sparse + graph | Milvus dense + sparse | SQLite/TCVDB hybrid |
| LLM 成本 | 压缩核心 | briefing 可选/cache | 默认零 LLM | 抽取/评估核心 | 维护摘要/可选 | L0→L3 管线核心 |
| 注入策略 | SessionStart 自动上下文 | scoped briefing | 默认可关闭注入 | 应用决定 | search/expand 渐进 | before_prompt_build + offload |

## 关键取舍

- **自动记忆 vs 主动记忆**：[[claude-mem]]、[[agentmemory]]、[[tencentdb-agent-memory]] 覆盖率高但需要去噪；[[agent-recall]] 结构更清楚但依赖 Agent 主动保存。
- **数据库 truth vs Markdown truth**：数据库查询快、结构强；Markdown 可 diff、可审计、可手改。[[memsearch]] 是 Markdown truth 的代表。
- **零 LLM 默认 vs AI 压缩**：[[agentmemory]] 默认保护 token 成本；[[powermem]] 和 [[tencentdb-agent-memory]] 更依赖 LLM 抽取换取语义质量。
- **个人插件 vs 服务化层**：[[claude-mem]] 贴近宿主；[[powermem]] 更像应用基础设施；[[agentmemory]] 在中间。

## 避坑条件

- 记忆系统必须区分 truth store 和 shadow index；不要把 embedding collection 当唯一事实。
- 自动注入默认要保守，否则会消耗 coding agent 上下文窗口。
- 多 Agent 共享记忆必须有 scope / tenant / project 边界。
- “支持 MCP”不等于写入策略成熟；要看 tool instructions、权限 enforcement 和恢复模型。

