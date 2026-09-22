---
title: PagedAttention
tags: [concept, ai-infra, kv-cache, llm-inference]
date: 2026-09-22
sources: [vllm-architecture-analysis.md]
related: [vllm, radix-attention, sglang]
---

# PagedAttention

[[vllm]] 论文（Kwon et al., SOSP 2023）提出的 **block 级 KV 缓存管理机制**；当前官方架构仍以 block table、attention backend 与 prefix caching 组合扩展。它把 OS 虚存分页思想（按页分配 + 页表映射）搬到 LLM KV cache：在一个确定的配置内，KV 按固定大小的逻辑/物理 block 管理，每个请求用 **block table** 记录"逻辑序列位置 → 物理 block"映射。具体 block 大小取决于配置、attention backend 和版本。

## 核心思想

```
传统 (HF transformers):
  按 max_seq_len 预分配 KV         浪费严重
  ──────────────────────────────
  [req0  used  ][   unused   ]
  [req1 used][        unused        ]

PagedAttention:
  按 block 按需分配（block size = B）
  Block 0: [████████]  complete (B/B tokens)
  Block 1: [█████░░░]  partial tail (k/B tokens, 0 < k < B)
  Block 2: [░░░░░░░░]  free (B slots)

  Block Table per req:
    req0: [B0, B1]
    req1: [B0, B2]   ← 共享 system prompt 在 B0
```

## 关键机制

- **Block table**：每个请求有一个 `int32 list[blocks]`，attention kernel 用它把"逻辑 token 索引"翻译成"物理 KV 位置"
- **Block 大小固定于当前配置**：逻辑/物理 block 使用同一 block size `B`；具体 `B` 依配置、attention backend 和版本而定
- **Prefix sharing**：传统/默认 full-block APC 路径按 block 边界共享 system prompt，partial tail 在形成完整 block 前不可复用。当前 vLLM 可通过 `cache_partial_block` 与可配置的 `prefix_match_unit` 启用更细粒度的 partial entry，但仍受配置、backend、版本及整除/match-unit 约束。Block table 的共享使用引用计数管理，释放时只有 ref=0 才回收。详见 [Prefix Caching](https://docs.vllm.ai/en/latest/design/prefix_caching/) 与 [BlockPool API](https://docs.vllm.ai/en/latest/api/vllm/v1/core/block_pool/)
- **Copy-on-write**：beam search 等场景 fork 同一个 block table，写入时拷贝
- **Swap to CPU**：内存紧张时把不活跃 block swap 到 CPU pinned memory

## 工程影响

- **首创性**：2023 年第一个把虚存分页引入 LLM serving，HuggingFace TGI / Ray Serve / Anyscale / Together AI 都基于此或受启发
- **吞吐量**：典型 2-4× over HF transformers
- **简单可靠**：block table 是数组，无需锁，调度逻辑直接

## 逻辑地址到物理 KV 的流程

```text
请求 token 位置 i → 逻辑 block = i // block_size
        → block table[logical block]
        → 物理 GPU KV block
        → attention kernel gather K/V
        → 写入新 token block 或触发扩容
```

## 局限与 [[radix-attention]] 的对比

- **Block 边界刚性**：前缀共享按当前 block size `B` 对齐，不能在 block 内任意分叉
- **默认 full-block APC 的 partial tail 限制**：在传统/默认路径中，末尾未满的 block 在形成完整 block 前无法被前缀复用；启用 `cache_partial_block` 并配置 `prefix_match_unit` 后可以更细粒度匹配，实际边界依配置/backend/版本与整除约束而定
- **内部碎片依负载而定**：程度取决于 block size、请求长度分布与实现配置

[[radix-attention]]（[[sglang]] 提出）通过 token 级 radix 树 + flat KV pool 解决这些限制。

## 出处

Kwon et al., *"Efficient Memory Management for Large Language Model Serving with PagedAttention"*, SOSP 2023。

## 相关页面

- 工程实现：[[vllm]]
- 改进算法：[[radix-attention]]（[[sglang]] 提出）
- 同类对比：[[sglang]] 架构详解 → [[src-sglang-architecture]]
