---
title: PagedAttention
tags: [concept, ai-infra, kv-cache, llm-inference]
date: 2026-05-15
sources: [sglang-architecture-analysis.md]
related: [vllm, radix-attention, sglang]
---

# PagedAttention

[[vllm]] 论文（Kwon et al., SOSP 2023）提出的 **block 级 KV 缓存管理机制**。把 OS 虚存分页思想（按页分配 + 页表映射）搬到 LLM KV cache，**16 token 为一个 block**，每个请求用 **block table** 记录"逻辑序列位置 → 物理 block"映射。

## 核心思想

```
传统 (HF transformers):
  按 max_seq_len 预分配 KV         浪费严重
  ──────────────────────────────
  [req0  used  ][   unused   ]
  [req1 used][        unused        ]

PagedAttention:
  按 block 按需分配                几乎无浪费
  Block 0: ████████████████ (16 tokens)
  Block 1: ████████████░░░░ (12 tokens used)
  Block 2: ░░░░░░░░░░░░░░░░ (free)

  Block Table per req:
    req0: [B0, B1]
    req1: [B0, B2]   ← 共享 system prompt 在 B0
```

## 关键机制

- **Block table**：每个请求有一个 `int32 list[blocks]`，attention kernel 用它把"逻辑 token 索引"翻译成"物理 KV 位置"
- **Block 大小固定**：默认 16 token，是性能 / 碎片权衡的产物
- **Prefix sharing**：多个请求共享同一个 system prompt block，引用计数管理；释放时只有 ref=0 才回收
- **Copy-on-write**：beam search 等场景 fork 同一个 block table，写入时拷贝
- **Swap to CPU**：内存紧张时把不活跃 block swap 到 CPU pinned memory

## 工程影响

- **首创性**：2023 年第一个把虚存分页引入 LLM serving，HuggingFace TGI / Ray Serve / Anyscale / Together AI 都基于此或受启发
- **吞吐量**：典型 2-4× over HF transformers
- **简单可靠**：block table 是数组，无需锁，调度逻辑直接

## 局限与 [[radix-attention]] 的对比

- **16 token 边界刚性**：长度 17 的 system prompt 占 2 个 block 但第 2 个 block 浪费 15 槽
- **共享只能整 block**：末尾不满 16 token 的尾巴无法被复用
- **碎片放大效应**：上千请求时累计碎片显著

[[radix-attention]]（[[sglang]] 提出）通过 token 级 radix 树 + flat KV pool 解决这些限制。

## 出处

Kwon et al., *"Efficient Memory Management for Large Language Model Serving with PagedAttention"*, SOSP 2023。

## 相关页面

- 工程实现：[[vllm]]
- 改进算法：[[radix-attention]]（[[sglang]] 提出）
- 同类对比：[[sglang]] 架构详解 → [[src-sglang-architecture]]
