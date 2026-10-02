---
title: KVCacheD、SGLang 与 vLLM 三项目知识体系
tags: [analysis, llm-inference, kv-cache, gpu-virtual-memory, architecture, source-code]
date: 2026-10-02
sources: [src-kvcached-architecture, src-sglang-architecture, src-vllm-architecture]
related: [kvcached, sglang, vllm, elastic-kv-cache, paged-attention, radix-attention, kv-cache-offload, gpu-sharing, llm-inference]
---

# KVCacheD、SGLang 与 vLLM 三项目知识体系

这页是三个项目的关系入口。目标不是把三仓文件逐个罗列，而是建立一套可重复使用的认知结构：先定位每个项目在哪一层，再把同一份请求从 scheduler、逻辑 KV、物理 page 一直追到 GPU VMM，最后理解两条集成路径为什么不同。

源码细节和行号证据集中在 [[src-kvcached-architecture]]；逐函数调用链、对象状态和时序图见 [[kvcached-source-code-deep-dive]]；可执行的安装、验证、压力、故障与升级路径见 [[kvcached-integration-implementation-guide]]；两套引擎自身的完整架构分别见 [[src-sglang-architecture]] 与 [[src-vllm-architecture]]。

## 0. 最先建立的结论

三个项目不是并列竞争关系：

- [[vllm]] 与 [[sglang]] 是同层的推理引擎，负责 API、调度、batch、模型执行、attention 和本地 KV 语义。
- [[kvcached]] 是下插到两套引擎内部的 KV physical-memory plugin，负责稳定虚拟地址和按需 VRAM backing。
- vLLM/SGLang 可以不用 KVCacheD 独立运行；KVCacheD 不能脱离引擎独立完成 LLM serving。
- KVCacheD 让两个实例共享的是 GPU physical capacity，不是同一份 KV 内容、同一棵 radix tree 或同一张 block table。

```text
                         同层竞争/选型
                  ┌─────────────────────┐
                  │ vLLM       SGLang   │
                  │ block       token   │
                  │ table       radix   │
                  └──────────┬──────────┘
                             │ allocator/tensor seam
                             ▼
                         KVCacheD
                 logical block → VMM page → VRAM
                             │
                             ▼
                     CUDA / HIP / GPU driver
```

## 1. 知识树

```text
LLM inference memory system
├─ Request execution
│  ├─ prefill / decode / continuous batching
│  ├─ scheduler / admission / preemption
│  └─ TP / PP / async execution lifetime
├─ Engine KV semantics
│  ├─ vLLM: Request → KVCacheManager → Coordinator → BlockPool → block table
│  └─ SGLang: Req → RadixCache → token allocator → KV pool → req_to_token
├─ Prefix reuse
│  ├─ vLLM APC: fixed logical blocks + hashes + ref count/LRU
│  └─ SGLang RadixCache: token/page-aligned radix nodes + lock_ref/eviction
├─ KVCacheD adaptation
│  ├─ .pth / import hook / version-aware patch
│  ├─ ElasticBlockPool or ElasticToken/PagedAllocator
│  └─ VMM-backed tensor shape/stride adapters
├─ Elastic physical memory
│  ├─ KVCacheManager block ledger
│  ├─ PageAllocator free/reserved/in-use/quarantined pages
│  └─ FTensorAllocator VA reservation + physical map/unmap
└─ Distributed correctness and operations
   ├─ TP/PP worker IPC + transactional unmap
   ├─ async release barrier
   ├─ /dev/shm limit + kvctl/kvtop
   └─ compatibility, failure recovery and shutdown cleanup
```

沿这棵树学习，可以避免两个常见误区：把 KVCacheD page 当成 PagedAttention block；把 elastic memory 当成跨节点 KV offload。

## 2. 三个项目各自解决什么

### vLLM：block-oriented serving engine

核心对象链：

```text
API / LLM
  → EngineCore
  → Scheduler
  → KVCacheManager
  → KVCacheCoordinator / single-type managers
  → BlockPool
  → SchedulerOutput block tables
  → GPUModelRunner
  → attention backend
```

vLLM 的 KV 语义围绕 fixed-size logical block：Request 预先计算 prefix block hashes；BlockPool 管 block object、free queue、ref count、cache hash 和 null block；KVCacheManager/Coordinator 为不同 KV group 分配 block；GPUModelRunner 将 block table 绑定到实际 per-layer KV tensor。

它擅长把 request scheduling、continuous batching、PagedAttention、多个 attention backend 和广泛模型生态组合成通用 serving baseline。KVCacheD 不改变这些核心对象，只把 BlockPool 的 block id 接到动态物理页，并替换 worker tensor allocation。

### SGLang：token/radix-oriented serving runtime

核心对象链：

