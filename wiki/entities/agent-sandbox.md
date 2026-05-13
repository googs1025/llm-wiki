---
title: agent-sandbox
tags: [k8s-operator, agent-runtime, ai-infra, sig-apps]
date: 2026-05-13
sources: [agent-sandbox-architecture-analysis.md]
related: [[HiClaw]], [[k8s-operator]], [[gvisor]], [[kata-containers]], [[declarative-agent-management]]
---

# agent-sandbox

`kubernetes-sigs/agent-sandbox` 是 **K8s SIG Apps 官方孵化**的 Sandbox CRD + controller。把 AI Agent runtime 那种"长寿命、有状态、单实例、可暂停、有稳定身份"的容器形态建模成第一类 K8s 资源——比 Deployment（无状态副本）和 StatefulSet（编号 Pod）都更精准。**隔离机制完全委托给标准 K8s 原语**（[[gvisor]] / [[kata-containers]] / [[network-policy]]），controller 只做生命周期编排。

详细架构见 [[src-agent-sandbox-architecture]]。

## 关键事实

- 仓库：[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox)
- 版本：v0.4.5+11（HEAD `e1d8898`，2026-04-23 左右）
- 主要语言：Go 1.26.2，模块 `sigs.k8s.io/agent-sandbox`
- 4 个 CRD：核心 `Sandbox` (agents.x-k8s.io) + 扩展 `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` (extensions.agents.x-k8s.io)
- 治理：K8s SIG Apps 孵化项目，遵循 [Kubernetes Resource Model](https://kubernetes.io/docs/concepts/overview/working-with-objects/) 范式
- SDK：Go + Python（codegen 生成） + 标准 K8s clientset/informer/lister
- 17 个 example：hello-world / kata-gke / openclaw / hermes / langchain / jupyter / vscode / chrome / HPA / Kueue / Cilium policy ...

## 与 [[HiClaw]] 的关系

互补不竞争——agent-sandbox 是**基础设施层**（提供"安全运行 1 个有状态 Agent 容器"原语），HiClaw 是**应用层**（提供"管 N 个 Agent 协作 + IM 平面 + 凭据网关"）。理论上 HiClaw 的 Worker runtime 完全可以跑在 agent-sandbox 之上。

## TODO

- [ ] 跟 [[HiClaw]] 做完整"基础设施 vs 应用层" 对比表（含部署、隔离、协作模型）
- [ ] 写一份"从 0 到一个 Sandbox 跑起来"的 GKE Kata walkthrough
- [ ] 补充：v0.5 / v1beta1 升级路线（roadmap.md 显示有计划）
- [ ] examples 子目录的导读（17 个，需要按"入门 / 隔离 / 集成"分类）
