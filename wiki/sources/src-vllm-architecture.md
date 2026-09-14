---
title: vLLM 架构与推理优化
tags: [architecture, llm-serving, kv-cache, inference-optimization]
date: 2026-09-13
sources: [vllm-architecture-analysis.md]
related: [[vllm]], [[paged-attention]], [[radix-attention]], [[llm-inference]], [[inference-routing]]
---

# vLLM 架构与推理优化

> 原文：`raw/vllm-architecture-analysis.md` · 资料：官方 README/docs · 版本：main @ `de50029`

## 一句话定位

[[vllm]] 是高吞吐 LLM serving 引擎：以 [[paged-attention]] 管理 KV block，以 continuous batching、编译/融合 kernel 和 TP/PP/EP/DP 扩展推理容量与吞吐。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Client / OpenAI API                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ request / stream tokens
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / LLM entrypoint                                           │
│  request validation · tokenizer · output streaming · metrics          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ IPC / multiprocessing
┌──────────────────────────────▼───────────────────────────────────────┐
│ V1 Engine Core                                                        │
│  Scheduler ──► Sequence groups ──► KV cache manager / block table     │
│      │                         │                                      │
│      └──────────────► Model input / sampling metadata                 │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ collective / IPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU Worker(s): ModelRunner                                           │
│  embedding → transformer blocks → attention backend → logits         │
│       │              │                    │                           │
│       │              ├─ TP all-reduce / all-gather                     │
│       │              ├─ PP send / receive between layer stages         │
│       │              └─ EP all-to-all for MoE experts                   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / logprobs
┌──────────────────────────────▼───────────────────────────────────────┐
│ Detokenization / output processor ──► API stream                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 请求与 KV 数据流

```
新请求
  │
  ├─ tokenize，计算 prompt token 与可复用 prefix hash
  │
  ├─ Scheduler 按 token budget 选择 waiting/running 请求
  │       ├─ 命中 block table → 只 prefill 未命中的 suffix
  │       └─ 未命中 → 分配 KV blocks；空间不足则 eviction / 等待
  │
  ├─ Prefill：批量处理 prompt，写入 paged KV cache
  │
  ├─ Decode：每轮为每条活跃序列生成一个 token；新序列可随时加入，完成序列释放 blocks
  │       └─ continuous batching + chunked prefill 平衡 TTFT 与 ITL
  │
  ├─ attention backend 通过 block table gather K/V，执行 fused attention
  │
  └─ logits → sampler → detokenize → stream；停止/异常时回收 sequence 与 KV blocks
```

## 推理优化要点

- **KV**：PagedAttention 解决碎片与动态增长；Prefix Caching 复用完整 KV block；offload/connector 扩展 GPU 之外的容量；FP8 等 KV dtype 以精度换容量。
- **连续批**：每轮按 token budget 调度；chunked prefill 与 decode 交错，平衡 TTFT、ITL、吞吐和队列等待。
- **融合**：attention backend、CUDA Graph、torch.compile fusion、RMSNorm/ROPE/KV 写入和 Fused MoE 降低 launch 与中间 tensor 成本。
- **并行**：TP 切层内权重，PP 切层，DP 复制模型，EP 分布 MoE 专家；通信拓扑和 batch shape 决定真实收益。

## 关键设计

- Engine Core 管理状态、预算和 KV；GPU worker 专注执行，形成清晰的调度/执行边界。
- 固定 block 换取可预测的内存管理；代价是 prefix sharing 受 block 边界影响。
- 后端可替换，允许按硬件、shape 和 prefill/decode 阶段选择不同 kernel。

## 相关页面

- [[vllm]]
- [[paged-attention]]
- [[radix-attention]]
- [[llm-inference]]
- [[inference-routing]]
