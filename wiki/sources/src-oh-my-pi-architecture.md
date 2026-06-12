---
title: oh-my-pi 架构与设计思路分析
tags: [architecture, coding-agent, tool-harness, lsp, rust]
date: 2026-06-12
sources: [oh-my-pi-architecture-analysis.md]
related: [[[coding-agent-selection-map]], [[agent-skills-plugin-system-map]], [[code-semantic-search-rag-map]], [[mcp]], [[claude-code]], [[agent-memory-project-map]]]
---

# oh-my-pi 架构与设计思路分析

`can1357/oh-my-pi` 是 Pi fork，但定位已经从“harness monorepo”升级成强工具 coding-agent 产品。README 直接强调 IDE wired in、32 tools、13 LSP ops、27 DAP ops、hashline edit、persistent eval、subagents、browser/web_search、memory、ACP/editor drive、conflict resolution 等能力；仓库也有 Rust `crates/pi-*` 原生层支撑搜索、AST、shell、isolated copy。

## 核心架构图

```text
┌──────────────────────────── omp CLI / TUI / editor ACP ──────────────────────┐
│ prompts · skills · rules · session tree · review/commit/conflict workflows    │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ TypeScript agent/tool runtime                                                 │
│ read/write/edit/search/bash/eval/lsp/debug/browser/task/memory/web_search     │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ Rust native crates            │  │ external systems                            │
│ pi-ast · pi-shell · pi-iso     │  │ LSP · DAP · browser · MCP · GitHub schemes  │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ workspace changes with hash anchors, proposed edits, checkpoints, memories    │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `packages/coding-agent` | CLI/TUI agent 主体、session、tool runtime、prompts。 |
| `packages/ai` | 多 provider 模型/catalog/auth gateway。 |
| `packages/hashline` | 基于内容 hash/anchors 的 edit format，减少 string-not-found 和 stale edit。 |
| `crates/pi-ast` | AST rewrite 和 structural search，`apply_edits` 拒绝 overlapping replacement。 |

## 关键数据流

1. 模型通过工具发现/主动工具集调用 `read/search/edit/bash/lsp/debug/...`。
2. 读写工具把本地文件、URL、PR/issue/internal scheme 统一成“路径可读”的接口，降低工具参数学习成本。
3. 编辑先通过 hashline 或 AST edit 定位；stale anchor/overlap 会被拒绝或要求 resolve，减少误写。

## 设计决策

- 把 IDE 能力下沉为一等工具：LSP rename/diagnostics、DAP debug、AST edit，而不是只靠 shell。
- hashline 是针对模型编辑失败模式的格式工程，和传统 unified diff/str_replace 路线不同。
- “GitHub is filesystem”把 PR/issue/diff 抽成 read/search 路径，显著减少工具面碎片。

## 对比定位

与 Pi 相比，oh-my-pi 是 batteries-included fork；与 Codex 相比，它更重工具和本地 IDE 集成，但治理边界更复杂；与 [[code-semantic-search-rag-map]] 中项目相比，它不是单独 Code RAG，而是把 search/read/LSP/AST/PR 都塞进执行面。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
