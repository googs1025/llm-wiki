---
title: Claude Code 插件机制
tags: [entity, claude-code, plugin-system, stub]
date: 2026-05-14
sources: [powermem-architecture-analysis.md]
related: [claude-code, powermem, claude-mem, mcp]
---

# Claude Code 插件机制

[[claude-code]] 的官方插件机制 —— 通过 `--plugin-dir` 加载，结构为 `.claude-plugin/plugin.json` + `hooks/` + `skills/` + `.mcp.json`。**HTTP hook + MCP server + Skill** 三种扩展通道。

> [!todo] Stub 占位
> [[powermem]] 的 [Claude Code 插件](https://github.com/oceanbase/powermem/tree/main/apps/claude-code-plugin) 是参考实现，详见 [[src-powermem-architecture]] 的"Apps · Claude Code 插件"模块和"关键组件深入解读"小节。
>
> 待补充：
> - 4 种 hook event 完整规范（UserPromptSubmit / Stop / PreCompact / PostToolUse）
> - `additionalContext` 注入机制详解
> - `.mcp.json` 双模式切换（HTTP / MCP）
> - 与 [[claude-mem]] 的对照（claude-mem 是同类项目，全包式插件）
> - Skill 格式（SKILL.md 头部约定）

## 速读：powermem 插件做了什么

- Go 原生二进制 `powermem-hook`（跨平台编译，无 Python 依赖）+ bash/PowerShell wrapper
- `UserPromptSubmit` hook 自动检索注入到对话上下文（`POWERMEM_PROMPT_SEARCH=0` 关闭）
- 默认 HTTP 模式 → `POST /api/v1/memories`；可选 MCP 模式 → 通过 [[mcp]] 工具
- 提供 `/memory-powermem:remember` + `/memory-powermem:recall` 两个 skill

## 相关页面

- 平台：[[claude-code]]
- 参考实现：[[powermem]]、[[src-powermem-architecture]]
- 同类项目：[[claude-mem]]（独立 npm 包，与 powermem 插件功能重叠但定位不同 —— claude-mem 是独立 agent 记忆，powermem 插件只是接入层）
- 工具协议：[[mcp]]