```text
HTTP / Engine / DSL
  → TokenizerManager
  → Scheduler
  → ScheduleBatch
  → RadixCache.match_prefix
  → TokenToKVPoolAllocator / PagedTokenToKVPoolAllocator
  → MHA/MLA/Mamba/Hybrid KV pool
  → ModelRunner / attention backend
  → DetokenizerManager
```

SGLang 的 KV 语义围绕 token slot 和 RadixCache：radix node 的 value 指向 token-to-KV pool index，prefix match 可在 token 或 page-aligned 边界复用；allocator 为 extend/decode 分配位置；KV pool 保存每层真实 K/V 或 recurrent state。

它的差异化能力是 token-level prefix reuse、复杂生成程序、丰富 speculative/disaggregation/backend 组合。KVCacheD 保留 radix tree 与 scheduler，只替换 allocator 和底层 buffer。

### KVCacheD：physical backing and elasticity layer

核心对象链：

```text
engine alloc/free
  → engine adapter
  → KVCacheManager
  → InternalPage / PageAllocator
  → FTensorAllocator / FTensor
  → CUDA/HIP VMM
```

它解决的是“逻辑 KV 容量很大，但平均真实活跃量较小”时的静态显存浪费。虚拟 tensor 可以覆盖 engine 计划的完整 KV 容量；physical page 只随活跃 block 映射。多个进程通过 GPU driver 的全设备 free memory 和 shared limit 协作竞争。

## 3. 同一个词在三个项目中的不同含义

| 词 | vLLM | SGLang | KVCacheD |
|---|---|---|---|
| Request | `Request` 状态、token、hash、computed tokens | `Req`、prefix、output、radix node | 不理解请求语义，只接收 block/token allocation |
| Block/Page | KV logical block，进入 block table | token page，page_size可为1或更大 | VMM physical page，默认2 MiB |
| Pool | BlockPool + KV groups | token allocator + KV pool | device-wide physical headroom + per-instance page ledger |
| Cache | APC full-block cache | RadixCache prefix tree | 不创建新 prefix 算法，只给两者设 memory bound |
| Capacity | num_gpu_blocks / KV config | max tokens/pages | virtual、logical、mapped、physical headroom四种容量 |
| Free | block进入free queue，可能仍缓存 | token index被allocator回收 | page内全部block释放后才可能unmap |
| Layout | backend-specific KV tensor shape | MHA/MLA/Mamba pool shape | contiguous compound或per-layer FTensor映射 |

阅读源码时必须先判断当前代码谈的是哪一层的 block/page/free。

## 4. 对象映射：KVCacheD 替换了什么

| 生命周期位置 | vLLM 原生对象 | KVCacheD 接管方式 | SGLang 原生对象 | KVCacheD 接管方式 |
|---|---|---|---|---|
| 启动容量 | `Worker.determine_available_memory` | 改为进程本地 virtual budget，避免 whole-device delta被邻居干扰 | `KVCacheConfigurator._profile_available_bytes` | 用 `total × mem_fraction - process reserved`，rank间取min |
| 逻辑 allocator | `BlockPool` | `ElasticBlockPool` 复制 block/APC contract，id来自KVCacheManager | token/paged allocator | 动态类替换，alloc/free委托KVCacheManager |
| KV tensor | GPUModelRunner allocation/reshape | 创建raw FTensor，再按backend shape/stride构造view并bind | MHA/MLA/Mamba/hybrid pool | 跳过原生真实buffer，建立VMM-backed view |
| prefix metadata | block hash/cache/ref count | 保留并加bounded LRU/page-aware eviction | RadixCache/tree node/lock_ref | 保留并在完成插入后限制evictable tokens |
| 分配失败 | native free count通常权威，异常视为bug | shared headroom race转成`allocate_slots=None` | allocator返回None/evict/retry | 保持SGLang原有allocation miss语义 |
| 多rank map | worker拥有tensor | coordinator通过socket fan-out | 每worker本地pool | 当前不广播本地pool操作 |
| 物理释放 | native tensor常驻 | queued batch fence + transactional unmap | native tensor常驻 | 本地page空闲后unmap |
| shutdown | engine/worker teardown | stop listener、pool shutdown、unlink segment | scheduler/worker teardown | stop listener和allocator |

## 5. 一次请求的完整生命周期

### vLLM + KVCacheD

1. API 层生成 `Request`，计算 token 和 prefix block hashes。
2. `EngineCore.step()` 调 Scheduler；scheduler 查询 computed/cached blocks。
3. `KVCacheManager.allocate_slots()` 进入 coordinator/BlockPool。
4. ElasticBlockPool 先复用 APC hit；缺块时调用 KVCacheD manager。
5. manager 检查 logical slots 与 device physical pages，选择已有 page 或申请新 page。
6. 新 page offset 经 Unix socket 发到相关 TP/PP worker；每个 worker 在本地 FTensor 相同 offset map 物理 handle。
7. block ids 写入 SchedulerOutput；GPUModelRunner 更新 block table。
8. 原生 attention backend 通过稳定 tensor pointer 和 block table 写/读 KV。
9. 请求结束时 partial/uncached block立即free；full cached block ref降到0后留在ElasticBlockPool LRU。
10. cache bound或物理压力触发evict；page所有block都free后进入reserve或unmap。
11. async/PP队列存在时，先做worker collective barrier，再执行transactional unmap。

