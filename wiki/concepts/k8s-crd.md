---
title: Kubernetes CRD
tags: [kubernetes, extensibility, api]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md, agent-sandbox-architecture-analysis.md]
related: [[kubernetes]], [[k8s-operator]], [[HiClaw]], [[agent-sandbox]]
---

# Kubernetes CRD

> Stub — 待充实

CustomResourceDefinition（CRD）是 K8s 的扩展点：让任何团队在 apiserver 里**声明自定义资源类型**（带 Spec / Status / OpenAPI v3 schema validation / printer columns），用 kubectl / client-go 像内置资源一样操作。配合 controller 使用即构成 [[k8s-operator|Operator 模式]]。

## 在 AI Agent 项目中的使用

- [[HiClaw]] 定义 4 个 CRD：`Worker` / `Team` / `Human` / `Manager`（agentscope.io 组）
- [[agent-sandbox]] 定义 4 个 CRD：`Sandbox`（agents.x-k8s.io）+ `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool`（extensions.agents.x-k8s.io）

## 关键字段约定

| 字段 | 用途 |
|------|------|
| `Spec` | 用户声明的期望状态——不可由 controller 写 |
| `Status.Conditions` | controller 上报的实际状态，标准 `metav1.Condition` 列表 |
| `Status.ObservedGeneration` | 防 reconcile 看旧 spec |
| `OwnerReferences` | K8s GC 级联删除链 |
| `Finalizers` | 删除拦截，给 controller 做清理 |

## TODO

- [ ] 写 CRD 演进路径：v1alpha1 → v1beta1 → v1 的弃用约定
- [ ] 写 CRD 校验：OpenAPI v3 schema vs admission webhook 的取舍
- [ ] 写 CRD 的隐藏陷阱：generation vs resourceVersion 不能混用
- [ ] CRD 子资源：scale / status subresource 的工作机制
