---
title: KVCacheD 与 SGLang、vLLM 架构关系及源码实现
tags: [architecture, llm-serving, kv-cache, gpu-virtual-memory, gpu-sharing]
date: 2026-10-02
sources: [kvcached-architecture-analysis.md]
related: [kvcached, sglang, vllm, elastic-kv-cache, gpu-sharing, llm-inference, paged-attention, radix-attention]
---

# KVCacheD 与 SGLang、vLLM 架构关系及源码实现

> 原文：`raw/kvcached-architecture-analysis.md` · 主仓库：`/Users/zhenyu.jiang/kvcached` · 对照仓库：`/Users/zhenyu.jiang/sglang`、`/Users/zhenyu.jiang/vllm` · 分析版本 KVCacheD `884108704f44` / SGLang `44ef8fecfe69` / vLLM `dc36fcce902a`

## 一句话定位

[[kvcached]] 不是新的推理引擎，而是插入 [[sglang]] 与 [[vllm]] KV 分配路径的 GPU 虚拟内存层：引擎仍管理 scheduler、prefix metadata、block/token index 和 attention kernel，KVCacheD 则让稳定的虚拟 KV tensor 按需映射/释放真实 VRAM page，使多个引擎实例在同一 GPU 上弹性共享物理显存。

这是一种 [[elastic-kv-cache]]：它不共享跨进程 prefix 内容，也不等同 [[kv-cache-offload]]、MIG、MPS 或 vGPU。当前采用 `.pth + import hook + version-aware monkey patch` 接入，两套上游引擎源码不直接依赖 KVCacheD。

## 核心架构图

```
┌────────────────────────────── Client / Application ──────────────────────────────┐
│ OpenAI API / SGLang Engine / vLLM LLM / controller router                        │
└───────────────────────────────┬───────────────────────────────────────────────────┘
                                │ request / token stream
          ┌─────────────────────┴──────────────────────┐
          ▼                                            ▼
┌──────────────────────────┐                 ┌──────────────────────────┐
│ SGLang runtime           │                 │ vLLM V1 runtime          │
│ Scheduler + RadixCache   │                 │ EngineCore + Scheduler   │
│ token/page allocator     │                 │ KV manager + BlockPool   │
│ ModelRunner + backend    │                 │ GPUModelRunner + backend │
└────────────┬─────────────┘                 └────────────┬─────────────┘
             │ patched allocation/free/tensor creation   │
             └─────────────────────┬──────────────────────┘
                                   ▼
┌────────────────────────── KVCacheD integration layer ─────────────────────────────┐
│ version-aware patches · SGLang/vLLM adapters · layout/geometry validation         │
│ Elastic token/page allocator · ElasticBlockPool · prefix-cache bound              │
└──────────────────────────────────┬────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────── KVCacheD Python control layer ──────────────────────────┐
│ KVCacheManager: block ledger · page affinity · reserve/resize/limit · rollback    │
│ TP/PP IPC: worker listeners · transactional map/unmap · lifecycle cleanup         │
│ observability: /dev/shm records · kvctl/kvtop · pool snapshots                    │
└──────────────────────────────────┬────────────────────────────────────────────────┘
                                   ▼
┌────────────────────────── C++ / GPU VMM data plane ───────────────────────────────┐
│ FTensorAllocator → stable virtual address → torch Tensor view                     │
│ PageAllocator → 2 MiB+ logical pages → physical CUDA/HIP allocation handles       │
│ cuMemAddressReserve/cuMemMap/cuMemUnmap or HIP equivalents                        │
└──────────────────────────────────┬────────────────────────────────────────────────┘
                                   ▼
                    GPU virtual address space ⇄ physical VRAM
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 自动注入与版本适配 | 安装 `.pth`、注册 import hook、按版本应用 SGLang/vLLM patch |
| 引擎语义适配 | 将 SGLang token/page pool 或 vLLM BlockPool 接到 KVCacheManager，并构造原生 backend 期望的 tensor view |
| Python 逻辑分配 | 维护 block ledger、page affinity、回滚、resize、limit、prefix bound 和延迟释放 |
| 多进程一致性 | 经 Unix socket 向 TP/PP worker 广播映射，以 prepare/commit/abort 保证 unmap 一致性 |
| C++ VMM 数据面 | 预留 VA、创建 stable tensor、按 offset 映射 CUDA/HIP physical page、维护 reserve/quarantine 状态 |
| 外部控制 | `/dev/shm` 使用量和 limit、`kvctl`/`kvtop`、可选多模型 router/sleep controller |

## 关键数据流

### 启动与自动注入

```
pip install kvcached
  │
  ├─ build kvcached._C (PyTorch stable ABI + CUDA/HIP VMM)
  └─ install kvcached_autopatch.pth into site-packages
                    │ Python interpreter startup
                    ▼
         import kvcached.autopatch
                    │ register wrapt.when_imported hooks
          ┌─────────┴──────────┐
          ▼                    ▼
     import sglang          import vllm
          │                    │
          ▼                    ▼
 PatchManager("sglang")   PatchManager("vllm")
          │ version range      │ version range
          ▼                    ▼
 replace allocator/pools  replace BlockPool/runner/worker
          └─────────┬──────────┘
                    ▼
 ENABLE_KVCACHED=true 时走 elastic path；否则保留原引擎行为
