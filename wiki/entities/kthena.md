---
title: Kthena
tags: [entity, kubernetes, llm-serving, inference-routing, autoscaling, volcano]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[llm-inference]], [[model-serving-operator]], [[inference-routing]], [[disaggregated-serving]], [[rbg]], [[llm-d]], [[vllm]], [[sglang]]
---

# Kthena

Kthena 是 Volcano 社区的 Kubernetes-native AI serving platform，覆盖模型生命周期、请求路由、P/D 分离、扩缩、限流、canary、拓扑感知和 gang scheduling。

## 核心抽象

- **ModelBooster**：一站式部署 API，级联创建下游 serving 资源。
- **ModelServing**：以 ServingGroup × Role 表达推理 workload，支持 Prefill/Decode、恢复、滚动更新、拓扑和 gang 调度。
- **ModelServer**：通过 workload selector 发现并暴露推理 Pod，承载重试、超时和连接策略。
- **ModelRoute**：按模型、LoRA、路径或 header 匹配，支持权重流量、canary、token rate limit。
- **AutoScalingPolicy**：指标驱动、panic/stabilization window、异构资源和 P/D role-level 扩缩。

## 架构边界

Kthena 的显著设计是 control plane 与 data plane 解耦：workload controller 和 router 可分别安装，router 也能接入 Gateway API。它比纯 model operator 更靠近完整 LLM serving platform；比 RBG 更直接提供模型/路由 API；与 [[llm-d]] 的差异在于更强调 Volcano 拓扑/gang 和自身的 ModelRoute/ModelServing 资源模型。

## 适用与限制

适合希望在 Kubernetes 内获得一体化 LLM serving、P/D role autoscaling、KV/LoRA-aware routing 和 Volcano 调度的团队。若组织已经标准化 Gateway API/InferencePool 并希望最大化复用该生态，应同时比较 [[llm-d]]；若主要需求是跨多云 GPU 管理和 MaaS，应比较 [[gpustack]]。
