---
title: AgentScope Runtime 架构与设计思路分析
tags: [architecture, agent-runtime, agent-as-a-service, sandbox, ai-agent]
date: 2026-06-12
sources: [agentscope-runtime-architecture-analysis.md]
related: [[[agent-runtime-sandbox-selection-map]], [[src-agentscope-architecture]], [[declarative-agent-management]], [[cloud-native-security]], [[mcp]], [[agent-sandbox]], [[agentgateway]]]
---

# AgentScope Runtime 架构与设计思路分析

`agentscope-ai/agentscope-runtime` 是 AgentScope 生态把 framework app 包装成生产 API/runtime 的过渡层：`AgentApp(FastAPI)` 暴露 streaming endpoint，`Runner` 统一 agent handler 生命周期，deployers 把本地、Kubernetes、Knative/FC 等环境抽象成可部署服务，sandbox manager 给工具调用提供隔离执行入口。README 明确提示这些能力已经并入 AgentScope 2.0，仓库更像生产 runtime 设计参考。

## 核心架构图

```text
┌──────────────────── AgentScope app / other framework app ────────────────────┐
│ user handler: init / query / shutdown, stream messages, tools, session state   │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ AgentApp(FastAPI)                                                             │
│ routes / OpenAPI / SSE · A2A / AG-UI / Response API adapters · interrupt svc   │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ Runner                                                                        │
│ framework adapters · stream_query · tracing · DeployManager integration        │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ sandbox manager / clients     │  │ deployers                                  │
│ docker/gVisor/K8s/Knative/FC  │  │ local · Kubernetes · Kruise · Knative · FC  │
└───────────────────────────────┘  └────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `src/agentscope_runtime/engine/app/agent_app.py` | `AgentApp` 直接继承 `FastAPI`，负责 endpoint、OpenAPI schema 注入、protocol adapters、分布式 interrupt service 和中间件。 |
| `src/agentscope_runtime/engine/runner.py` | 核心执行器，管理 `query_handler/init_handler/shutdown_handler`，把 handler 输出统一成 streaming event。 |
| `engine/deployers/**` | 把 runtime 投递到 local、Kubernetes、Knative、Kruise、FC、ModelStudio 等环境。 |
| `sandbox/**` + `common/container_clients/**` | sandbox registry、manager server、workspace/storage mixin，以及 docker/gVisor/K8s/Knative/FC client。 |

## 关键数据流

1. 请求进入 `/process` 或 A2A/Response API adapter，`AgentApp` 反序列化成 `AgentRequest`，交给 `Runner.stream_query`。
2. `Runner` 检查 framework type 和 health，再调用用户注册的 query handler；同步、异步、generator、async generator 输出都被包成统一 stream。
3. 工具调用通过 adapter 转成 runtime tool；需要隔离时走 sandbox client/manager，manager 再落到 Docker、gVisor、K8s、serverless 容器。

## 设计决策

- 把 Agent app 做成 FastAPI 子类，而不是另起 RPC 框架，换来 OpenAPI、中间件、生命周期和生态兼容。
- protocol adapter 是外壳，Runner 是内核；A2A/AG-UI/Response API 可以并存。
- sandbox 和 deployer 分离：前者处理工具调用隔离，后者处理整个 agent service 如何运行。

## 对比定位

和 [[src-agentscope-architecture]] 相比，它不是 agent 编程框架，而是服务化/部署/隔离壳；和 [[agent-sandbox]] 相比，它不把 workload 建模成 K8s CRD，而是在 Python runtime 内部暴露 Agent-as-a-Service；和 Agent Substrate 相比，它偏应用 runtime，不做高密度 actor/worker multiplexing。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
