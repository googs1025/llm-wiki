---
title: RadixAttention
tags: [concept, ai-infra, kv-cache, llm-inference, prefix-sharing]
date: 2026-09-22
sources: [sglang-architecture-analysis.md]
related: [sglang, paged-attention, vllm]
---

# RadixAttention

[[sglang]] 论文（Zheng et al., NeurIPS 2024）提出的 **token 级 KV 缓存复用机制**。它用 **radix 树** + **两级 KV pool** 实现"任意 token 边界都能 split & share"；[[vllm]] 的 [[paged-attention]] 则使用配置内固定大小、按 block 边界复用的逻辑/物理 block，具体大小取决于配置、attention backend 和版本。历史论文仅在其 LLaMA-7B tree-of-thought / few-shot 等工作负载上报告 **1.6–6.4×** over vLLM，不是当前通用吞吐结论。

## 核心数据结构

### TreeNode

每个节点持有：
- `key: RadixKey` —— 变长 token 序列（支持 bigram 模式给 EAGLE 用）
- `value: torch.Tensor` —— 指向 `TokenToKVPool` 的 KV 索引张量
- `children: dict[int, TreeNode]` —— 首 token 到子节点的映射
- `lock_ref: int` —— 引用计数，>0 时禁止 evict（保护 in-flight 请求）
- `evicted: bool` —— 已 evict 的占位（支持增量恢复）

### 两级 KV pool

```
┌──── ReqToTokenPool ────┐     ┌──── TokenToKVPool ────┐
│ shape: [N_req, ctx_max]│     │ flat token-indexed    │
│ row i → list of token  │ ──> │ [kv_0, kv_1, ..., kv_M]│
│         indices for    │     │ 物理 GPU K, V tensors │
│         req i          │     │ MHA / MLA / NSA 变体  │
└────────────────────────┘     └───────────────────────┘
              ▲                          ▲
              │                          │
              └── radix 树叶 value ──────┘
                  指向 KV pool 索引区间
```

**双跳的好处**：radix 树叶直接指向 KV pool 位置；attention kernel 用 device-resident `req_to_token` 张量做一次 gather —— 既保留 token 级粒度，又能让 kernel 高效访存。

## 核心算法

### match_prefix(input_ids)

```
walk from root:
  for each level:
    find child whose key shares prefix with remaining input_ids
    if full match → descend
    if partial match → SPLIT child:
        原节点截断到匹配长度
        剩余 token 移到新子节点（保留原 value 的对应区间）
    if no match → stop
return (device_indices, last_node)
  device_indices = 已命中所有节点 value 的拼接（直接喂 attention kernel）
  last_node     = 匹配链尾（给后续 insert 用）
```

### insert(req)

请求完成时调用：
1. 在 `req.last_node` 下挂新节点，`key = req.fill_ids[len(prefix):]`
2. `value = req.out_cache_loc`（这次 forward 新写入的 KV 槽位）
3. 父节点 `lock_ref` 递减 → 完成后可被 evict

### Eviction

5 策略：LRU / LFU / FIFO / SLRU / Priority。
evict 时 pop `evictable_leaves` 堆顶 → free 该节点 `value` 指向的 KV 槽位 → 递归向上 unlock。`lock_ref > 0` 的节点跳过（保护 in-flight 请求）。

## 前缀命中与分叉流程

```text
输入 token prefix → Radix root → longest-prefix match
        ┌───────────────┴────────────────┐
        │ 完整命中                        │ 部分命中/未命中
        │ 复用已有 KV 节点                │ split node / 新建 suffix
        └───────────────┬────────────────┘
                        ↓
             只对未命中 suffix 执行 prefill
                        ↓
             insert token → KV pool → radix tree
                        ↓
             eviction 从可回收叶节点释放
```

## vs [[paged-attention]] 关键差异

| 维度 | RadixAttention | PagedAttention |
|------|----------------|----------------|
| **复用粒度** | token 级（树节点变长） | 配置内固定大小的 block（大小依配置/backend/版本） |
| **索引结构** | Radix 树 + 两级 pool | Block table（数组） |
| **任意分叉点 split** | ✅ 树节点动态 split | 默认 full-block APC 按 block 边界对齐；可选更细的可配置 match unit |
| **碎片** | 区间连续 | partial block 可有未用槽，程度依 block size 与负载而定 |
| **共享 system prompt** | Radix 树支持任意 token 边界的前缀分叉 | 默认 full-block APC 路径需等待完整 block；当前 vLLM 可通过 `cache_partial_block` / 可配置 `prefix_match_unit` 使用更细的 partial entry，受配置/backend/版本与 match-unit 约束 |
| **实现复杂度** | 较高（树平衡 + lock_ref + evict） | 较低（block table 哈希） |
| **历史论文工作负载** | LLaMA-7B tree-of-thought / few-shot 等工作负载报告 1.6–6.4× over vLLM，非当前通用结论 | 论文当时的对照实现 |

## 工程要点

- **radix 树是 lock-free 的**：单 Scheduler 进程独占，不需要锁
- **device_indices 是 device-resident 张量**：直接喂 attention kernel，省去 CPU↔GPU 拷贝
- **bigram 模式**：给 EAGLE 投机解码用 —— key 是 (token_i, token_i+1) 对而非单 token，匹配 draft tree 结构
- **5 变体并存（2026-09-14 分析快照）**：`radix_cache.py`（vanilla）/ `hiradix_cache.py`（分层）/ `mamba_radix_cache.py`（Mamba）/ `swa_radix_cache.py`（Sliding Window Attention）/ `radix_cache_cpp.py`（C++ 加速版），按 attention 类型在启动时绑定；当前 release 需重新核验该 inventory

## 出处

Zheng et al., *"SGLang: Efficient Execution of Structured Language Model Programs"*, NeurIPS 2024。

## 相关页面

- 工程实现：[[sglang]] → `mem_cache/radix_cache.py`
- 对照算法：[[paged-attention]]（[[vllm]] 的 KV 管理）
- 架构详解：[[src-sglang-architecture]]
