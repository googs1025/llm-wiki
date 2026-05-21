---
title: LLM Inference
tags: [concept, ai-infra, llm-inference, llm-serving, stub]
date: 2026-05-16
sources: [dynamo-architecture-analysis.md]
related: [vllm, sglang, dynamo, paged-attention, radix-attention, disaggregated-serving, kv-cache-offload]
---

# LLM Inference

> [!note] Stub
> 占位页。LLM 推理是 vLLM/SGLang/Dynamo 等条目的上位概念，待后续主题摄入时扩写。

LLM 推理（inference / serving）指把训练好的大语言模型部署成在线服务，对外提供 token 生成 API。核心挑战：高吞吐、低延迟、长 context、多并发、成本。

## TODO

待后续摄入主题：
- prefill vs decode 两阶段计算图
- continuous batching / inflight batching
- speculative decoding（投机解码）家族
- chunked prefill
- LoRA serving
- multi-modal serving
- 量化推理（FP8 / INT4 / AWQ / GPTQ）

## 已建相关页

- 工程实现：[[vllm]]、[[sglang]]、[[dynamo]]
- KV 管理：[[paged-attention]]、[[radix-attention]]、[[kv-cache-offload]]
- 部署架构：[[disaggregated-serving]]
- 架构详解：[[src-dynamo-architecture]]
