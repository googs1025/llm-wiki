---
title: AIBrix
tags: [entity, llm-serving, kubernetes, vllm, ai-infra]
date: 2026-06-12
sources: [aibrix-architecture-analysis.md]
related: [[llm-inference]], [[llm-serving-engine-selection-map]], [[inference-routing]], [[model-serving-operator]], [[vllm]]
---

# AIBrix

vLLM 生态的 Kubernetes GenAI inference infrastructure，覆盖 gateway/routing、PodAutoscaler、ModelAdapter、KV cache/event sync、LoRA、distributed inference、GPU failure detection。详见 [[src-aibrix-architecture]]。

## 架构边界

AIBrix 不是新的推理引擎，而是把 [[vllm]] 等引擎放到 K8s 上运行时需要的 control plane。它和 [[dynamo]] 的区别在于：Dynamo 更强调分离式 P/D、KV-aware router 和多级 KV cache 的统一 runtime；AIBrix 更贴近 vLLM 生态和 K8s 组件化控制面。

## 选型判断

- 单机推理吞吐：先看 [[vllm]] / [[sglang]]。
- K8s 上的 vLLM fleet、autoscaling、adapter 和 routing：看 AIBrix。
- 分布式 serving runtime + KV 系统：看 [[dynamo]] / [[llm-d]]。
