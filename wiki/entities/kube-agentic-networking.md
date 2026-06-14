---
title: kube-agentic-networking
tags: [entity, kubernetes, agent, networking]
date: 2026-06-14
sources: [kube-agentic-networking-architecture-analysis.md]
related: ["[[kube-agentic-networking]]", "[[kubernetes]]", "[[agentgateway]]", "[[agent-sandbox]]", "[[cloud-native-security]]"]
---

# kube-agentic-networking

kube-agentic-networking 为 Kubernetes 中 agents/tools 提供 agentic networking policies and governance，面向 AI Agent 出口、工具调用和网络权限边界。 详见 [[src-kube-agentic-networking-architecture]]。

## 架构边界

它和 agentgateway/agent-sandbox 互补：sandbox 管运行时隔离，gateway/networking 管出入口策略。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Agent networking governance` 能力 | 适合，kube-agentic-networking 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[agentgateway]], [[agent-sandbox]], [[cloud-native-security]] 组合。 |

## 核心组件

- CRD/policies: agent/tool/network intent
- Controller: policy reconciliation
- Gateway/network integration
- Audit/governance signals

## 选型提示

把 kube-agentic-networking 放在 `Agent networking governance` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
