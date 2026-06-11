---
title: Agent Runtime / Sandbox 细分选型地图
tags: [agent-runtime, sandbox, project-map, selection, cloud-native]
date: 2026-06-11
sources: [src-agent-sandbox-architecture, src-agentcube-architecture, src-openshell-architecture, src-nemoclaw-architecture, src-hiclaw-architecture, src-agentscope-architecture, src-agentgateway-architecture]
related: [[agent-runtime-sandbox-project-map]], [[agent-sandbox]], [[agentcube]], [[HiClaw]], [[agentgateway]], [[agent-credential-isolation]]
---

# Agent Runtime / Sandbox 细分选型地图

已有 [[agent-runtime-sandbox-project-map]] 做了完整分层。这页面向选型：你需要的是 sandbox primitive、session API、安全 runtime、多 Agent 平台，还是 AI gateway。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 当前定位 |
|------|------|-----------|-------|--------|----------|
| [[agent-sandbox]] | https://github.com/kubernetes-sigs/agent-sandbox | 2026-06-10 | 2.8k | Go | K8s-native isolated stateful singleton workload |
| [[agentcube]] | https://github.com/volcano-sh/agentcube | 2026-06-08 | 147 | Go | Sandbox session orchestration |
| [[src-openshell-architecture|OpenShell]] | https://github.com/NVIDIA/OpenShell | 2026-06-11 | 7k | Rust | Safe private runtime for autonomous agents |
| [[src-nemoclaw-architecture|NemoClaw]] | https://github.com/NVIDIA/NemoClaw | 2026-06-11 | 21k | TypeScript | OpenShell 内运行 Hermes/OpenClaw |
| [[HiClaw]] | https://github.com/agentscope-ai/HiClaw | 2026-06-10 | 4.8k | Go | Matrix + K8s 的 collaborative multi-agent OS |
| [[src-agentscope-architecture|AgentScope]] | https://github.com/agentscope-ai/agentscope | 2026-06-09 | 26k | Python | 可观测、可理解、可信任的 Agent 构建框架 |
| [[agentgateway]] | https://github.com/agentgateway/agentgateway | 2026-06-10 | 3.2k | Rust | AI agents / MCP servers 的 agentic proxy |

## 分层选择

| 你要解决的问题 | 首选 | 不适合 |
|----------------|------|--------|
| K8s 上安全运行一个有状态 Agent 容器 | [[agent-sandbox]] | 需要完整产品 API、IM 协作或工具治理 |
| 把 sandbox 包成 session/invocation API | [[agentcube]] | 不使用 Kubernetes 或不想引入 Redis/session registry |
| 本地/私有强安全 Agent runtime | [[src-openshell-architecture|OpenShell]] | 只需要普通容器隔离 |
| 给 OpenShell 配套 agent onboarding | [[src-nemoclaw-architecture|NemoClaw]] | 只想写一个 Agent 应用框架 |
| 多 Agent 协作 + 人在回路 | [[HiClaw]] | 不想引入 Matrix / K8s operator |
| Python Agent 应用服务化 | [[src-agentscope-architecture|AgentScope]] | 需要强 sandbox 原语 |
| LLM/MCP/A2A 流量治理 | [[agentgateway]] | 需要运行 Agent 进程本身 |

## 架构边界

```
Agent framework / app
        ↓
session orchestration
        ↓
sandbox lifecycle primitive
        ↓
runtime enforcement
        ↓
network / credential / tool gateway
```

[[agent-sandbox]] 处在 sandbox lifecycle primitive；[[src-openshell-architecture|OpenShell]] 处在 runtime enforcement；[[agentgateway]] 处在 network/tool gateway；[[HiClaw]] 和 [[agentcube]] 是上层产品化编排；[[src-agentscope-architecture|AgentScope]] 是应用框架层。

## 关键对比

| 维度 | [[agent-sandbox]] | [[src-openshell-architecture|OpenShell]] | [[agentcube]] | [[HiClaw]] | [[agentgateway]] |
|------|------------------|----------------|---------------|------------|----------------|
| 控制面 | K8s controller | Gateway desired state | Router + WorkloadManager | K8s operator + Matrix/Higress | Gateway API/xDS |
| 数据面 | Pod/PVC/Service | supervisor + policy proxy | Sandbox pod + PicoD | Worker containers + Matrix rooms | Rust L7 proxy |
| 状态 | K8s API + PVC | object store + sandbox state | Redis/ValKey session registry | etcd/kine + Matrix + MinIO | route/backend/policy stores |
| 凭据 | 交给上层 | gateway 托管 provider key | Router JWT / workload auth | Higress 托管真实凭据 | backend secret / policy |
| 用户入口 | CRD / SDK | CLI / SDK | HTTP / Python SDK / Dify | Matrix / CRD / CLI | CRD / Gateway / UI |

## 采用建议

- 做“Agent 运行在 K8s 里的基础设施”：先看 [[agent-sandbox]]，上层再接 [[agentcube]]。
- 做“安全私有 Agent 运行时”：先看 [[src-openshell-architecture|OpenShell]]，再看 [[src-nemoclaw-architecture|NemoClaw]] 如何编排。
- 做“团队协作 Agent 平台”：[[HiClaw]] 的 Matrix-first 协作面比普通 Agent framework 更贴近人类介入。
- 做“工具/模型访问治理”：[[agentgateway]] 应作为 sandbox 外侧的流量控制点。