### SGLang + KVCacheD

1. TokenizerManager 创建 tokenized request，Scheduler 收到 `Req`。
2. RadixCache longest-prefix match 返回已缓存 token-slot indices。
3. extend/decode 对未命中 suffix 请求 token/page slots。
4. Elastic allocator 将 token需求换成 KVCacheManager block需求；paged path再把block id展开为token indices。
5. KVCacheManager 在本 worker 的 FTensor map physical page。
6. ScheduleBatch 仍以 EXTEND/DECODE/MIXED 方式执行；ModelRunner 和 backend不感知VMM。
7. 完成时 RadixCache 插入新 prefix并持有indices；未缓存indices返回allocator。
8. cached-token bound超限时，RadixCache原生evict释放indices。
9. page全部空闲后保留少量reserve或unmap。

## 6. prefix cache：三层所有权

prefix cache 不是一个单独组件，而是三层状态同时成立：

```text
Prefix identity and lookup
  vLLM block hash / SGLang radix key
                │ owns logical IDs
                ▼
Engine block/token metadata
  ref count · lock_ref · LRU/eviction
                │ IDs reference pages
                ▼
KVCacheD physical backing
  page occupancy · mapped handle · reclaimability
```

上层 cache hit 不会因为 KVCacheD 自动消失；下层也不能在 metadata 仍引用 block 时擅自 unmap。bounded prefix cache 是两层策略的结合点。

## 7. 多进程所有权模型

### vLLM ownership

```text
EngineCore process
  owns scheduler-side logical block allocation
  owns KVCacheD manager / shared page decision
             │ map/unmap commands
             ▼
GPU worker processes (TP × PP)
  own local CUDA context and FTensor mapping
  must apply same logical offset transition
```

因此 vLLM 需要 worker listeners、PP namespace、transaction id、async batch fence。manager 的 decision 与 worker 的 CUDA context 分离，是复杂性的根因。

### SGLang ownership

```text
SGLang scheduler/worker rank
  owns local token allocator
  owns local KV pool tensor
  owns local KVCacheD manager and mapping
```

每个 TP worker 处理本 rank 的本地 pool，不能把本地 page operation 再广播给 peers，否则会重复/错误操作不同 ownership 的 pool。

## 8. GPU VMM 状态机

```text
virtual range reserved
        │ initialize
        ▼
zero-page mapped
        │ alloc logical blocks needs backing
        ▼
physical page mapped ── free but reserve budget ──► reserved mapped page
        │ all blocks free and no reserve need               │ reuse
        ▼                                                   └──────┐
unmap-retain (distributed prepare)                                │
        │ commit                         │ abort                    │
        ▼                                ▼                          │
physical handle released          physical mapping restored ◄─────┘

any partial/rollback uncertainty → quarantined / failed pool
```

zero page 的作用是让尚未真实 backing 的地址仍保持有效映射，但它不是可写入实际 KV 的容量替代。真正使用前必须 map physical page。

## 9. Layout 与模型类型

### MHA/GQA

每层通常有 K 与 V 两个 buffer。non-contiguous 可以在每层 FTensor 前后半区存 K/V；contiguous 把 token/page、layer、K/V interleave 在同一 reservation，再用 stride暴露每层view。

### MLA

K/V 往往组合为单一 latent buffer，`num_kv_buffers=1`。FTensor大小和VMM page需要额外对齐，不能套用普通MHA的K/V split。

### Hybrid attention / sliding window

多个KV group可能共享BlockPool，但每组有不同attention rule；只要物理block bytes统一，可以为不同geometry建立不同view。hash还必须带group id，避免相同prefix在不同group碰撞。

### Mamba / linear attention

状态不再只是K/V，而是conv和temporal/SSM state。KVCacheD将一个slot的多类state打包成super-cell，或在vLLM hybrid unified pool中给同一physical bytes建立attention与mamba两种解释。cell/page和partial-tail处理是correctness关键。

## 10. 与其它项目层的关系