```

### 逻辑 block 映射为物理 VRAM

```
Engine asks alloc(N logical blocks)
              │
              ▼
KVCacheManager.available_size / _alloc
  │ reuse reserved blocks
  │ choose best-fit partially used InternalPage
  └─ no page available → PageAllocator.alloc_page()
                              │
                    free page or pre-mapped reserved page
                              │ slow path
                              ▼
                    page_id → virtual byte offset
                              │
          ┌───────────────────┴───────────────────┐
          │ same process                          │ TP/PP or remote worker
          ▼                                       ▼
 FTensorAllocator.map(offset)         Unix socket broadcast map(offset)
          │                                       │ each worker
          └───────────────────┬───────────────────┘
                              ▼
        unmap zero page → allocate physical page → cuMemMap/hipMemMap
                              │
                              ▼
 stable Tensor pointer now backed by VRAM; return block ids to engine
                              │
                    attention kernel writes/reads KV
                              │ free / eviction
                              ▼
 block ledger empty for page → reserve briefly or transactional unmap
                              │
                              ▼
 physical handle released; virtual address and Tensor object remain valid
```

`FTensor` 先预留虚拟地址并用 zero page 初始化，然后通过 `torch::stable::from_blob` 暴露 tensor。请求触碰新 page 时，在相同 VA 上换入真实 physical page；释放后重新映回 zero page，所以 tensor 指针不变，原生 attention kernel 不需要了解 KVCacheD。

### SGLang 集成流

```
HTTP / Engine request
        │ tokenize
        ▼
SGLang Scheduler → RadixCache.match_prefix()
        │ hit indices                       │ suffix demand
        │                                   ▼
        │                     ElasticToken/PagedAllocator.alloc()
        │                                   │
        │                                   ▼
        │                         KVCacheManager.alloc()
        │                                   │ maps pages lazily
        └──────────────────┬────────────────┘
                           ▼
ScheduleBatch EXTEND / DECODE / MIXED
                           │
                           ▼
ModelRunner + native attention backend
  reads ElasticMHA/MLA/Mamba pool views over stable VM-backed tensors
                           │
                           ▼
process_batch_result → cache_finished_req / free
        │ cached prefix retained             │ uncached / evicted
        ▼                                    ▼
 RadixCache owns indices            KVCacheManager.free(indices)
        │ bound exceeded                     │ empty page
        └──────────── evict ──────────────────┴─→ VMM unmap
