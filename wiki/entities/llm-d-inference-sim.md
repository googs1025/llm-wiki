---
title: llm-d Inference Sim
tags: [entity, llm-serving, simulator, benchmark, llm-d]
date: 2026-06-13
sources: [llm-d-inference-sim-architecture-analysis.md]
related: [[llm-d]], [[llm-d-benchmark]], [[inference-routing]], [[llm-inference]], [[kv-cache-offload]]
---

# llm-d Inference Sim

llm-d Inference Sim 是 [[llm-d]] 生态的轻量 vLLM 行为模拟器，用 OpenAI-compatible HTTP、vLLM-like gRPC/API、KV cache events、LoRA lifecycle、延迟模型和 metrics 模拟推理服务。详见 [[src-llm-d-inference-sim-architecture]]。

## 架构边界

它不做真实模型推理，也不代表真实 GPU 性能。它的定位是控制面和系统策略验证：让 [[inference-routing]]、[[llm-d-benchmark]]、autoscaling、P/D、KV-aware routing 和 failure injection 可以在无 GPU 或低成本环境中先跑通。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 验证 router / Gateway / benchmark 流程 | 适合，协议和 metrics 尽量贴近 vLLM。 |
| 测试 KV-aware routing / prefix cache 信号 | 适合，能生成 block key、PrefixCacheStats 和事件。 |
| 需要生产性能数据 | 不适合，必须用真实 [[vllm]] / [[sglang]] / GPU。 |
| 做 CI 或 Kind 环境 smoke test | 适合，比真实模型更便宜稳定。 |

## 同类对比

| 维度 | [[llm-d-inference-sim]] | [[vllm]] | mock HTTP server |
|---|---|---|---|
| 推理行为 | 行为模拟 | 真实推理 | 少量 API stub |
| KV/cache 语义 | 模拟 block/cache/events | 真实 KV cache | 通常没有 |
| 适合问题 | 控制面、路由、autoscaling、benchmark 流程 | 性能和生产执行 | 客户端单元测试 |

## 选型提示

把它当成“系统测试替身”，不要当成性能基线。要理解 [[llm-d]] 的控制面闭环，它和 [[llm-d-benchmark]] 放在一起看最有价值。
