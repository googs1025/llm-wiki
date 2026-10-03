---
title: PagedAttention
tags: [concept, ai-infra, kv-cache, llm-inference]
date: 2026-10-03
sources: [src-vllm-architecture]
related: ["[[vllm]]", "[[radix-attention]]", "[[sglang]]", "[[continuous-batching]]", "[[llm-inference]]", "[[kv-cache-offload]]", "[[elastic-kv-cache]]", "[[inference-routing]]"]
---

# PagedAttention

PagedAttention 是 [[vllm]] 论文提出的本地 KV 分块寻址与管理机制：序列使用逻辑 block 表达 KV，block table 把逻辑位置映射到实际 KV buffer 中的物理 block，attention kernel 按映射访问数据。这里的“物理 block”属于 engine 的 KV 分配层，不等于 GPU 驱动的物理显存页；后者见 [[elastic-kv-cache]]。

核心收益是让序列按需使用非连续的 KV blocks，减少为每个请求按最大长度预留空间造成的浪费。block 大小、布局与 attention backend 有关，不存在适用于所有版本、模型和硬件的统一 block size。[vLLM Paged Attention 设计](https://docs.vllm.ai/en/latest/design/paged_attention/)描述了这种按 block 寻址的 kernel 布局；原始分析保存在 [[src-vllm-architecture]]。

## 核心思想

```text
PagedAttention:
  按 block 按需分配（block size = B）
  Block 0: [████████]  complete (B/B tokens)
  Block 1: [█████░░░]  partial tail (k/B tokens, 0 < k < B)
  Block 2: [░░░░░░░░]  free (B slots)

  Block Table per req:
    req0: [B0, B1]
    req1: [B0, B2]   ← 已验证可复用的 prefix 在 B0
```

图中共享 B0 需要额外的前缀身份、有效性和引用管理；拥有 block table 本身不保证两个请求能共享 KV。

## 分配、复用与回收

- 调度器为本轮需要执行的 token 申请 KV slots；逻辑 block table 与物理 KV buffer 的映射必须一致。
- Prefix caching 可在该分块体系上识别已有前缀并复用 blocks。缓存键、共享边界、partial-block 支持和引用计数由实际实现决定，不能从“分页”直接推出。
- 请求完成会释放其引用；仍被其他请求或前缀缓存保留的 KV 不一定立即被覆盖。缓存淘汰、请求释放与底层显存释放属于不同动作。
- 共享后的写入隔离、抢占时的重算或 offload 需遵守目标 engine 的协议，不能假设所有 PagedAttention 路径都支持 CPU swap 或 copy-on-write。

当前前缀缓存实现见 [vLLM Prefix Caching](https://docs.vllm.ai/en/latest/design/prefix_caching/)。该链接为 2026-10-03 核验的 latest 文档，具体匹配粒度应回到部署 release 的代码和配置确认。

## 和调度及外部 KV 系统的边界

[[continuous-batching]] 决定本轮哪些请求前进、需要多少 KV；PagedAttention 提供它使用的局部空间管理。申请、写入、引用、保留与回收的共同流程见 [[llm-inference#F2 · KV Block 生命周期|F2 · KV Block 生命周期]]。

| 相邻机制 | 负责什么 | 与 PagedAttention 的区别 |
|---|---|---|
| [[radix-attention]] | 用前缀树组织缓存身份、匹配与淘汰 | 前缀语义和寻址布局是不同轴；不能推定与 vLLM block 对象相同 |
| [[inference-routing]] | 用负载或外部 locality index 选择 endpoint | 外部索引记录位置线索，实际 KV 有效性由 engine 确认 |
| [[kv-cache-offload]] | 将 KV 内容复制到 CPU、SSD 或远端，再按需恢复 | block table 不执行跨层复制，也不保证远端副本存在 |
| [[elastic-kv-cache]] | 将稳定的 GPU 虚拟地址与物理 backing 解耦 | engine 的 block 可用不代表底层物理显存一定能成功映射 |

## 评估与出处

关注 block 利用率、尾块浪费、分配失败与抢占、前缀命中后的实际 prefill 节省。吞吐收益需固定模型、硬件、请求长度和调度配置后测量，不能沿用历史论文中的倍数作为当前通用承诺。

Kwon et al., *Efficient Memory Management for Large Language Model Serving with PagedAttention*, SOSP 2023；工程证据见 [[src-vllm-architecture]]，SGLang 的对照分析见 [[src-sglang-architecture]]。
