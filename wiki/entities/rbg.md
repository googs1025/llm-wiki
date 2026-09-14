---
title: RBG（RoleBasedGroup）
tags: [entity, kubernetes, llm-serving, distributed-inference, workload-api]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[llm-inference]], [[disaggregated-serving]], [[model-serving-operator]], [[kthena]], [[llm-d]], [[dynamo]]
---

# RBG（RoleBasedGroup）

RBG 是 sgl-project 的 Kubernetes workload API，用于编排多角色、有状态、分布式 AI inference workload。它把 gateway → router → prefill → decode 这类服务表达成 RoleBasedGroup，而不是把多个 Deployment/StatefulSet 当成互不相关的对象。

## 核心抽象

- **Role**：每个角色拥有自己的 spec、生命周期和策略，例如 prefill/decode。
- **RoleBasedGroup**：组成一个逻辑推理服务的多角色整体。
- **RoleInstance**：与一组 Pod 绑定的状态与升级单元。
- **CoordinatedPolicy**：协调跨角色升级、扩缩、maxSkew 和 progression。

## 架构边界

RBG 解决的是 workload topology、状态、原子操作、gang scheduling、硬件/网络亲和和跨角色协调；它不是完整 API gateway，也不是推理 engine。它适合作为 [[dynamo]]、[[llm-d]] 或自研 router/engine 上方的 Kubernetes workload substrate。

## 适用与限制

适合 P/D、multi-role、需要成组部署/升级/扩缩和稳定实例语义的场景。若只需要一个简单模型 Deployment + Service，RBG 的协调模型可能过重；若需要完整模型路由、限流、canary 和 API 入口，还要组合专用 serving/router 组件。
