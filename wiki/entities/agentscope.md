---
title: AgentScope
tags: [entity, ai-agent, multi-agent, mcp, agent-framework]
date: 2026-06-13
sources: [agentscope-architecture-analysis.md]
related: [[agentscope-runtime]], [[agent-memory]], [[mcp]], [[ai-agent-plugin-patterns]], [[agent-framework-programming-model-map]], [[agent-sandbox]]
---

# AgentScope

AgentScope 2.0 是面向生产化多 Agent 应用的 Python 框架。它把 Agent 推理循环、模型 provider、工具 / [[mcp]] / skill、workspace、权限、人类确认、长任务 offload 和 FastAPI 服务层拆成可组合的异步组件。详见 [[src-agentscope-architecture]]。

## 架构边界

AgentScope 的核心协议是 `Agent.reply_stream()` 事件流，而不是只返回最终文本。模型输出、thinking、tool call、tool result、确认请求和外部执行结果都会进入 `AgentEvent` / `Msg`，这让 SDK、SSE、存储和前端可以共享同一套执行语义。

## 关键设计

- `Agent` 只依赖模型、toolkit、workspace、permission 和 middleware 抽象。
- ReAct loop 把“等待人类确认/外部执行”作为一等状态，可以暂停后恢复。
- Workspace 是工具资源和上下文外溢边界，可接 Local / Docker / E2B。
- 慢工具可以 offload 到后台，完成后再把结果注入后续 reasoning。
- 服务层用 FastAPI / SessionManager / storage 把 agent app 多租户化。

## 选型判断

需要写多 Agent 应用和服务化 agent app 时看 AgentScope。需要只做记忆组件看 [[ReMe]] 或 [[mem0]]；需要 Kubernetes 运行时部署看 [[agentscope-runtime]]；需要强 sandbox 隔离看 [[agent-sandbox]] / [[openshell]]。

