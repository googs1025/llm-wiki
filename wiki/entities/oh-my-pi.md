---
title: oh-my-pi
tags: [entity, coding-agent, tool-harness, lsp, rust]
date: 2026-06-13
sources: [oh-my-pi-architecture-analysis.md]
related: [[pi]], [[coding-agent-selection-map]], [[code-semantic-search-rag-map]], [[mcp]], [[claude-code]], [[agent-memory]]
---

# oh-my-pi

oh-my-pi 是 Pi fork，但定位已经从 harness monorepo 变成强工具 coding-agent 产品。它强调 IDE wired in、32 tools、LSP/DAP、hashline edit、persistent eval、subagents、browser/web_search、memory、ACP/editor drive 和 conflict resolution。详见 [[src-oh-my-pi-architecture]]。

## 架构边界

oh-my-pi 不是单独 Code RAG，也不是只接模型的轻量 CLI。它把 search/read/edit/bash/eval/LSP/debug/browser/task/memory/web_search 等能力一起放进执行面，并用 Rust crate 支撑 AST、shell、isolated copy 和结构化编辑。

## 关键设计

- hashline 通过内容 hash/anchors 定位编辑，减少 string-not-found 和 stale edit。
- LSP / DAP 是一等工具，而不是靠 shell 间接调用。
- `GitHub is filesystem` 把 PR、issue、diff 抽成可 read/search 路径。
- Rust native crates 负责 AST rewrite、structural search、shell 和隔离 copy。

## 选型判断

需要“工具全、IDE 深、本地执行面强”的 coding agent 可看 oh-my-pi。需要更克制的 provider-neutral harness 看 [[pi]]；需要成熟安全沙箱和审批流看 [[codex]]；需要代码图谱辅助理解看 [[code-review-graph]] / [[gitnexus]]。

