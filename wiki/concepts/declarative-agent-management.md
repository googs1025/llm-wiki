---
title: 声明式 Agent 管理
tags: [k8s-operator, multi-agent, agent-platform, design-pattern]
date: 2026-06-12
sources: [hiclaw-architecture-analysis.md, agent-sandbox-architecture-analysis.md, agentcube-architecture-analysis.md]
related: [[HiClaw]], [[agent-sandbox]], [[agentcube]], [[kagent]], [[kubernetes]], [[agent-credential-isolation]], [[ai-agent-plugin-patterns]]
---

# 声明式 Agent 管理

把 [[k8s-operator|Kubernetes Operator 模式]]套到 AI Agent 运维上的设计哲学：**Agent 是资源（CR），不是对象（class）**。

由 [[HiClaw]] 在 2026 年开源时首次清晰展现：

- Agent 用 CRD 声明（YAML），不是用 Python class 编排
- controller 持续 reconcile，让 actual state（容器、IM 房间、网关 consumer）向 desired state（CR）收敛
- 免费获得 K8s 的 self-healing / 多副本 / RBAC / Helm 上线下线 / kubectl 操作面
- 与 LangGraph / AutoGen / CrewAI 这类"在你自己进程里跑 Python"的框架根本不同——后者要做企业级运维需重头补

## Kubernetes Resource Model 对应

| K8s 模型 | Agent 管理类比 | 说明 |
|----------|----------------|------|
| `spec` | 期望 Agent 能力 | model、runtime、tools、skills、权限、协作关系 |
| `status` | 实际运行状态 | 容器状态、IM 身份、room id、gateway consumer、ready/error |
| `reconcile` | 自愈循环 | 外部资源被删或漂移后重新创建/修正 |
| `OwnerReference` | 生命周期归属 | Team 删除时清理成员或 session 资源 |
| finalizer | 有序清理 | 先删 gateway consumer、Matrix user、storage，再删 CR |

## 代表项目

| 项目 | 声明式对象 | 负责层级 |
|------|------------|----------|
| [[HiClaw]] | `Worker` / `Team` / `Human` / `Manager` | 多 Agent 协作、IM 平面、凭据网关、容器后端 |
| [[agent-sandbox]] | `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` | 有状态单实例 Agent runtime 原语 |
| [[agentcube]] | `AgentRuntime` / `CodeInterpreter` | 把 agent-sandbox 包成会话、Router、PicoD、WarmPool API |
| [[kagent]] | agentic DevOps/K8s 操作入口 | 更偏“用 Agent 操作 K8s”，不是底层 runtime CRD |

## 什么时候适合

- Agent 是长寿命、有状态、有身份的运行单元；
- 需要多人/多 Agent 协作和可审计生命周期；
- 需要 RBAC、namespace、多租户、Helm/GitOps 交付；
- 需要自愈、滚动升级、资源配额、网络/存储策略；
- 需要把 Agent 与 gateway、storage、IM、sandbox 等外部资源绑定。

## 什么时候是反模式

- 只是在一个 Python 进程里编排短生命周期 workflow；
- 目标是本地个人自动化，不需要多租户或运维控制面；
- Agent 没有持久身份、状态、权限或外部资源；
- 团队还没准备好 Kubernetes operator 的调试和发布复杂度。

## 与插件设计原则的关系

声明式 Agent 管理把 [[ai-agent-plugin-patterns]] 里的“接口化”和“宿主边界”推到集群级：Agent 能力不是散落在 prompt、脚本和环境变量里，而是被 CRD、policy、secret、gateway backend 和 controller 状态明确表达。
