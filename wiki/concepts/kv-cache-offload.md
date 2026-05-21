---
title: KV Cache Offload（KV 多级缓存）
tags: [concept, ai-infra, kv-cache, llm-inference, memory-hierarchy]
date: 2026-05-16
sources: [dynamo-architecture-analysis.md]
related: [dynamo, paged-attention, radix-attention, disaggregated-serving, vllm, sglang, llm-inference]
---

# KV Cache Offload（KV 多级缓存）

把 LLM KV 缓存按访问频率分布在 **GPU 显存 → CPU pinned → 本地 NVMe → 远端对象存储** 多级存储层上，自动升降级，扩展 effective context length 超出单 GPU 显存上限的方法论。

## 为什么需要多级

GPU 显存有限（A100 80GB / H200 141GB / B200 192GB），但生产 LLM serving 面临：
- **长 context 需求**：128K / 1M token 的 system prompt + 多轮对话累积
- **多副本共享**：同一份 system prompt 被几千个请求复用，但 KV 重新算太贵
- **代价不对称**：算 KV ≈ 数百 ms（prefill），从 CPU 读回来 ≈ µs，从 SSD ≈ ms

把不活跃的 KV blocks 从 GPU 挤到便宜的存储层，等需要时再拉回来，比每次重新 prefill 划算得多。

## 四级层次（[[dynamo|Dynamo KVBM]] 实现为参考）

```
┌──────────────────────────────────────────────────────┐
│ G1: GPU device memory      最快、最贵、最稀缺        │
│     - Active compute blocks                          │
│     - ns 级访问                                       │
└────────────────┬─────────────────────────────────────┘
                 │ LRU 挤出（pop_lru）
                 ↓
┌──────────────────────────────────────────────────────┐
│ G2: CPU pinned memory     µs 级 RDMA 待命            │
│     - 热的非活跃 block                                │
│     - DDR4/5 几百 GB                                  │
└────────────────┬─────────────────────────────────────┘
                 │ TinyLFU + presence filter 降级
                 ↓
┌──────────────────────────────────────────────────────┐
│ G3: 本地 NVMe / SSD       ms 级，TB 规模              │
│     - 温的历史 block                                  │
│     - NIXL / GPUDirect Storage 直读                   │
└────────────────┬─────────────────────────────────────┘
                 │ 长尾归档
                 ↓
┌──────────────────────────────────────────────────────┐
│ G4: 对象存储（S3/Azure Blob/MinIO）   秒级，无上限    │
│     - 冷的历史 block                                  │
│     - 经 NIXL OBJ backend 透明访问                    │
└──────────────────────────────────────────────────────┘
```

## 关键机制

- **块身份必须全局唯一**：KV block 在所有层、所有 worker 中需要有同一个名字。Dynamo 用 128-bit `SequenceHash`（XXH3 + LoRA id），让块在 GPU/CPU/SSD/S3 之间认得出。
- **升降级策略**：高频用 LRU 控制 G1→G2，冷热分明用 LFU 控制 G2→G3。Dynamo KVBM 用 TinyLFU + presence filter（跳过已在目的层的 block）。
- **零拷贝传输**：跨层传输用 GPUDirect RDMA / GDS（GPU Direct Storage）/ 对象存储 SDK 减少 CPU 参与。NIXL 把这些统一成一个抽象。
- **去重 / 归并**：多副本独立产出的同一 prefix 应该只存一份。Dynamo 用 consolidator 按 SequenceHash 合并跨进程事件。
- **弱引用避免悬空**：offload pipeline 持有 weak ref，evict 后自然失效，不会"已经移走了还以为在原地"。

## 与 [[paged-attention|PagedAttention]] / [[radix-attention|RadixAttention]] 的关系

- **PagedAttention** 解决"单 GPU 内 KV 怎么按 block 管"
- **RadixAttention** 解决"多请求间 prefix 怎么免重算"
- **KV cache offload** 解决"KV 装不下时怎么挤出去 / 找回来"

三者正交、互补：现代推理栈通常同时部署。

## 与 [[disaggregated-serving|Disaggregated Serving]] 的协同

分离式 P/D 把 KV 从 prefill worker 传到 decode worker 时，本质上也是一种 "offload"——只不过目的地是另一个 GPU 而不是本地 CPU/SSD。Dynamo 把这两件事都包装成 NIXL MemType，传输路径同形。

## 收益与代价

**收益：**
- 长 context 不再被 GPU 显存上限卡死
- 多请求的 system prompt KV 跨集群共享（router 配合）
- 显存压力下降 → 更大 batch / 更多并发

**代价：**
- 多一层调度逻辑（什么时候升 / 什么时候降）
- 不命中时延迟跳到 µs / ms / 秒级
- 跨层传输需要高速互联或对应硬件（GDS / RDMA）

## 相关页面

- 旗舰实现：[[dynamo]] KVBM（[[src-dynamo-architecture]] "KVBM 四级层次"节）
- 协同概念：[[paged-attention]]、[[radix-attention]]、[[disaggregated-serving]]
- 上位概念：[[llm-inference]]
