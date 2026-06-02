---
title: AgentCube
tags: [ai-agent, code-interpreter, kubernetes, volcano, agent-sandbox, serverless]
date: 2026-06-02
sources: [agentcube-architecture-analysis.md]
related: ["[[agent-sandbox]]", "[[kubernetes]]", "[[declarative-agent-management]]", "[[agent-credential-isolation]]", "[[src-agentcube-architecture]]"]
---

# AgentCube

AgentCube 是 Volcano 社区面向 AI Agent / Code Interpreter 的 Kubernetes 原生会话编排层。它不是替代 [[agent-sandbox]]，而是在 agent-sandbox 的 `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` 之上，补上应用级会话、HTTP 入口、代码执行 API、SDK 入口和生命周期回收。

详细架构见 [[src-agentcube-architecture]]。

## 关键事实

- 仓库：[volcano-sh/agentcube](https://github.com/volcano-sh/agentcube)
- 版本：HEAD `208da32`（2026-06-01）
- 阶段：Proposal / Early Design，README 明确标注仍在早期设计期
- 主要语言：Go，模块 `github.com/volcano-sh/agentcube`
- 核心依赖：`sigs.k8s.io/agent-sandbox v0.1.1`
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

## TODO

- [ ] 等 AgentCube 发布 tagged release 后补充版本差异与 CRD 稳定性。
- [ ] 跟 [[agent-sandbox]] v0.4.x 对比 API 兼容性，确认当前 `v0.1.1` 依赖升级成本。
- [ ] 做一份 CodeInterpreter warm pool 请求时序图，从 Router 到 SandboxClaim 再到 PicoD。
