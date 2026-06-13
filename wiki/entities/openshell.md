---
title: OpenShell
tags: [entity, sandbox, ai-agent, security, nvidia]
date: 2026-06-13
sources: [openshell-architecture-analysis.md]
related: [[nemoclaw]], [[agent-sandbox]], [[agentgateway]], [[cloud-native-security]], [[agent-credential-isolation]], [[mcp]]
---

# OpenShell

OpenShell 是 NVIDIA 面向 autonomous AI Agent 的安全私有运行时。它把 agent 放进可审计、可连接、可恢复的 sandbox 中运行，并把 Gateway 控制面、sandbox supervisor enforcement、OPA/Z3 policy pipeline、provider credential 管理和 `inference.local` 推理路由拆成清晰边界。详见 [[src-openshell-architecture]]。

## 架构边界

OpenShell 不是 Agent framework。它不负责定义 ReAct loop 或多 Agent 工作流，而是负责让这些 agent 在受控环境中执行：Gateway owns desired state，Supervisor owns runtime enforcement。

## 核心组件

- Gateway control plane：管理 sandbox、provider、policy、settings、inference、session 和 compute orchestration。
- Runtime driver：把 Docker、Podman、Kubernetes、VM/libkrun 等后端收敛成统一 compute driver。
- Sandbox supervisor：在 sandbox 内准备 filesystem、process limits、network namespace、TLS、proxy、SSH 和 agent child。
- Policy proxy：用 OPA 做 L4/L7 网络裁决，绑定进程身份并做 SSRF 防护。
- `inference.local`：由 sandbox proxy 拦截并路由到 provider，避免 agent 直接持有真实模型凭证。

## 选型判断

适合把本地或托管 coding agent 放到强安全边界里运行。和 [[agent-sandbox]] 相比，OpenShell 更偏完整安全 runtime；和 [[substrate]] 相比，它不追求大规模 actor snapshot multiplex；和 [[agentgateway]] 相比，它治理运行时与网络 enforcement，而不是集群入口网关。
