---
title: AIBrix
tags: [entity, llm-serving, kubernetes, vllm, ai-infra, kv-cache]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[llm-inference]], [[inference-routing]], [[model-serving-operator]], [[vllm]], [[dynamo]], [[llm-d]], [[kv-cache-offload]]
---

# AIBrix

AIBrix 是 vLLM 生态的可插拔 GenAI inference infrastructure，提供 LLM Gateway/Routing、LoRA 管理、LLM app-tailored autoscaler、Unified AI Runtime、distributed inference、distributed KV cache、异构 GPU serving 和 GPU 硬件故障检测。

## 解决的问题

企业使用 vLLM fleet 时，真正的难点不只在 engine：还需要 adapter 管理、跨副本路由、KV 复用、动态扩缩、成本优化和 GPU 故障处理。AIBrix 把这些能力拆成可组合组件。

## 核心边界

AIBrix 更贴近 vLLM 生态和企业控制面，不是新的推理 engine，也不是 Kubernetes 通用模型 API。它的 KV offloading 可以作为独立组件使用，路由和 autoscaling 也可以按需组合。

## 适用场景

适合已有 vLLM 技术栈、希望逐步加入 LoRA、KV、Gateway、异构 GPU 和企业运维能力的团队。需要 Gateway API/InferencePool 标准化时比较 [[llm-d]]；需要完整 P/D/KV runtime 时比较 [[dynamo]]。

详见 [[src-aibrix-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
