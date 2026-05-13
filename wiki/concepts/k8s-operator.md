---
title: K8s Operator 模式
tags: [kubernetes, design-pattern, controller-runtime]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md, agent-sandbox-architecture-analysis.md]
related: [[kubernetes]], [[HiClaw]], [[agent-sandbox]], [[declarative-agent-management]]
---

# K8s Operator 模式

> Stub — 待充实

Kubernetes Operator 模式：用 **CRD（CustomResourceDefinition）** 声明业务对象的期望状态，用 **controller**（持续 reconcile loop）让实际状态向期望状态收敛。最初由 CoreOS 在 2016 年命名（"用代码封装运维知识"），现已成为 K8s 生态扩展的标准范式。

## 核心要素

- **CRD**：定义业务对象的 Schema（Spec + Status）。
- **Reconciler**：`Reconcile(req) (Result, error)` 循环——读 CR、比对状态、修复差异、写回 Status、按需 requeue。
- **controller-runtime**：kubebuilder 提供的 Go 框架，封装了 informer / cache / workqueue / leader election。
- **OwnerReferences + Finalizers**：让 K8s 帮你做级联删除和清理拦截。

## 在 AI Agent 领域的应用

- [[HiClaw]] 把"4 个 CRD（Worker/Team/Human/Manager）+ 4 个 reconciler"套到多 Agent 协作运维（详见 [[declarative-agent-management]]）。
- [[agent-sandbox]] 把"4 个 CRD（Sandbox + Template/Claim/WarmPool）"套到 Agent runtime 沙箱生命周期。

## TODO

- [ ] 写 controller-runtime 的工作流程图（informer → cache → workqueue → reconciler）
- [ ] 写 OperatorHub / kubebuilder / operator-sdk 的关系
- [ ] 写"什么时候不该用 Operator"（反模式：简单的脚本能解决的别上 CRD）
- [ ] 经典 Operator 案例：prometheus-operator / cert-manager / istio-operator
