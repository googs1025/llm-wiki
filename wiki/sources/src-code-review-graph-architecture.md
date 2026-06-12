---
title: code-review-graph 架构与设计思路分析
tags: [architecture, code-intelligence, graph-rag, mcp, coding-agent]
date: 2026-06-12
sources: [code-review-graph-architecture-analysis.md]
related: [[[code-semantic-search-rag-map]], [[coding-agent-selection-map]], [[mcp]], [[agent-skills-plugin-system-map]]]
---

# code-review-graph 架构与设计思路分析

`tirth8205/code-review-graph` 是本地优先 code intelligence graph，目标是给 MCP/CLI/coding agent 提供结构化代码上下文，尤其服务 code review、delta review、debug/refactor。仓库有 Python core、tools、VSCode extension、skills、docs/tests。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `tirth8205/code-review-graph` 是本地优先 code intelligence graph，目标是给 MCP/CLI… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `code_review_graph/**` · `code_review_graph/tools/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `skills/**`                     │  │ `code-review-graph-vscode/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `code_review_graph/**` | Python 核心图构建/查询。 |
| `code_review_graph/tools/**` | CLI/MCP 工具。 |
| `skills/**` | build graph、review changes、review PR、debug issue 等技能。 |
| `code-review-graph-vscode/**` | VSCode extension。 |

## 关键数据流

1. 本地仓库被解析成代码图。
2. agent/CLI/MCP 根据任务查询相关节点、边、diff 或 review context。
3. 技能把常见 review/refactor 流程固化为 agent instructions。

## 设计决策

- local-first 保护代码隐私，也减少服务端依赖。
- 从 vector search 升级到 code graph，适合补 code RAG 地图。
- skills 与 MCP tools 并存，说明它面向 coding agent 工作流。

## 对比定位

和 Claude Context/memsearch 相比，它更图谱化；和 deepwiki-open 相比，它服务交互式 review，不是生成静态 wiki。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
