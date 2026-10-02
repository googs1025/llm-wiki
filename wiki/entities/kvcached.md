---
title: KVCacheD
tags: [entity, ai-infra, llm-inference, kv-cache, gpu-virtual-memory, gpu-sharing, oss]
date: 2026-10-02
sources: [kvcached-architecture-analysis.md]
related: [vllm, sglang, elastic-kv-cache, gpu-sharing, paged-attention, radix-attention, kv-cache-offload]
---

# KVCacheD

> 本地源码分析：[[src-kvcached-architecture]]，HEAD `884108704f44`；三项目关系知识地图：[[kvcached-sglang-vllm-knowledge-system]]；逐函数调用链：[[kvcached-source-code-deep-dive]]。

## 一句话定位

KVCacheD 是面向 [[vllm]] 与 [[sglang]] 的 GPU KV cache 虚拟内存插件：给引擎提供地址稳定、容量较大的虚拟 KV tensor，再按请求真实使用的 block/token 动态映射 CUDA/HIP 物理页，使同一 GPU 上的多个模型实例弹性共享 VRAM。

## 它在系统中的边界

KVCacheD 管理：

- KV tensor 的 GPU virtual address reservation 与 physical page backing。
- engine logical block/token 到 VMM page 的映射、释放、回滚和 resize。
- SGLang/vLLM allocator、pool、tensor allocation 和 capacity profiling 的适配。
- TP/PP worker map/unmap 一致性、shared-memory limit 和可观测性。

KVCacheD 不管理：

- 请求排队、batching、preemption policy 和模型 forward。
- attention kernel、block table/RadixCache 的核心算法。
- 跨实例共享同一份 prefix KV 内容。
- 通用 GPU 调度、硬件分区或 hostile multi-tenant 隔离。
- 模型权重本身；可选 controller 只是调用引擎已有 sleep/release API。

## 架构边界

```text
vLLM / SGLang
  scheduler · prefix metadata · block/token IDs · attention kernels
                       │ allocator/tensor contract
                       ▼
KVCacheD engine adapters
                       │ logical block operations
                       ▼
KVCacheManager → PageAllocator → FTensorAllocator
                       │ VA map/unmap
                       ▼
                 CUDA/HIP physical VRAM
```

最重要的三个抽象不要混淆：engine block/token page 是调度和 attention 的逻辑单位；KVCacheD page 是 GPU VMM 物理映射单位；attention kernel block 是 backend 执行单位。三者大小可以不同。

## 与 vLLM 的关系

[[vllm]] 的 scheduler-side BlockPool/KV coordinator 与 worker-side KV tensor 常分属不同进程。KVCacheD 因此替换 `BlockPool` 为 ElasticBlockPool，在 GPUModelRunner 创建 VMM-backed tensor，并让 EngineCore 通过 Unix socket 把相同 offset 的 map/unmap 广播到所有 TP/PP worker。queued/async execution 下，物理页释放前还有 worker collective barrier。

保留的 vLLM 语义包括：block table、request hash、APC、null block、ref count、scheduler preemption、attention backend 和 `bind_kv_cache`。

## 与 SGLang 的关系

[[sglang]] 的 Scheduler、token allocator、KV pool 和 [[radix-attention]] 围绕 token index 工作。KVCacheD 将 token/paged allocator 和 MHA/MLA/Mamba/hybrid memory pool 替换为 elastic 版本，但保留原生 RadixCache、ScheduleBatch、ModelRunner 和 attention backend。当前每个 TP worker 本地拥有并驱动自己的 KVCacheD pool。

## 何时使用

- 同卡常驻多个模型，权重可以共存，但各模型 KV 峰值错开。
- compound AI 或 multi-agent 流程中，多个专用模型负载间歇出现。
- 推理与 fine-tuning、diffusion 等任务共置，需要 KV cache 主动让出 VRAM。
- 能固定 engine/PyTorch/backend 版本并维护 GPU correctness regression。

## 何时不使用

- 单模型已经长期吃满 GPU，几乎没有可复用的 idle KV reservation。
- 需要跨节点 KV transfer/offload、prefix 内容共享或 KV-aware routing；应看 [[kv-cache-offload]] 和 distributed serving 层。
- 需要强租户隔离或通用 CUDA memory quota；应看 [[gpu-sharing]] 的 MIG/MPS/vGPU 路线。
- 目标 engine/backend/layout 超出 adapter 支持范围，且无法锁版本和回归。
- 不能接受 version-aware monkey patch 对上游内部 API 的维护成本。

## 同类与相邻方案

| 方案 | 与 KVCacheD 的关系 |
|---|---|
| [[paged-attention]] | vLLM 的逻辑 block/KV indexing；KVCacheD 可作为其下层 physical backing |
| [[radix-attention]] | SGLang 的 prefix metadata/token-index reuse；KVCacheD 管其引用的物理 backing |
| [[kv-cache-offload]] | 把 KV 内容迁到 CPU/SSD/远端；与同卡 GPU VMM 弹性互补而非等价 |
| [[gpu-sharing]] | 调度、分区和通用 runtime 隔离；KVCacheD 只优化接入引擎的 KV memory |

## 入口

- 完整源码分析：[[src-kvcached-architecture]]
- 三项目知识体系：[[kvcached-sglang-vllm-knowledge-system]]
- 源码深潜：[[kvcached-source-code-deep-dive]]
- 集成与实验：[[kvcached-integration-implementation-guide]]
- 核心概念：[[elastic-kv-cache]]
- 引擎背景：[[vllm]]、[[sglang]]