```

[[radix-attention]] 和 Scheduler 保持原生。KVCacheD 主要替换 token/page allocator、MHA/MLA/Mamba/hybrid pool 的 buffer 创建，并给 RadixCache 加物理内存上限。当前每个 SGLang TP worker 本地拥有自己的 pool；真实 TP width 只用于 listener/rank 信息，manager 不把本地分配重复广播给 peer。

### vLLM 集成流

```
API request → EngineCore.step → Scheduler.schedule
                                  │
                         KVCacheManager.allocate_slots
                                  │ native metadata/coordinator
                                  ▼
                         ElasticBlockPool.get_new_blocks
                         │ prefix hit/touch/ref_cnt/LRU
                         │ physical shortage → evict cached blocks
                         ▼
                         KVCacheD KVCacheManager.alloc
                                  │
                                  ▼
                        map page on every worker rank
                                  │ block ids
                                  ▼
SchedulerOutput.req_to_new_blocks → GPUModelRunner.execute_model
                                  │
                                  ▼
native attention backend reads VMM-backed per-layer KV views
                                  │
               finish/preempt     │ APC full block
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
       free physical candidate       retain in elastic prefix LRU
                    │                           │ cap/pressure
                    └───────────────┬───────────┘
                                    ▼
                         ordered worker barrier + unmap
```

[[paged-attention]]、block table、request hash、scheduler 和 backend 仍是原生逻辑。ElasticBlockPool 复制 null block、ref count、APC full-block cache、duplicate hash 和 LRU 契约，但 block id 的物理 backing 由 KVCacheD 提供。共享池竞争造成的 transient miss 被翻译为 `allocate_slots() -> None`，由 vLLM scheduler preempt/retry。

### TP/PP 事务性 unmap

```
Coordinator decides page P can be released
                 │
                 ├─ vLLM queued/async path: worker collective barrier
                 │      ensures earlier GPU batches crossed the fence
                 ▼
transaction id = UUID
                 │ PREPARE(P)
     ┌───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼
 pp0/tp0      pp0/tp1     pp1/tp0     pp1/tp1
 unmap-retain  unmap-retain unmap-retain unmap-retain
 keep physical handles until global decision
     │ prepared   │ prepared   │ prepared   │ prepared
     └───────────┴───────────┬─────────────┘
                             │ COMMIT
                             ▼
                   release retained handles
                             │
             failure before commit → ABORT + restore mapping
             ambiguous commit → idempotent retry; otherwise fail pool
```

Map 失败可回滚新增映射；unmap 若只有部分 rank 成功，会让 block table 在各 GPU 上含义不同，因此使用两阶段事务。commit 结果不明时只能幂等重试 commit；无法确认一致性就 fail pool，而不是继续产生 silent corruption。

### 可选多模型控制器

```
controller/example-config.yaml
        │
        ▼
launch.py → tmux sessions → vLLM and/or SGLang instances
        │                                  │
        └──────────────┬───────────────────┘
                       ▼
             MultiLLMFrontend / LLMRouter
                       │ model name → endpoint
                       ▼
                 OpenAI-compatible proxy
                       │
          TrafficMonitor records activity/rate
                       │ idle threshold
                       ▼
                  SleepManager
          ┌────────────┴────────────┐
          ▼                         ▼
 vLLM /sleep?level=1          SGLang /release_memory_occupation
 vLLM /wake_up                SGLang /resume_memory_occupation
