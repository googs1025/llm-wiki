---
title: Agent Skills / Plugin System 对比地图
tags: [agent-skills, plugin-system, ai-agent, selection]
date: 2026-06-11
sources: [src-ai-agent-frameworks-stars]
related: [[claude-code-plugin]], [[ai-agent-plugin-patterns]], [[claude-code]], [[mcp]], [[ai-agent-frameworks-map]]
---

# Agent Skills / Plugin System 对比地图

Skills 和 plugins 在 Agent 生态里解决不同问题：plugin 更像宿主扩展点，skill 更像可迁移能力包，MCP tool 更像可调用外部能力。本页按工程边界对比。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 定位 |
|------|------|-----------|-------|--------|------|
| Anthropic Skills | https://github.com/anthropics/skills | 2026-06-09 | 149k | Python | Agent Skills 官方公共仓库 |
| agent-skills | https://github.com/addyosmani/agent-skills | 2026-06-11 | 52k | Shell | 面向 AI coding agents 的工程 skills |
| Matt Pocock skills | https://github.com/mattpocock/skills | 2026-06-10 | 124k | Shell | 个人工程 skills 集合 |
| awesome-agent-skills | https://github.com/libukai/awesome-agent-skills | 2026-03-26 | 4.6k | Python | skills 指南与精选资源 |

## 三种扩展形态

| 形态 | 例子 | 适合 | 不适合 |
|------|------|------|--------|
| Host plugin | [[claude-code-plugin]], OpenCode plugin | 生命周期 hook、UI/CLI 集成、宿主事件采集 | 跨宿主迁移 |
| Skill pack | Anthropic Skills, agent-skills, Codex skills | 操作流程、领域方法、脚本模板、可迁移经验 | 需要长期 daemon 或强权限 server |
| MCP tool | GitHub MCP, Playwright MCP | 标准 tool/resource 访问 | 复杂 workflow 说明和人工判断 |

## 选型判断

- 需要监听 `UserPromptSubmit` / `PostToolUse` / `Stop`：写 plugin。
- 需要教 Agent “怎么做代码审查/架构图/调研”：写 skill。
- 需要访问 GitHub、浏览器、K8s、数据库：写 MCP server 或接现成 server。
- 需要跨 Claude Code / Codex / OpenCode 复用：优先 skill + scripts，宿主适配层尽量薄。

## 架构差异

| 维度 | Plugin | Skill | MCP server |
|------|--------|-------|------------|
| 触发 | 宿主生命周期或命令 | LLM 根据描述选择 | LLM tool call |
| 状态 | 可持有宿主状态 | 文件/脚本/模板为主 | server 进程/外部系统状态 |
| 权限 | 常接近宿主权限 | 取决于脚本执行权限 | 取决于 server 凭据 |
| 可迁移 | 低到中 | 高 | 中 |
| 测试方式 | 宿主集成测试 | prompt + script 测试 | tool schema + server 测试 |

## 避坑条件

- skill 描述要短而可判别，否则 Agent 不会在正确时机调用。
- plugin 不要把重任务放在 hook 同步路径，参考 [[event-driven-memory-pipeline]] 的薄 hook 模式。
- MCP server 不要直接暴露全权限 token，优先通过 gateway/secret 管理。
- 同一能力不要同时做成 plugin、skill、MCP，除非边界清楚：plugin 负责捕获，skill 负责流程，MCP 负责外部动作。

