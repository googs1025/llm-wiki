---
title: substrate
tags: [entity, agent-runtime, sandbox, kubernetes, ai-infra]
date: 2026-06-13
sources: [substrate-architecture-analysis.md]
related: [[agent-runtime-substrate]], [[agent-runtime-sandbox-selection-map]], [[agent-sandbox]], [[agentcube]], [[kubernetes]], [[cloud-native-security]]
---

# substrate

Agent Substrate 是运行在 [[kubernetes]] 之上的高密度 agent-like workload substrate。它把 Kubernetes 当作低频容量和模板控制面，把 Actor 的高频 resume/suspend、worker 分配、状态锁和路由唤醒放到 Redis/ValKey、ateapi、atelet、ateom-gVisor 和 atenet router 里完成。详见 [[src-substrate-architecture]]。

## 架构边界

Substrate 不是普通的 Agent framework，也不是只创建一个 Pod 的 sandbox CRD。它的核心目标是让大量 idle actor multiplex 到较少 warm worker 上，通过 golden snapshot、runtime checkpoint/restore、actor DNS 和 Envoy ext_proc 唤醒降低激活延迟。

它和 [[agent-sandbox]] / [[agentcube]] 的区别在层级：[[agent-sandbox]] 提供有状态 Sandbox 原语，[[agentcube]] 做会话路由和 warm pool，Substrate 更底层，直接把 worker pool、actor template、snapshot 和路由恢复做成 substrate。

## 关键抽象

- `WorkerPool`：声明 worker 容量和运行模板，由 controller 物化为 privileged ateom pods。
- `ActorTemplate`：生成 golden actor，再 checkpoint 成 golden snapshot，供后续 actor 快速恢复。
- `Actor`：高频运行状态不进 K8s API，而是存 Redis/ValKey。
- `atelet` / `ateom-gvisor`：节点侧 supervisor 和 gVisor worker，负责 runsc create/start/checkpoint/restore。
- `atenet`：通过 actor hostname 触发 `ResumeActor`，再把请求转发到已分配 worker。

## 选型判断

适合研究或构建高密度、低空闲成本、可暂停恢复的 agent runtime。若只是给单个 agent 提供隔离，优先看 [[agent-sandbox]] 或 [[OpenShell]]；若需要团队级会话编排和 warm pool，优先看 [[agentcube]]；若要把 sandbox 出口流量纳入治理，再叠加 [[agentgateway]] / [[ai-gateway]]。

