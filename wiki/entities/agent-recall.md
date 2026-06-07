---
title: agent-recall
tags: [agent-memory, ai-agent, llm-infra, open-source, mcp]
date: 2026-06-06
sources: [src-agent-recall-architecture]
related: [[agent-memory]], [[mcp]], [[claude-code]], [[claude-mem]], [[agentmemory]], [[powermem]], [[ai-as-compressor]]
---

# agent-recall

agent-recall 是 Max Nardit 开源的本地优先 [[agent-memory]] 系统（仓库 `mnardit/agent-recall`，MIT）。它面向 [[claude-code]]、Cursor、Windsurf、Cline 等 MCP-compatible coding agents，通过 [[mcp]] tools 保存实体、关系、观察和日志，再在 session start 时注入 AI briefing。

## 解决的问题

coding agent 跨 session 会忘记人名、项目决策、偏好、上下文和未完成事项。agent-recall 用一份本地 SQLite 数据库保存这些事实，并用 scope hierarchy 让同一个人或项目在不同客户、团队、topic 下有不同上下文。

## 核心特征

- **MCP-native memory tools**：`create_entities`、`add_observations`、`search_nodes`、`open_nodes` 等 9 个工具，server instructions 要求 Agent 主动保存重要上下文。
- **Scope hierarchy**：`memory.yaml` 定义 hierarchy、tiers、agent types；`MCPBridge` 按 scope chain 做读写过滤。
- **本地 SQLite**：默认 `~/.agent-recall/frames.db`，FTS5 可用时做全文搜索，无向量库或云服务默认依赖。
- **Bitemporal slots**：结构化 key-value 旧值归档，不直接覆盖历史。
- **AI briefings**：session start 时优先读取 per-agent cache；cache miss 时从 store 组装 raw context，也可调用 Claude CLI / Anthropic API 生成压缩 briefing。
- **Claude hooks**：`agent-recall-session-start` 自动注入上下文，`agent-recall-post-tool-use` 在记忆写入后做 adaptive cache invalidation。

## 架构骨架

- **接口层**：`mcp_server.py`、`cli.py`、`hooks.py`
- **权限层**：`mcp_bridge.py`，多 Agent 读写 scope enforcement 边界
- **存储层**：`store.py` + `migrations.py`，单 SQLite 文件和 FTS5 fallback
- **上下文层**：`context.py` + `context_gen/*`，raw context assembly、模板、LLM caller、cache

完整分析见 [[src-agent-recall-architecture]]。

## 与同类关系

| 维度 | agent-recall | [[claude-mem]] | [[agentmemory]] | [[powermem]] |
|------|--------------|----------------|-----------------|--------------|
| 部署 | Python package + SQLite | Claude Code plugin | Node/iii-engine worker | 数据库/服务层 memory middleware |
| 客户端 | MCP clients + CLI + hooks | Claude Code 为主 | 多 Agent hooks + MCP + REST | SDK / API / MCP / Dashboard |
| 隔离 | scope hierarchy | profile/workspace | shared worker scopes | 应用侧租户边界 |
| AI 用法 | briefing 压缩，可 cache | LLM 压缩核心 | 默认零 LLM，可选压缩 | LLM 抽取/优化更深 |

设计上，agent-recall 比 [[claude-mem]] 更强调多 scope 组织结构，比 [[agentmemory]] 更轻量，比 [[powermem]] 更贴近个人 coding agent 本地工作流。

## 相关页面

- [[src-agent-recall-architecture]]
- [[agent-memory]]
- [[mcp]]
- [[claude-code]]
- [[claude-mem]]
- [[agentmemory]]
- [[powermem]]
- [[ai-as-compressor]]