| 层 | 项目/概念 | 与三项目体系的关系 |
|---|---|---|
| Engine | [[vllm]], [[sglang]] | 本页两套上层运行时 |
| Elastic KV backing | [[kvcached]], [[elastic-kv-cache]] | 同卡physical KV弹性 |
| KV offload/transfer | [[kv-cache-offload]], Dynamo/NIXL/connector | 跨memory tier或P/D节点传输KV内容 |
| Routing | [[inference-routing]], llm-d KV index | 根据endpoint负载/KV locality选择实例 |
| GPU sharing | [[gpu-sharing]]、MIG/MPS/HAMi | 更外层的设备分配、执行/内存隔离 |
| Serving control plane | llm-d/AIBrix/KServe等 | 部署、扩缩、endpoint选择和生命周期 |

KVCacheD 可以与这些层组合，但不能替代它们。尤其是“同卡物理页弹性”和“跨节点 KV transfer”经常都叫 KV cache management，实际数据路径和故障模型完全不同。

## 11. 采用时的决策框架

### 最佳匹配

- 多模型权重可同时驻留，KV峰值错开。
- 工作负载有明显idle/突发周期。
- 静态`gpu_memory_utilization`切分导致活跃模型容量不足、空闲模型浪费。
- 团队可以维护固定engine版本和GPU测试矩阵。

### 避免条件

- 单实例持续满载，没有可回收的KV空闲期。
- 目标是跨实例复用同一prefix KV，或远端KV持久化。
- 目标backend/layout/quantized format未被适配器明确支持。
- 必须依赖KV cache events，而当前ElasticBlockPool不支持。
- 多租户要求硬隔离或强资源quota。

### 采用成本

| 成本 | 内容 |
|---|---|
| 版本成本 | 上游内部API变化需要更新patch |
| 测试成本 | model × backend × layout × TP/PP × cache × engine version矩阵 |
| 运维成本 | `/dev/shm`、worker socket、IPC timeout、shutdown cleanup |
| 性能成本 | 首次map、IPC、transactional unmap、少量reserve footprint |
| 正确性成本 | stride/layout、async lifetime、partial allocation rollback |

## 12. 学习路径

### 路线 A：先理解关系

1. 本页的 0–4 节。
2. [[vllm]] 和 [[sglang]] 实体页，建立引擎差异。
3. [[elastic-kv-cache]]，掌握四类容量和两级分页。
4. [[src-kvcached-architecture]] 的核心架构图、关键数据流和项目关系。

### 路线 B：追一条源码热路径

1. KVCacheD `autopatch.py` / `patch_base.py`。
2. 任选 vLLM `ElasticBlockPool.get_new_blocks` 或 SGLang `ElasticTokenToKVPoolAllocator.alloc`。
3. `KVCacheManager._alloc`。
4. `PageAllocator.alloc_page/map_pages`。
5. `FTensorAllocator.map_to_kv_tensors_with_result` 与 `FTensor::map`。
6. 反向追 `free → empty page → unmap`。

### 路线 C：专攻正确性

1. page geometry validation。
2. partial alloc rollback 与 MapQuarantinedError。
3. TP/PP prepare/commit/abort unmap。
4. vLLM queued/async release barrier。
5. manager/tensor capacity guard、null block、hybrid group hash。
6. shutdown drain 与 segment/socket cleanup tests。

### 路线 D：专攻集成

1. SGLang allocator/pool class alias 与版本范围。
2. vLLM EngineCore/coordinator/worker/runner 四个进程边界。
3. MHA → MLA → hybrid → Mamba，逐级增加geometry复杂度。
4. contiguous vs non-contiguous、CUDA vs ROCm。
5. APC/RadixCache bound、NIXL/P-D smoke path。

## 13. 快速自测问题

- vLLM block id、SGLang token index 和 KVCacheD page id 是否一一对应？为什么？
- logical free blocks 很多时，为什么 physical allocation 仍会失败？
- 为什么一个 cached block 可能阻止整张 2 MiB page 回收？
- FTensor unmap 后为什么 tensor 对象仍存在？
- vLLM allocation miss 为什么要转成 `None`，而状态不一致必须抛错？
- SGLang 为什么保留 RadixCache而只替换allocator/pool？
- vLLM为什么必须在EngineCore和GPU worker两侧都patch？
- transactional unmap 的prepare阶段保留了什么？
- contiguous layout的compound page如何改变offset计算？
- KVCacheD为什么不是KV offload，也不是通用GPU隔离方案？

如果这些问题都能从对象所有权、逻辑/物理分层和生命周期三个角度回答，三个项目之间的关系就已经形成稳定知识结构。

## 相关入口

- 主源码分析：[[src-kvcached-architecture]]
- 逐函数源码深潜：[[kvcached-source-code-deep-dive]]
- 集成与实验手册：[[kvcached-integration-implementation-guide]]
- KVCacheD：[[kvcached]]
- 引擎：[[vllm]]、[[sglang]]
- 核心概念：[[elastic-kv-cache]]
- 引擎缓存：[[paged-attention]]、[[radix-attention]]
- 相邻系统：[[kv-cache-offload]]、[[gpu-sharing]]、[[llm-inference]]
