---
title: Agent Runtime Substrate
tags: [concept, agent-runtime, substrate, sandbox, cloud-native]
date: 2026-06-15
sources: [substrate-architecture-analysis.md, agentscope-runtime-architecture-analysis.md, openkruise-agents-architecture-analysis.md]
related: [[agent-sandbox]], [[openkruise-agents]], [[agentcube]], [[agentscope-runtime]], [[agent-runtime-sandbox-selection-map]], [[declarative-agent-management]]
---

# Agent Runtime Substrate

Agent runtime substrate 指承载大量 agent-like workload 的底层运行基座：worker/actor 生命周期、状态保存、唤醒路由、沙箱隔离、快照恢复、并发密度和调度策略。

## 为什么单独成概念

传统 [[agent-sandbox]] 解决“一个 Agent 会话如何安全运行”，而 substrate 解决“一批 Agent 会话如何高密度、可恢复、可路由地运行”。[[openkruise-agents]] 则把这条线推向 K8s 平台化：用 SandboxSet/Claim 管 warm pool 和领取协议，用 E2B API 暴露产品入口，用 Envoy route registry 把请求导向具体 sandbox。[[src-substrate-architecture]] 把这个方向推进到 WorkerPool/ActorTemplate、Redis/ValKey actor state、Envoy 唤醒路由、gVisor snapshot；[[agentscope-runtime]] 则代表 framework app 到 Agent-as-a-Service 的服务化路线。

## 项目对比

| 项目 | 层级 | 重点 |
|---|---|---|
| [[agent-sandbox]] | sandbox primitive | 单会话隔离和有状态容器 |
| [[openkruise-agents]] | sandbox lifecycle platform | SandboxSet/Claim warm pool + E2B API + Envoy route + runtime/CSI/identity 扩展 |
| [[agentcube]] | session orchestration | Router + WorkloadManager + WarmPool |
| Substrate | runtime substrate | actor/worker multiplexing + snapshot/wakeup |
| [[agentscope-runtime]] | Agent-as-a-Service | Agent app 服务化和部署器 |

## 选型提示

如果问题是安全隔离，看 sandbox；如果问题是 Kubernetes 上的 E2B-like sandbox 平台，看 [[openkruise-agents]]；如果问题是高密度运行、唤醒和恢复，看 substrate；如果问题是把 framework app 暴露成服务，看 Agent-as-a-Service runtime。
