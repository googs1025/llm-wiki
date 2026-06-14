---
title: kube-agentic-networking 架构与设计思路分析
tags: [architecture, kubernetes, agent, networking]
date: 2026-06-14
sources: [kube-agentic-networking-architecture-analysis.md]
related: ["[[kube-agentic-networking]]", "[[kubernetes]]", "[[agentgateway]]", "[[agent-sandbox]]", "[[cloud-native-security]]"]
---

# kube-agentic-networking 架构与设计思路分析

> 原文：`raw/kube-agentic-networking-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kube-agentic-networking · 优先级 P1

## 一句话定位

kube-agentic-networking 为 Kubernetes 中 agents/tools 提供 agentic networking policies and governance，面向 AI Agent 出口、工具调用和网络权限边界。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ kube-agentic-networking    │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CRD/polici │ │ Controller: po │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Gateway/ne │ │ Audit/governan │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CRD/policies | agent/tool/network intent |
| Controller | policy reconciliation |
| Gateway/network integration | Gateway/network integration |
| Audit/governance signals | Audit/governance signals |

## 关键数据流

```
平台声明 agent/tool 网络策略
        │
        ▼
controller 解析目标和权限
        │
        ▼
下发到 gateway/network policy 层
        │
        ▼
Agent 调用工具时被策略约束
        │
        ▼
审计和状态回写
```

## 设计决策与哲学

- **补齐 `Agent networking governance` 维度**：kube-agentic-networking 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它和 agentgateway/agent-sandbox 互补：sandbox 管运行时隔离，gateway/networking 管出入口策略。
- **选型价值**：它应和 [[agentgateway]], [[agent-sandbox]], [[cloud-native-security]] 一起看，而不是孤立评估。

## 相关页面

- [[kube-agentic-networking]]
- [[kubernetes]]
- [[agentgateway]]
- [[agent-sandbox]]
- [[cloud-native-security]]
