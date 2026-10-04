---
title: RadixAttention
tags: [concept, ai-infra, kv-cache, llm-inference, prefix-sharing]
date: 2026-10-03
sources: [src-sglang-architecture]
related: ["[[sglang]]", "[[paged-attention]]", "[[vllm]]", "[[continuous-batching]]", "[[llm-inference]]", "[[inference-routing]]", "[[kv-cache-offload]]"]
---

# RadixAttention

RadixAttention 是 [[sglang]] 提出的前缀 KV 复用机制：把 token 序列的共享前缀组织成 radix 树，树节点关联已经计算好的 KV 位置；新请求先匹配前缀，再只计算未命中的部分。树组织的是缓存身份与复用关系，底层 KV pool 负责实际内容和寻址。

这与 [[paged-attention]] 的逻辑 block → 物理 KV block 映射侧重点不同。两者都需要分配、引用、回收和 attention addressing，不能把 RadixCache node 当成 vLLM block，也不能把 radix 树描述为对分页机制的全面替代。

## 核心数据与操作

| 对象或操作 | 语义 |
|---|---|
| Prefix key | 标识 token 前缀及影响缓存兼容性的命名空间或额外键 |
| Tree node | 保存一段共享前缀、子节点和对应 KV indices；分叉时可拆分节点 |
| KV pool | 持有实际 K/V buffer；树的 value 指向其中的槽位 |
| Prefix match | 返回可复用的最长前缀及索引，未命中 suffix 继续 prefill |
| 引用与淘汰 | 在飞请求的引用保护 KV；可淘汰节点释放所占槽位，策略由实现决定 |

[[src-sglang-architecture]] 提供 2026-09-14 所分析版本的 SGLang 历史架构、调度与缓存流程概览；其中的对象关系和执行路径不能直接外推到所有后续 release。

## 当前粒度约束（2026-10-03）

在 [SGLang v0.5.21 RadixCache 源码](https://github.com/sgl-project/sglang/blob/v0.5.21/python/sglang/srt/mem_cache/radix_cache.py)中，`RadixKey.match` 的结果会按 `page_size` 对齐；key 还具有额外命名空间语义。因此“任意 token 边界都能 split/share”只适用于满足相应粒度条件的路径，不是所有 attention backend 和 cache 变体的共同保证。

前缀相同也不自动意味着 KV 可用：模型、adapter、tokenization、缓存布局与状态必须兼容，且数据在使用前不能已经被淘汰。Radix 树的匹配结果需要与 KV allocator、请求引用和实际 residency 一起解释；cache eviction 不等于释放 GPU 驱动层的物理页，后者见 [[elastic-kv-cache]]。

## 和连续批处理的关系

[[continuous-batching]] 每轮决定 waiting/running 请求如何共享 token 与 KV 预算。前缀命中会减少需要执行的 prefill，但缓存保留也会占用 KV 空间，影响后续请求的准入与抢占。请求结束后可以释放请求引用并保留前缀缓存；容量压力下再按策略淘汰。完整状态边界见 [[llm-inference#F2 · KV Block 生命周期|F2 · KV Block 生命周期]]。

## 本地缓存与外部路由

RadixCache 在 engine 内确认“这个前缀有哪些可复用 KV”。外部 [[inference-routing]] 可以维护相似的前缀树或 locality index，回答“哪个 endpoint 更可能命中”。外部索引是异步信息，既不持有 engine 的本地引用，也不替 engine 保证数据仍然存在。

[[kv-cache-offload]] 则实际搬运 KV 内容，并在恢复后交由 engine 验证和接入。树匹配、endpoint picking 与 KV 数据复制可以协同，但各自拥有不同状态与失败边界。

## 出处与评估

Zheng et al., *SGLang: Efficient Execution of Structured Language Model Programs*, NeurIPS 2024。历史论文中的吞吐结果只对应其当时模型与工作负载；当前评估应同时记录前缀分布、命中长度、缓存占用、淘汰压力和 TTFT，见 [[llm-serving-performance]]。

工程入口为 [[sglang]] 与 [[src-sglang-architecture]]；[[vllm]] / [[paged-attention]] 提供本地 KV 分块管理的对照。
