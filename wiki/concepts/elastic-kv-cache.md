---
title: Elastic KV Cache
tags: [concept, ai-infra, llm-inference, kv-cache, gpu-virtual-memory, memory-management]
date: 2026-10-02
sources: [kvcached-architecture-analysis.md, vllm-architecture-analysis.md, sglang-architecture-analysis.md]
related: [kvcached, vllm, sglang, paged-attention, radix-attention, kv-cache-offload, gpu-sharing, llm-inference]
---

# Elastic KV Cache

Elastic KV cache 指把推理引擎可寻址的 KV 容量与当前真实占用的 GPU 物理显存解耦：引擎拥有稳定的逻辑槽位和 tensor 地址，物理页只在活跃请求使用时映射，并在 block/token 不再被运行请求或 prefix cache 引用后回收。

[[kvcached]] 是这一模式的直接实现；[[vllm]] 的 [[paged-attention]] 和 [[sglang]] 的 [[radix-attention]] 则分别提供上层 block/token 与 prefix reuse 语义。

## 四类容量

理解弹性 KV 必须区分四个数字：

| 容量 | 含义 | 谁决定 |
|---|---|---|
| Virtual capacity | engine 可以寻址的最大 KV slot/block 数 | engine profile + KVCacheD tensor reservation |
| Logical free capacity | 当前没有被 request/cache metadata 占用的 slot/block | BlockPool 或 token allocator + KVCacheManager ledger |
| Mapped physical capacity | 当前已有真实 VRAM backing 的 VMM pages | PageAllocator/FTensorAllocator |
| Device physical headroom | 同 GPU 所有进程竞争后的剩余 VRAM | GPU driver，全设备动态状态 |

`logical free > 0` 不代表下一次 allocation 一定成功，因为另一个进程可能在检查后拿走 device headroom。共享环境中的 capacity check 是 snapshot，不是 reservation。

## 两级分页模型

```text
Engine logical space
  request → token slots / KV blocks → block table or RadixCache values
                         │ many logical blocks per VMM page
                         ▼
KVCacheD physical space
  InternalPage → virtual offset → CUDA/HIP physical page handle
                         │ map
                         ▼
GPU virtual tensor address → physical VRAM
```

[[paged-attention]] 的“page/block”解决 sequence KV 的逻辑碎片和 block table 映射；KVCacheD 的 page 解决 GPU virtual address 与 physical allocation 的映射。它们是上下两层分页，不是重复实现。

## 为什么 tensor 指针可以稳定

GPU VMM 允许先 reserve 一段 virtual address，再把不同 physical allocation handle map 到其中的 page-aligned offset。KVCacheD 用该 VA 创建 torch tensor view；attention kernel 捕获和读取的是相同地址。物理页释放时重新映射 zero page，tensor 本身不销毁。

这使 engine 无需感知物理页生命周期，但引入严格约束：

- shape/stride 必须与 backend 的真实读写方式一致。
- unmap 前必须确保所有 GPU command 已结束。
- 同一 logical offset 在 TP/PP rank 上必须处于一致状态。
- block/page geometry 必须保证逻辑 block 不落入无法映射的跨页空洞。

## prefix cache 与弹性的张力

完成请求后，prefix cache 继续保留 block/token index，就等价于继续引用对应 KV 数据。只要 page 上还有一个被缓存的 block，整个物理页都不能释放。因此更高 hit rate 与更强显存弹性天然冲突。

常见策略：

- `unlimited`：最接近原生 cache，弹性最弱。
- `disabled/immediate eviction`：最容易释放显存，但丢失跨请求复用。
- `bounded cache`：限制 cached tokens/blocks，并优先淘汰能清空完整 physical page 的 victim。

## contiguous 与 per-layer layout

| Layout | 物理映射 | 优点 | 约束 |
|---|---|---|---|
| Contiguous/compound | 一个 page 同时覆盖多 layer/KV buffer | map 次数少、跨层 backing 一致 | per-layer view 有 stride/interleave；部分 copy、PD、ROCm backend 不接受 |
| Non-contiguous/per-layer | 每层独立 FTensor/page | 每层 region 连续，兼容更多 backend/transfer | map handle更多，多层原子性和开销更高 |

Layout 不是纯性能开关，而是 attention backend、KV copy、P/D connector 与 Mamba/hybrid state 的数据契约。

## 正确性模型

Elastic KV cache 需要同时维持三类不变量：

1. **Ledger invariant**：逻辑 block 不能重复分配或丢失，partial allocation 失败必须完整回滚。
2. **Mapping invariant**：一个 logical offset 的所有 layer/K/V target 必须全映射或全未映射，不能处于 partial mapping。
3. **Execution lifetime invariant**：GPU/worker 在最后一次读写完成前，physical page 不得释放。

为满足这些不变量，[[kvcached]] 使用 map rollback/quarantine、TP/PP transactional unmap、vLLM async worker barrier、shutdown drain 和 fail-pool 语义。

## 与相邻概念的区别

| 概念 | 主要解决的问题 | 与 Elastic KV 的关系 |
|---|---|---|
| [[paged-attention]] | engine 内 KV block 管理和 attention addressing | 上层逻辑索引 |
| [[radix-attention]] | token-level prefix reuse | 上层 cache metadata |
| [[kv-cache-offload]] | KV 数据跨 GPU/CPU/SSD/远端层级迁移 | 可组合，但数据路径和故障域不同 |
| [[gpu-sharing]] | GPU 调度、分区、执行/显存隔离 | 更外层资源治理 |
| sleep mode | 释放 KV，甚至权重和 allocator state | 粗粒度实例生命周期；Elastic KV 是请求级/页级 |

## 评估指标

- idle/steady/peak mapped KV bytes。
- logical blocks、mapped pages、reserved pages、page occupancy。
- allocation miss、scheduler retry/preemption、map/unmap latency。
- prefix hit rate 与 page-aware eviction 造成的命中损失。
- TTFT、ITL、throughput 和 OOM rate。
- TP/PP failure injection、shutdown 后 shared segment/socket cleanup。

## 相关页面

- 实现：[[kvcached]]、[[src-kvcached-architecture]]
- 关系地图：[[kvcached-sglang-vllm-knowledge-system]]
- 引擎：[[vllm]]、[[sglang]]
- 基础概念：[[llm-inference]]、[[paged-attention]]、[[radix-attention]]
