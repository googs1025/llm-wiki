---
title: SGLang 架构与推理优化
tags: [architecture, llm-serving, radix-cache, kv-cache, inference-optimization]
date: 2026-09-13
sources: [sglang-architecture-analysis.md]
related: [[sglang]], [[vllm]], [[radix-attention]], [[paged-attention]], [[llm-inference]]
---

# SGLang 架构与推理优化

> 原文：`raw/sglang-architecture-analysis.md` · 资料：官方 README/docs · 版本：main @ `7f1f8c7`

## 一句话定位

[[sglang]] 是高性能 LLM serving runtime，核心差异是 [[radix-attention]]：用 radix tree 做 token-level KV prefix sharing；再以连续批、chunked prefill、融合 kernel、投机解码和 TP/PP/EP/DP 构成执行管线。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│ Client / OpenAI · Anthropic · Ollama · Native Engine                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP / gRPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / TokenizerManager                                         │
│  request lifecycle · tokenizer · structured program · streaming       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ ZMQ / shared memory
┌──────────────────────────────▼───────────────────────────────────────┐
│ Scheduler subprocess                                                  │
│  waiting/running batch · EXTEND/DECODE/MIXED · RadixCache · allocator  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ model input / metadata
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU ModelRunner                                                       │
│  attention backend · fused/quantized kernels · sampler                │
│       │                         │                                     │
│       ├─ TP/PP collectives         └─ EP token dispatch for MoE         │
│       └─ DP attention / batch partition                                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / states
┌──────────────────────────────▼───────────────────────────────────────┐
│ DetokenizerManager ──► stream response                                │
└──────────────────────────────────────────────────────────────────────┘
             │
             ├─ RadixCache / HiCache: GPU → host → storage tiers
             └─ PD/EPD disaggregation: transfer KV or encoder outputs
```

## 请求与缓存数据流

```
请求 / SGLang program
  │
  ├─ tokenizer + program state，形成可复用 token prefix
  ├─ RadixCache longest-prefix match：命中则复用 KV，否则分配 token/KV pool
  ├─ Scheduler 组成连续 batch：EXTEND / DECODE / MIXED
  │       └─ 长 prompt 以 chunked prefill 切片并与 decode 交错
  ├─ ModelRunner 选择 attention backend，执行 fused attention/FFN/MoE
  │       └─ TP/PP/DP/EP collective 或 all-to-all
  └─ sampler → DetokenizerManager → streaming response；完成后更新 radix tree
```

## 推理优化要点

- **KV**：RadixCache 做 token-level 前缀共享；HiCache 提供 GPU/host/storage 分层；量化 KV 降低容量；P/D 分离搬运 KV。
- **连续批**：EXTEND/DECODE/MIXED 与 chunked prefill 在 TTFT、ITL、吞吐间调节。
- **融合**：attention backend、sgl-kernel、JIT/torch.compile、CUDA Graph、fused MoE/量化 kernel 减少 launch 和中间读写。
- **并行**：TP 切权重，PP 切层，EP 分布 MoE 专家，DP 分区请求/批/KV；DP attention 可复制 attention、保留 FFN/MoE 的 TP/EP。

## 关键设计

- Radix tree 换取更细粒度 prefix reuse，同时增加树维护、eviction 与跨 rank locality 复杂度。
- Scheduler 只生成紧凑 batch/attention metadata，ModelRunner 专注 GPU 执行，backend 可替换。
- 结构化程序、会话缓存、投机解码和 P/D/EPD 复用同一套 runtime 扩展点。

## 相关页面

- [[sglang]]
- [[vllm]]
- [[radix-attention]]
- [[paged-attention]]
- [[llm-inference]]
