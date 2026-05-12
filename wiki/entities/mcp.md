---
title: Model Context Protocol (MCP)
tags: [protocol, ai-agent, claude, llm-infra]
date: 2026-05-12
sources: [src-claude-context-architecture, src-claude-mem-architecture]
related: [[claude-code]], [[claude-context]], [[claude-mem]]
---

# Model Context Protocol (MCP)

Anthropic 推出的 AI Agent **工具/资源/Skill 接入协议**，基于 JSON-RPC over stdio（或 SSE）。让任意 Agent 客户端（Claude Code / Cursor / Gemini CLI / Codex）通过统一协议加载第三方工具。

## 角色

| 端 | 谁 | 干啥 |
|----|----|------|
| Server | 插件 / 工具进程 | 暴露工具（`tools/list`、`tools/call`）和资源 |
| Client | AI Agent runtime | 启动 server 子进程，转发 LLM 的工具调用请求 |

## 在本知识库中的应用

- [[claude-context]] —— 通过 MCP 暴露 4 个代码检索工具（`index_codebase` / `search_code` / `clear_index` / `get_indexing_status`）
- [[claude-mem]] —— `server-beta` 模式下用 MCP 暴露记忆查询（替代 hook-only 模式）

## 协议通道纪律

> [!warning] stdout 只跑协议
> MCP 用 stdout 传 JSON-RPC，任何 `console.log` 都会污染协议导致客户端解析失败。
> 第一行代码就应该把 stdout 重定向到 stderr：
> ```ts
> console.log = (...args) => process.stderr.write('[LOG] ' + args.join(' ') + '\n');
> ```
> 这是 [[ai-agent-plugin-patterns]] 中"协议通道纪律"原则的典型案例。

## 配置示例（Claude Code）

```bash
claude mcp add <name> -e KEY=VALUE -- <command> <args>
```

启动后 Claude Code 会把 server 注册的工具加入自己的 tool list，LLM 可像调用内置工具一样调用。

## 参考

- [[src-claude-context-architecture]]
- [[src-claude-mem-architecture]]
