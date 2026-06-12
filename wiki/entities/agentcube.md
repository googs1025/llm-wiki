---
title: AgentCube
tags: [ai-agent, code-interpreter, kubernetes, volcano, agent-sandbox, serverless]
date: 2026-06-12
sources: [agentcube-architecture-analysis.md]
related: ["[[agent-sandbox]]", "[[kubernetes]]", "[[declarative-agent-management]]", "[[agent-credential-isolation]]", "[[src-agentcube-architecture]]"]
---

# AgentCube

AgentCube 是 Volcano 社区面向 AI Agent / Code Interpreter 的 Kubernetes 原生会话编排层。它不是替代 [[agent-sandbox]]，而是在 agent-sandbox 的 `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` 之上，补上应用级会话、HTTP 入口、代码执行 API、SDK 入口和生命周期回收。

详细架构见 [[src-agentcube-architecture]]。

## 关键事实

- 仓库：[volcano-sh/agentcube](https://github.com/volcano-sh/agentcube)
- 当前核验：GitHub API 显示 main 最近 push `2026-06-12`，已有 tag `v0.1.0`
- 本 wiki 架构分析版本：HEAD `208da32`（2026-06-01）
- 阶段：已从 Proposal 进入早期 release，但 API 仍需按上游 agent-sandbox 演进持续核验
- 主要语言：Go 1.24.4，模块 `github.com/volcano-sh/agentcube`
- 核心依赖：`sigs.k8s.io/agent-sandbox v0.1.1`（当前 main 的 `go.mod` 仍如此）
- 2 个 AgentCube CRD：`AgentRuntime` 与 `CodeInterpreter`
- 主要组件：Router、WorkloadManager、PicoD、Redis / ValKey session registry

## 架构定位

AgentCube 把 agent-sandbox 的底层运行时原语包装成更贴近 AI 应用的会话模型：

- `AgentRuntime` 面向长期运行的 Agent 服务，声明 `targetPort`、PodTemplate 和 session timeout。
- `CodeInterpreter` 面向代码执行工作负载，声明执行镜像、端口、session timeout、最大会话时长、warm pool 规模和鉴权模式。
- Router 是数据平面，根据 `x-agentcube-session-id` 查询 Redis / ValKey，把请求反向代理到已存在的 Sandbox，必要时调用 WorkloadManager 创建新 session。
- WorkloadManager 是控制平面，负责创建 `Sandbox` 或 `SandboxClaim`，等待 Ready、做 entrypoint TCP probe、写入 session 映射并执行 GC。
- PicoD 是轻量 HTTP daemon，提供 `/api/execute` 与 `/api/files`，用 Router 签发的 JWT 做访问控制，替代传统 SSH 进入容器。

## 与 [[agent-sandbox]] 的结合

AgentCube 复用了 agent-sandbox 的隔离、Pod 生命周期和 WarmPool 能力，但把它们隐藏在更高层 API 后面：

- 冷启动路径：`AgentRuntime` / `CodeInterpreter` -> WorkloadManager -> `Sandbox` -> Pod。
- 预热路径：`CodeInterpreter.warmPoolSize` -> `SandboxTemplate` + `SandboxWarmPool` -> 首次请求创建 `SandboxClaim` -> 领取预热 Sandbox。
- 会话路径：Router 从 session registry 解析 `sessionId -> endpoint`，后续请求不再走 K8s reconcile，而是直接代理到 PicoD 或 Agent 服务。

这个分层让 agent-sandbox 继续专注"安全、有状态、可回收的单实例容器"，AgentCube 则负责"用户请求如何变成一个可复用的 AI / Code session"。

## agent-sandbox API 兼容性

AgentCube 当前已发布 `v0.1.0`，但仍依赖 `sigs.k8s.io/agent-sandbox v0.1.1`。这意味着它和当前 agent-sandbox `v0.4.6` / `v0.5.0rc1` 之间可能存在 API 追赶成本：

- `SandboxTemplate` / `SandboxWarmPool` 字段可能需要适配新版本 rolling update / backend 解耦；
- claim / warm pool 的 status 和 owner reference 语义可能变化；
- router/session registry 依赖 Sandbox Ready、endpoint、port 等状态字段，升级时要重点回归；
- AgentCube 的 `CodeInterpreter.warmPoolSize` 是对 agent-sandbox WarmPool 的上层封装，上游 API 变动会直接影响这一功能。

选型上，AgentCube 当前适合作为“agent-sandbox 上层应用 API”的设计参考；生产采用前应先验证它是否已跟上目标 agent-sandbox 版本。

## CodeInterpreter warm pool 请求时序

```
Client request
  │  POST /sessions or /execute
  ▼
AgentCube Router
  │  check x-agentcube-session-id
  │  miss → ask WorkloadManager
  ▼
WorkloadManager
  │  CodeInterpreter.warmPoolSize > 0 ?
  │
  ├─ warm path:
  │    create SandboxClaim
  │      │
  │      ▼
  │    agent-sandbox controller assigns prewarmed Sandbox
  │
  └─ cold path:
       create Sandbox directly from template
         │
         ▼
  wait Sandbox Ready + entrypoint TCP probe
         │
         ▼
  write sessionId → endpoint into Redis / ValKey
         │
         ▼
Router reverse proxy → PicoD `/api/execute` / `/api/files`
```

这条路径把高频请求和低频 K8s reconcile 分开：首次 miss 需要控制面介入，后续同一 session 直接由 Router 查 registry 并代理到 PicoD。
