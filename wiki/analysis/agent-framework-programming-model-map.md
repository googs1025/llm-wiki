---
title: Agent Framework 编程模型对比地图
tags: [ai-agent, agent-framework, programming-model, selection]
date: 2026-06-11
sources: [src-ai-agent-frameworks-stars, src-agentscope-architecture]
related: [[ai-agent-frameworks-map]], [[agent-runtime-sandbox-project-map]], [[mcp]], [[agent-memory]], [[ai-agent-plugin-patterns]]
---

# Agent Framework 编程模型对比地图

这页比较“写 Agent 应用”的框架，而不是直接可用的 coding agent 产品。核心问题是：你希望用 graph、workflow、event loop、role-play multi-agent，还是 Go 代码优先框架。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 定位 |
|------|------|-----------|-------|--------|------|
| LangGraph | https://github.com/langchain-ai/langgraph | 2026-06-11 | 34k | Python | resilient agents graph runtime |
| LangChain | https://github.com/langchain-ai/langchain | 2026-06-11 | 138k | Python | agent engineering platform |
| Dify | https://github.com/langgenius/dify | 2026-06-11 | 144k | TypeScript | production-ready agentic workflow platform |
| [[src-agentscope-architecture|AgentScope]] | https://github.com/agentscope-ai/agentscope | 2026-06-09 | 26k | Python | see/understand/trust agents |
| Eino | https://github.com/cloudwego/eino | 2026-06-11 | 11k | Go | Go LLM/AI app framework |
| ADK Go | https://github.com/google/adk-go | 2026-06-10 | 8k | Go | code-first Go toolkit for AI agents |
| AutoGen | https://github.com/microsoft/autogen | 2026-04-15 | 58k | Python | programming framework for agentic AI |
| CrewAI | https://github.com/crewAIInc/crewAI | 2026-06-11 | 53k | Python | role-playing autonomous agent orchestration |

## 选型

| 需求 | 推荐 |
|------|------|
| 状态图、可恢复 agent workflow | LangGraph |
| Python LLM app 生态和组件库 | LangChain |
| 可视化/产品化 workflow 平台 | Dify |
| 事件流、tool/MCP/skill、服务化 Agent app | [[src-agentscope-architecture|AgentScope]] |
| Go 代码优先 LLM app | Eino / ADK Go |
| 多 Agent 对话/协作研究 | AutoGen / CrewAI |

## 编程模型差异

| 维度 | LangGraph | Dify | [[src-agentscope-architecture|AgentScope]] | Eino / ADK Go | AutoGen / CrewAI |
|------|-----------|------|----------------|----------------|------------------|
| 主抽象 | graph/state | workflow app | AgentEvent / Msg / toolkit / workspace | typed Go components | agents / roles / conversations |
| 人在回路 | graph interrupt/checkpoint | workflow 节点/UI | continuation event / confirm event | 代码自建 | conversation callback |
| Tool 接入 | LangChain tools / MCP bridge | platform tools | Toolkit / MCP / Skill | Go tool interfaces | function/tool calls |
| 服务化 | LangGraph platform / app | 内置平台 | FastAPI service | 自建服务 | 自建或框架服务 |
| 最适合 | 可恢复复杂流程 | 低代码产品平台 | 可观测 Agent 应用 | Go infra 团队 | 多 Agent 角色编排 |

## 和 runtime/sandbox 的边界

这些框架通常不应该自己承担强 sandbox。更稳的组合是：

```
Agent framework
        ↓
tool permission / event stream
        ↓
MCP / gateway
        ↓
runtime sandbox
```

例如 [[src-agentscope-architecture|AgentScope]] 可以编排 tool 和 workspace，但如果要运行不可信代码，仍应接 [[agent-runtime-sandbox-project-map]] 中的 sandbox 或外部 workspace backend。

## 避坑条件

- “多 Agent”不是自动带来更好结果；先确认任务是否真的需要角色分工。
- 图式框架适合可恢复流程，但简单 coding task 可能过重。
- 低代码平台适合快速产品化，但深度 runtime/sandbox 改造成本高。
- Go 框架适合基础设施团队，但 Python 生态的模型/provider/tool 覆盖通常更快。

