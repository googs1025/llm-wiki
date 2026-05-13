---
title: 声明式 Agent 管理
tags: [k8s-operator, multi-agent, agent-platform, design-pattern]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md]
related: [[HiClaw]], [[k8s-operator]], [[agent-credential-isolation]], [[ai-agent-plugin-patterns]]
---

# 声明式 Agent 管理

> Stub — 待充实

把 [[k8s-operator|Kubernetes Operator 模式]]套到 AI Agent 运维上的设计哲学：**Agent 是资源（CR），不是对象（class）**。

由 [[HiClaw]] 在 2026 年开源时首次清晰展现：

- Agent 用 CRD 声明（YAML），不是用 Python class 编排
- controller 持续 reconcile，让 actual state（容器、IM 房间、网关 consumer）向 desired state（CR）收敛
- 免费获得 K8s 的 self-healing / 多副本 / RBAC / Helm 上线下线 / kubectl 操作面
- 与 [[langgraph]] / [[autogen]] / [[crewai]] 这类"在你自己进程里跑 Python"的框架根本不同——后者要做企业级运维需重头补

## TODO

- [ ] 补充：除 HiClaw 外其它声明式 Agent 系统（如 Agentic Framework on K8s 各家方案）
- [ ] 解释：与 Kubernetes Resource Model 的精确对应（Worker = Pod、Team = Deployment、Manager = Daemon？）
- [ ] 写"反模式"：什么时候不该这么做（轻量级、单进程编排的场景）
- [ ] 加链接到 [[ai-agent-plugin-patterns]] 的对应原则