```

控制器解决进程拉起、路由和 idle sleep；核心 VMM 则解决活跃实例的 KV 物理显存弹性。它不是 Kubernetes operator，也不在 request 热路径里决定 page 分配。

## 设计决策与哲学

- **稳定 VA、弹性 backing**：engine 始终持有稳定 tensor，真实 VRAM 按活跃 block/token 映射。
- **适配 storage，不替换 engine**：[[vllm]] 与 [[sglang]] 仍拥有调度、cache metadata、模型执行和 kernel。
- **物理 page 与 engine block 解耦**：默认 VMM page 2 MiB，一个 page 可装多个 engine block；只有整页空闲才能归还 VRAM。
- **把共享容量视为动态状态**：`available_size` 不是 reservation；并发实例可使后续 alloc 失败，失败必须进入 scheduler retry 而非 engine crash。
- **prefix cache 有界**：无限 APC/RadixCache 会 pin 住 physical page，使弹性退化；默认以 cached-token budget 协调命中率与回收能力。
- **一致性优先**：map rollback、quarantine、unmap 2PC 和 queued-batch barrier 都选择 fail-loud，避免 KV silent corruption。
- **零上游改动换来版本耦合**：plugin 安装简单，但上游内部类、签名、layout、runner 变化都要更新 compatibility patch。

## 核心组件深入

### FTensor 与 KVCacheManager

FTensor 把“地址空间”与“物理 page handle”分开；PageAllocator 管 free/reserved/in-use/quarantined page；KVCacheManager 再把 engine block id 分组到 page。manager 使用 page-affine best-fit，避免长请求散落后由少量 prefix block pin 住很多 page，并在物理竞争中对部分分配做来源感知回滚。

contiguous layout 用一次 compound mapping 覆盖所有 layer/K/V，映射少但 per-layer view 有 stride；non-contiguous 每层独立，适合要求独立 region 的 PD/NIXL 或 ROCm backend。CUDA 默认前者，ROCm 默认后者。

### 两套引擎为什么不能共用同一适配器

SGLang 的 Scheduler、token allocator 和 KV pool 共同围绕 token index 工作，替换 allocator/pool 即可覆盖主路径。vLLM V1 的 scheduler-side BlockPool 与 worker-side tensor 分进程，EngineCore 分配 block id 后必须通知所有 GPU worker 映射同一 offset，还要在异步批完成后才能 unmap。因此 vLLM patch 覆盖 EngineCore、coordinator、BlockPool、GPUWorker、GPUModelRunner 和 shutdown。

## 项目关系与边界

| 问题 | 结论 |
|---|---|
| 是否替代推理引擎 | 否；是两套 engine 的 KV memory plugin |
| 是否替代 PagedAttention/RadixAttention | 否；保留 block table/radix tree，只改变 backing allocator |
| 是否共享跨实例 KV 内容 | 否；共享同卡 physical capacity，不共享 cache metadata/data |
| 是否等同 KV offload | 否；核心是 GPU VA ↔ GPU VRAM page，P/D/NIXL只是额外兼容 |
| 是否提供显存安全隔离 | 否；只管理接入的 KV path，不是 MIG/MPS/vGPU sandbox |
| 是否管理模型权重 | 核心不管理；可选 controller 通过 engine sleep API释放更多资源 |

## 集成与验证重点

最小接入需要先安装匹配 backend 的 PyTorch 和 KVCacheD，再同时设置 `ENABLE_KVCACHED=true`、`KVCACHED_AUTOPATCH=1`。日志必须出现 patch 成功信息，并通过 `kvctl list`/`kvtop`、`nvidia-smi` 和固定 seed 请求验证确实进入 elastic path。

生产化应锁定 KVCacheD/engine/PyTorch/GPU backend/attention backend/model 组合，依次验证：单实例正确性、双实例竞争、prefix cache bound、limit 收缩、abort/shutdown、TP、PP、async scheduling、目标 layout/hybrid/quantized path。README 的 tested-up-to 与 HEAD 中新增的更高版本 adapter 不是同一强度的兼容承诺。

不适合采用的情况包括：无法固定和回归 engine 版本；目标 backend/layout 不在 adapter 支持集合；必须使用 KV cache events；需要跨节点 KV 内容共享；需要 hostile multi-tenant 隔离；不能接受 monkey patch 维护成本。

## 知识体系结论

KVCacheD 的价值不是让单次 attention 计算更快，而是把原来“启动时静态占有”的 KV cache 变成“地址稳定、物理按需、跨实例可控”的资源。理解它的关键不是只记住 GPU VMM，而是同时掌握三个 contract：引擎的 block/token/cache 语义、KVCacheD 的 block-to-page ledger，以及多 rank GPU 执行结束前不可 unmap 的生命周期约束。

## 相关页面

- [[kvcached]]
- [[kvcached-source-code-deep-dive]]
- [[sglang]]
- [[vllm]]
- [[elastic-kv-cache]]
- [[gpu-sharing]]
- [[llm-inference]]
- [[paged-attention]]
- [[radix-attention]]
- [[kv-cache-offload]]
