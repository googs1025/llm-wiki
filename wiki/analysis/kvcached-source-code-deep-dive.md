---
title: KVCacheD × SGLang × vLLM 源码深潜
tags: [analysis, source-code, llm-inference, kv-cache, gpu-virtual-memory, architecture]
date: 2026-10-02
sources: [src-kvcached-architecture, src-sglang-architecture, src-vllm-architecture]
related: [kvcached, sglang, vllm, elastic-kv-cache, kvcached-sglang-vllm-knowledge-system, paged-attention, radix-attention]
---

# KVCacheD × SGLang × vLLM 源码深潜

本页专门回答“代码具体怎么跑”。关系与概念先读 [[kvcached-sglang-vllm-knowledge-system]]；完整原始分析与兼容矩阵见 [[src-kvcached-architecture]]。本页所有路径基于以下本地快照：

需要把调用链落到实际部署、实验和升级验证时，继续阅读 [[kvcached-integration-implementation-guide]]。

| 仓库 | HEAD | 角色 |
|---|---|---|
| `/Users/zhenyu.jiang/kvcached` | `884108704f44` | GPU VMM、逻辑页管理、engine patches |
| `/Users/zhenyu.jiang/sglang` | `44ef8fecfe69` | token/radix-oriented inference engine |
| `/Users/zhenyu.jiang/vllm` | `dc36fcce902a` | block-oriented inference engine |

## 1. 源码总架构

```text
┌──────────────────────── Engine source trees ─────────────────────────┐
│ SGLang                                  vLLM                         │
│ scheduler.py                            engine/core.py                │
│ mem_cache/allocator/*                   core/kv_cache_manager.py      │
│ mem_cache/memory_pool.py                core/kv_cache_coordinator.py  │
│ mem_cache/radix_cache.py                core/block_pool.py            │
│ model_executor/*                        worker/gpu_model_runner.py    │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ monkey-patched seams
┌───────────────────────────▼───────────────────────────────────────────┐
│ kvcached/integration                                                │
│ patch_base.py · version_utils.py · sglang/* · vllm/*                │
│                                                                     │
│ logical engine object ←→ KVCacheManager block API ←→ tensor views   │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ Python/C++ binding
┌───────────────────────────▼───────────────────────────────────────────┐
│ kvcached core                                                       │
│ kv_cache_manager.py · tp_ipc_util.py · vmm_ops.py                   │
│ pool_registry.py · observability.py · mem_info_tracker.py           │
└───────────────────────────┬───────────────────────────────────────────┘
                            │ torch custom ops / pybind
┌───────────────────────────▼───────────────────────────────────────────┐
│ C++ VMM data plane                                                  │
│ torch_bindings.cpp → allocator.cpp → ftensor.cpp                    │
│                     → page_allocator.cpp → gpu_vmm.hpp              │
└───────────────────────────┬───────────────────────────────────────────┘
                            ▼
                  CUDA Driver API / HIP VMM
```

源码阅读时沿纵向追一条调用链，不要同时横向展开三仓所有模块。核心 seam 只有两个：

1. engine 的 logical allocator：SGLang token/page allocator 或 vLLM BlockPool。
2. engine 的 physical KV tensor creation：SGLang memory pool buffer 或 vLLM GPUModelRunner KV tensors。

## 2. 自动注入：补丁如何在 engine import 前生效

### 2.1 安装期

入口文件：

- `kvcached/setup.py`
- `kvcached/kvcached_autopatch.pth`
- `kvcached/kvcached/autopatch.py`

`setup.py` 做两件重要的事：

1. 以 PyTorch C++ stable ABI 构建 `kvcached._C`。CUDA build 链接 `libcuda` 以获得 `cuMem*`；HIP build 使用 `CppExtension + amdhip64`，避免 torch hipify 破坏已有的 backend abstraction。
2. 把 `kvcached_autopatch.pth` 放在 site-packages 根目录。Python 启动时 `site` 模块执行 `.pth` 中的 import，因此补丁注册发生在用户显式 import vLLM/SGLang 之前。

### 2.2 启动时序

```text
Python          .pth/autopatch       wrapt importer      engine package      PatchManager
  │                    │                   │                    │                  │
  │ interpreter start  │                   │                    │                  │
  ├───────────────────►│                   │                    │                  │
  │                    │ import autopatch  │                    │                  │
  │                    ├──────────────────►│ register hooks     │                  │
  │                    │                   │                    │                  │
  │ user imports vllm/sglang               │                    │                  │
  ├───────────────────────────────────────►│                    │                  │
  │                    │                   ├───────────────────►│ load package     │
  │                    │                   │ hook fires         │                  │
  │                    │                   ├──────────────────────────────────────►│
  │                    │                   │                    │  detect version   │
  │                    │                   │                    │  import targets   │
  │                    │                   │                    │  apply patches    │
  │                    │                   │◄──────────────────────────────────────┤
  │ engine import completes with patched aliases/classes           results log   │
  │◄──────────────────────────────────────┤                    │                  │
```

`kvcached/autopatch.py:6-19` 只是 import 两个 engine-specific autopatch module；异常被吞掉是为了没安装某个 engine 时不影响另一个。真正是否启用由 engine autopatch 中的 `KVCACHED_AUTOPATCH` 检查决定。

### 2.3 PatchManager 的执行模型

`integration/patch_base.py` 定义：

- `BasePatch`：声明 `library`、`target_module`、`target_class`、`patch_name`，并提供 patch marker 幂等检查。
- `PatchManager.register_patch`：保存 patch 与 version range。
- `apply_all_patches`：检测 engine version、按 range 跳过不兼容 patch、动态 import `target_module`、调用 `apply()`。
- `VersionManager/VersionRange`：隔离跨版本签名和模块位置差异。

Patch marker 是必要的，因为 import hook、测试 reload 或多条引用链都可能重复触发；没有幂等标记会发生 wrapper 套 wrapper、重复 listener 或 alias 漂移。

## 3. Python/C++ API 边界

### 3.1 Python 暴露的 VMM 操作

`kvcached/vmm_ops.py` 把 C++ 接口分成两类：

| Python 名称 | 实现通道 | 作用 |
|---|---|---|
| `init_kvcached` | `torch.ops.kvcached` | 初始化全局 FTensorAllocator |
| `create_kv_tensors` | `torch.ops.kvcached` | reserve VA 并返回 torch tensor |
| `kv_tensors_created` | `torch.ops.kvcached` | manager 后台初始化同步 |
| `map_to_kv_tensors` | `torch.ops.kvcached` | 映射 logical offsets |
| `unmap_from_kv_tensors` | `torch.ops.kvcached` | 单进程直接解除映射 |
| transactional map/unmap | pybind `_C` | 返回新增offset或持有transaction state |
| `PageAllocator`/`InternalPage` | pybind `_C` | Python manager直接操作C++对象 |

为何混用 custom ops 与 pybind：tensor 参数和 stable ABI 操作适合注册到 `torch.ops`；不接 tensor、需要返回 C++ class/复杂 transaction 结果的接口保留 pybind。

### 3.2 Tensor 创建调用链

```text
engine adapter alloc_kv_cache(...)
  → kvcached.vmm_ops.create_kv_tensors
  → torch binding create_kv_tensors
  → FTensorAllocator::create_kv_tensors
      ├─ align requested bytes to kPageSize
      ├─ choose per-layer or contiguous layout
      ├─ construct zero page / compound zero page
      └─ FTensor(name, size, dtype, device)
          ├─ alloc_virtual_mem(device, size)
          ├─ init_with_zero_()
          └─ torch::stable::from_blob(vaddr, sizes, strides, device, dtype)
  → raw flat tensor(s)
  → adapter uses view/as_strided/permute
  → engine receives native expected KV shape
```

`FTensor` 是实现的核心。`from_blob` 不分配第二份 storage；它把预留的 GPU virtual address 当作 tensor storage。tensor 的可寻址范围大，不代表相同大小的 VRAM 已分配。

## 4. C++ VMM 数据结构

### 4.1 FTensorAllocator

文件：`csrc/allocator.cpp`、`csrc/inc/allocator.hpp`。

主要状态：

- static `g_allocators_`：按 `group_id` 保存 allocator；group 0 在 init 创建，其余 hybrid group 懒创建。
- `ftensors_`：non-contiguous layout 下每层一个 FTensor。
- `contiguous_kv_tensor_`：contiguous layout 下单一大 FTensor。
- `zero_page_`：尚未backing或解除backing后的安全映射。
- `pending_unmap_`、`finalized_unmap_transactions_`：分布式unmap幂等状态。

`create_kv_tensors` 的 layout 分支：

```text
non-contiguous
  layer0 FTensor: [K region | V region]
  layer1 FTensor: [K region | V region]
  ...
  one logical page offset maps one page in every layer and K/V target

contiguous
  one FTensor: [block/page major][layer][K/V][payload]
  one compound physical mapping covers num_layers × num_kv_buffers
```

### 4.2 FTensor

文件：`csrc/ftensor.cpp`、`csrc/inc/ftensor.hpp`。

一个 FTensor 保存：

- `vaddr_`：稳定 virtual base address。
- `size_`、`page_size_`、dtype/device。
- `tensor_`：from_blob 创建的稳定 view。
- `mapping_`：page_id → physical `Page` handle。
- `failed_pages_`：rollback/释放不确定时保留handle，避免错误复用。

### 4.3 map 状态转换

```text
FTensor::map(offset)
  → validate offset alignment/range
  → reject if mapping_ already owns page_id
  → GPU: unmap zero page at target VA
  → make_unique_page(device, page_id, page_size)
  → physical Page::map(target VA)
  → mapping_[page_id] = handle

failure:
  if physical map happened → unmap it
  remap zero page
  release physical handle
  any rollback failure → retain failed handle + state consistency error
```

### 4.4 unmap 状态转换

```text
FTensor::unmap_retain_(offset)
  → validate currently mapped
  → cuMemUnmap physical mapping
  → map zero page back to same VA
  → move physical handle out of mapping_
  → caller decides:
       direct unmap: handle.release()
       transaction prepare: keep handle in PendingUnmapTransaction
       abort: map retained handle back
       commit: release retained handle
```

“先重新映 zero page，再释放 handle”的顺序避免 VA 留下未映射洞，也让 rollback 有明确恢复点。

## 5. PageAllocator 与 KVCacheManager

### 5.1 C++ PageAllocator 状态

文件：`csrc/page_allocator.cpp`。

```text
free_page_list
  logical page IDs with no physical backing
        │ alloc slow path + map
        ▼
in-use page
        │ all blocks free
        ├─ reserve pool below max ──► reserved_page_list (still mapped)
        │                              │ alloc fast path
        │                              └──────────────► in-use
        └─ reserve pool full ───────► unmap ──► free_page_list

map rollback uncertain ─────────────► quarantined_pages
state consistency unknown ──────────► transaction_failed (pool rejects work)
```

constructor 根据 `mem_size_per_layer / page_size` 建 logical page id 空间，并创建 `MemInfoTracker`。`alloc_page()` 优先从 `reserved_page_list_` 取，避免map latency；slow path从free list取后调用`map_pages()`。`free_pages()`保留一部分mapped reserve，其余批量unmap。

### 5.2 Python KVCacheManager 状态

文件：`kvcached/kv_cache_manager.py`。

| 状态 | 内容 |
|---|---|
| `avail_pages` | 已mapped、有free blocks的InternalPage |
| `full_pages` | 已mapped、没有free block的InternalPage |
| `num_avail_blocks` | 仅统计avail_pages中的free block |
| `reserved_blocks` | resize/reserve逻辑中暂不参与普通allocation的block |
| `null_block` | SGLang/vLLM padding/null contract要求保留的block 0 |
| `retired_pages` | logical free但等待GPU batch fence才能unmap的page |
| memory-limit fields | limit revision、effective bytes、shrink target |

### 5.3 alloc 详细流程

```text
KVCacheManager.alloc(need_size)
  → _wait_post_init(): tensor必须已在worker创建
  → observe PageAllocator resize target
  → available_size() >= need_size ?
      ├─ no  → return None
      └─ yes
  → first consume reserved_blocks
  → while remaining > 0
      ├─ avail_pages non-empty
      │    → _pick_avail_page(remaining)
      │       exact/best fit first; otherwiselargest partial page
      └─ no avail page
           → PageAllocator.alloc_page()
           → InternalPage.init(block_mem_size)
           → map physical page if slow path
  → InternalPage.alloc(k)
  → move page to full_pages or avail_pages
  → return exactly need_size block IDs

alloc_page failure after partial work
  → page-derived IDs go through free()
  → reserved-derived IDs prepend back to reserved ledger
  → return None
```

`_pick_avail_page` 是page-affine关键：能容纳完整remaining run时选最小合适page，不能时选free最多的page。它试图让一个request的blocks集中，减少prefix cache pin住多页的概率。

### 5.4 free 详细流程

```text
KVCacheManager.free(block_ids)
  → group block IDs by physical page
  → locate page in full_pages/avail_pages
  → InternalPage.free_batch(ids)
  → page still occupied
      └─ keep in avail_pages
  → page empty
      ├─ defer_physical_release
      │    └─ append (epoch, page_ids) to retired_pages
      └─ immediate
           └─ PageAllocator.free_pages
                ├─ retain mapped reserve pages
                └─ transactional/direct unmap remainder
```

逻辑free与物理release是分开的。即便request释放了block，page内其它request/prefix仍可能占用；即便整页空了，reserve pool或async fence也可能暂时保留physical mapping。

## 6. SGLang 源码接入

### 6.1 原生对象

关键上游文件：

- `sglang/python/sglang/srt/managers/scheduler.py`
- `sglang/python/sglang/srt/mem_cache/allocator/base.py`
- `.../allocator/token.py`
- `.../allocator/paged.py`
- `sglang/python/sglang/srt/mem_cache/memory_pool.py`
- `sglang/python/sglang/srt/mem_cache/radix_cache.py`
- `sglang/python/sglang/srt/mem_cache/kv_cache_configurator.py`

原生调用关系：

```text
Scheduler.run_event_loop
  → get_next_batch_to_run
  → RadixCache.match_prefix
  → allocation helpers
      → TokenToKVPoolAllocator.alloc
      or PagedTokenToKVPoolAllocator.alloc_extend/alloc_decode
  → ScheduleBatch
  → run_batch / ModelRunner
  → process_batch_result
  → RadixCache.cache_finished_req or allocator.free
```

### 6.2 patch 注册清单

`integration/sglang/autopatch.py` 注册顺序是有语义的：

1. `ElasticAllocatorPatch`
2. `ElasticSWAAllocatorPatch`
3. `ElasticMemoryPoolPatch`
4. `ElasticMLAMemoryPoolPatch`
5. `ElasticMambaPoolPatch`
6. `ElasticHybridLinearKVPoolPatch`
7. legacy/current virtual capacity patch
8. Scheduler memory leak patch
9. RadixCache limit patch

allocator和pool alias必须先于捕获这些class alias的capacity owner模块；否则目标模块在import时已经把原生class保存到module global，后续只改package alias无法生效。

### 6.3 SGLang 初始化时序

```text
SGLang import      KVCacheD hook     allocator module     memory_pool module       worker rank
     │                  │                  │                       │                    │
     ├─────────────────►│                  │                       │                    │
     │                  ├─────────────────►│ inject Elastic classes│                    │
     │                  │◄─────────────────┤ alias public names     │                    │
     │                  ├─────────────────────────────────────────►│ inject pool classes│
     │                  │◄─────────────────────────────────────────┤ alias pool names   │
     │                  │                  │                       │                    │
     │ Scheduler/model pool construction                          │                    │
     ├────────────────────────────────────────────────────────────►│                    │
     │                  │                  │                       ├───────────────────►│
     │                  │                  │                       │ init_kvcached      │
     │                  │                  │                       │ alloc virtual tensor
     │                  │                  │                       │ create local manager
     │                  │                  │◄──────────────────────┤ attach allocator   │
```

### 6.4 Elastic token allocator

`ElasticTokenToKVPoolAllocator` 继承 `BaseTokenToKVPoolAllocator`，但不维护原生free tensor：

- `available_size()` → `min(manager.available_size(), self.size)`。
- `alloc(n)` → manager返回Python block/token IDs，再转GPU int64 tensor。
- `free(indices)` → 根据SGLang free-group语义立即free或延迟到group end。
- `clear()` → manager.clear并重置free group。

page_size > 1 时，ElasticPaged allocator把manager block id视作SGLang page id：

```text
manager block IDs [4, 9], SGLang page_size = 4
  → token indices [16,17,18,19, 36,37,38,39]
```

extend/decode location计算仍复用SGLang原生kernel，KVCacheD只供应新page ids。

### 6.5 Elastic MHA/MLA pool

原生 `MHATokenToKVPool` 会创建每层 K/V torch buffer。elastic subclass 跳过这段allocation，调用：

```text
sglang.interfaces.init_kvcached
  → vmm_ops.init_kvcached(device, PAGE_SIZE, layout)

sglang.interfaces.alloc_kv_cache(shape, dtype, device, layers, page_size, type)
  → compute bytes per engine block
  → reserve virtual bytes per layer
  → create_kv_tensors
  → build K/V or MLA views

sglang.interfaces.get_kv_cache_manager(...)
  → world_size=1 local manager
  → reserve_null_block=True
  → attach as pool.kvcached_allocator
```

`world_size=1` 是刻意选择：每个SGLang TP worker的pool/tensor由本rank拥有，本地map只改变本rank，不做vLLM式coordinator fan-out。

### 6.6 Mamba super-cell

`alloc_mamba_states` 把一个slot的多种state布局为：

```text
slot cell
┌──────────────┬──────────────┬───────────────┐
│ conv state 0 │ conv state 1 │ temporal/SSM  │
└──────────────┴──────────────┴───────────────┘
```

每种state按dtype itemsize对齐，整个cell再pad到`PAGE_SIZE`的最小可用因数。原因是InternalPage只交付完整block；若cell不能整除page，会出现跨页block被跳过、manager却按`num_slots`高估容量。

### 6.7 RadixCache bound

KVCacheD 不重写 `match_prefix/insert/evict`。`RadixCacheLimitPatch` 只包装 `cache_finished_req`：

```text
original cache_finished_req(req)
  → radix tree owns finished token indices
  → excess = evictable_size - MAX_CACHED_TOKENS
  → if excess > 0: call native RadixCache.evict(excess)
  → native allocator.free(indices)
  → elastic allocator → KVCacheManager.free
```

## 7. vLLM 源码接入

### 7.1 原生对象

关键上游文件：

- `vllm/v1/engine/core.py`
- `vllm/v1/core/kv_cache_manager.py`
- `vllm/v1/core/kv_cache_coordinator.py`
- `vllm/v1/core/single_type_kv_cache_manager.py`
- `vllm/v1/core/block_pool.py`
- `vllm/v1/worker/gpu_worker.py`
- `vllm/v1/worker/gpu_model_runner.py`

原生调用关系：

```text
EngineCore.step
  → Scheduler.schedule
  → KVCacheManager.allocate_slots
  → KVCacheCoordinator / specialized managers
  → BlockPool.get_new_blocks / touch / free_blocks
  → SchedulerOutput
  → model_executor.execute_model
  → GPUModelRunner.execute_model
  → attention backend using block table + KV tensors
```

### 7.2 patch 覆盖面

`integration/vllm/autopatch.py` 注册的关键patch：

- `ElasticBlockPoolPatch`
- `EngineCorePatch`、`MPClientPatch`、`CoreEngineProcManagerPatch`
- `GPUModelRunnerPatch`，以及0.28/0.29 MRV2专用patch
- `GPUWorkerPatch`
- `HybridBlockSizeAlignPatch`
- `KVCacheCoordinatorPatch` 或旧版 `KVCacheManagerPatch`
- `KVCacheManagerAllocateSlotsPatch`
- Mamba tail、Triton scale、NIXL compatibility patches

vLLM patch更多，不是因为VMM机制不同，而是 scheduler-side block ownership 与 worker-side CUDA mapping 分离。

### 7.3 vLLM 初始化时序

```text
EngineCore         KVCache patch       KV coordinator       GPU worker       GPUModelRunner
    │                    │                    │                   │                 │
    │ __init__(config)   │                    │                   │                 │
    ├───────────────────►│ init coordinator-side kvcached        │                 │
    │                    │ record TP/PP/async  │                   │                 │
    │                    ├───────────────────►│ native init       │                 │
    │                    │                    │ replace BlockPool │                 │
    │                    │                    │ create manager    │                 │
    │                    │                    │                   │                 │
    │ start executors/workers                 │                   │                 │
    ├───────────────────────────────────────────────────────────►│                 │
    │                    │                    │                   ├────────────────►│
    │                    │                    │                   │ init worker VMM │
    │                    │                    │                   │ start listener  │
    │                    │                    │                   │ allocate VA KV  │
    │                    │                    │                   │ bind views       │
    │◄───────────────────────────────────────────────────────────┤ ready            │
    │ install ordered-unmap worker collective barrier           │                 │
```

### 7.4 ElasticBlockPool

类在 `integration/vllm/patches.py:620-1121` 动态定义。它不能只实现alloc/free，因为vLLM上层依赖BlockPool的隐式contract：

| Contract | 实现 |
|---|---|
| block object identity | 预建 `KVCacheBlockClass(i)` 数组，按manager返回id索引 |
| null block | block 0 永久保留并标 `is_null` |
| prefix lookup | `(block_hash, group_id) → blocks`，支持duplicate materialization |
| active ownership | `ref_cnt`，touch时从evictable LRU移除 |
| cached free | full cached block ref=0后进入evictable LRU，不立即释放 |
| uncached free | partial/无hash block直接manager.free |
| cache cap | cached blocks超限时evict并manager.free |
| scheduler capacity | physical manager free + evictable cached blocks |

### 7.5 vLLM allocation 时序

```text
Scheduler        KVCacheManager       Coordinator       ElasticBlockPool      KVCacheD manager
    │ allocate_slots(req,n) │                  │                  │                    │
    ├──────────────────────►│                  │                  │                    │
    │                       ├─────────────────►│ group allocation │                    │
    │                       │                  ├─────────────────►│ get_new_blocks(n)  │
    │                       │                  │                  ├───────────────────►│
    │                       │                  │                  │ available snapshot │
    │                       │                  │                  │◄───────────────────┤
    │                       │                  │                  │ alloc(n)            │
    │                       │                  │                  ├───────────────────►│
    │                       │                  │                  │   map if needed     │
    │                       │                  │                  │◄───────────────────┤
    │                       │                  │◄─────────────────┤ KVCacheBlock list  │
    │                       │◄─────────────────┤ block tables     │                    │
    │◄──────────────────────┤ SchedulerOutput │                  │                    │

race: another process consumes last physical page
    KVCacheD alloc returns None
    → ElasticBlockPool raises KVCachePoolExhausted
    → patched allocate_slots rolls back partial group allocation
    → returns None
    → Scheduler treats as temporary miss/preempts/retries
```

只捕获`KVCachePoolExhausted`。shape/layout/invariant ValueError仍然fatal，避免把真实bug伪装成负载压力。

### 7.6 GPUModelRunner tensor allocation

vLLM 0.9+ patch 给GPUModelRunner增加 `_allocate_kv_cache_from_kvcached`：

1. 验证各 KV group 的 physical block geometry。
2. 排除 cross-layer sharing 的borrower layer，只给tensor owner分配storage。
3. 找代表性的attention group/spec/backend。
4. 取得backend KV shape和kernel block size。
5. 对packed KV、MLA、HYBRID_LINEAR、heterogeneous attention做专门geometry检查。
6. 调 `vllm.interfaces.alloc_kv_cache` 创建raw FTensor。
7. 根据group/layer构建per-layer `view/as_strided/permute`。
8. shared layer alias到owner tensor。
9. 交还原生 `bind_kv_cache` 注册到attention modules。

关键点：物理bytes布局必须和backend计算地址的方式一致。tensor shape“看起来正确”不够，stride、K/V offset、kernel-block ratio、inline scale/padding都必须匹配。

### 7.7 Worker capacity profile

vLLM原生 `Worker.determine_available_memory` 用初始化前后whole-device free-memory delta；共置进程在profile期间分配/释放会破坏这个假设。patch改用：

```text
virtual_budget
  - model_runner.model_memory_usage
  - process-local torch activation peak
  = available KV virtual bytes
```

显式 `kv_cache_memory_bytes` 和upstream startup plan仍优先，避免patch覆盖用户明确预算。CUDA graph的whole-device delta不计入可用KV预算，但相关字段仍填充给upstream warmup contract。

### 7.8 APC 与physical page eviction

ElasticBlockPool区分两种eviction目标：

- allocation shortage：free的logical slot马上复用，按纯LRU即可；page-aware排序不会多释放物理页，反而可能牺牲更新prefix。
- 主动cache cap/trim：目标是归还VRAM，优先选择所有occupancy都在evictable集合中的page；整页清空才有physical收益。

### 7.9 async/queued batch 释放

```text
EngineCore step N submits worker batch reading page P
    │
Scheduler logically frees P during/after later bookkeeping
    │
KVCacheManager marks P retired with epoch E
    │
EngineCore.step_with_batch_queue returns after submitting ordered work
    │
capture marker E
    │
model_executor.collective_rpc(_worker_physical_release_barrier)
    │ every worker synchronizes prior work
    ▼
release_retired_pages_through(E)
    │
transactional unmap P
```

没有这条barrier，scheduler CPU状态可能已经free block，但GPU队列中旧batch仍在异步读取相同page，提前unmap会产生illegal memory access或silent output corruption。

## 8. TP/PP IPC 协议

文件：`kvcached/tp_ipc_util.py`。

### 8.1 地址与所有权

socket root：`/tmp/kvcached-tp-<ipc-name>-<hash>`。

```text
PP=1:
  root/w0.sock
  root/w1.sock

PP>1:
  root/w0.sock, root/w1.sock        # pp0
  root/pp1/w0.sock, root/pp1/w1.sock
  root/pp2/w0.sock, root/pp2/w1.sock
```

`pp_rank=-1` 表示coordinator operation要覆盖所有PP stage；`KVCACHED_PP_SIZE`决定stage集合。

### 8.2 map 协议

```text
coordinator          rank0           rank1           rankN
    │ MAP(offsets)      │               │               │
    ├─────────────────►│               │               │
    ├─────────────────────────────────►│               │
    ├─────────────────────────────────────────────────►│
    │                  local map       local map       local map
    │◄──────────────── success/new ────┤               │
    │◄──────────────────────────────── success/new ────┤

any failure:
  coordinator sends rollback/unmap for offsets newly mapped by successful ranks
  rollback uncertainty → StateConsistencyError / quarantine
```

### 8.3 unmap 两阶段协议

```text
Coordinator                 Workers
     │ PREPARE(tx, offsets)     │
     ├────────────────────────► │ unmap physical, remap zero,
     │                          │ retain physical handles
     │ ◄──────── prepared ───── │
     │
     ├─ if any prepare failed:
     │      ABORT(tx) ─────────► restore retained handles
     │
     └─ if all prepared:
            COMMIT(tx) ────────► release handles
            ambiguous result ──► retry COMMIT, never ABORT
```

transaction outcome有bounded history，使重复commit/abort幂等。prepare未到达某worker而全局abort时，该worker也记录ABORTED，防止延迟prepare重新打开transaction。

### 8.4 listener shutdown

`_WorkerListener.stop`：

1. 设置stop event，拒绝新connection dispatch。
2. `shutdown()`已accept sockets，唤醒blocked recv。
3. 主动连接自己，唤醒blocked accept。
4. join listener thread，等待正在执行的VMM call结束。
5. 只有thread确认退出后，才unlink socket和空目录。

若5秒内无法drain，返回False并保留资源供重试；不能一边handler还在VMM里，一边销毁allocator。

## 9. shared memory limit 与 resize

`csrc/inc/mem_info_tracker.hpp` 的shared record保存KV limit、used、preallocated等。`kvctl`修改limit/revision后：

```text
kvctl limit
  → update /dev/shm record + revision
  → PageAllocator resize_watcher observes change
  → compute new per-layer target
  → KVCacheManager next allocation observes resize target
  → grow: extend logical page space
  → shrink:
       stop issuing blocks beyond target
       move/free empty pages
       wait until in-use tail blocks drain
       trim reserve mappings
```

resize不是强制抢占正在运行request；收缩可能是渐进的。上层scheduler/cache eviction决定多快释放live/cached blocks，KVCacheD不能无视ownership直接unmap。

## 10. Prefix cache 的源码所有权

### vLLM

```text
Request.block_hashes
  → KVCacheManager/Coordinator finds cached full blocks
  → ElasticBlockPool._cached_blocks[(hash, group)]
  → touch increments ref_cnt
  → free_blocks decrements ref_cnt
       cached full block → _evictable_blocks LRU
       uncached partial  → KVCacheManager.free immediately
```

### SGLang

```text
RadixKey(token_ids, extra_key, cache_salt)
  → RadixCache.match_prefix
  → TreeNode.value = token-slot tensor
  → lock_ref protects in-flight prefix
  → cache_finished_req inserts suffix
  → eviction frees TreeNode.value through allocator
```

### KVCacheD

KVCacheD不理解hash或radix key，只看最终block IDs。它唯一能做的prefix-aware事情，是要求engine cache layer在bound/pressure下释放ID；page ledger随后判断是否能归还physical page。

## 11. Layout 计算

### 11.1 基本公式

```text
engine block bytes = tokens_per_block × per_token_cell_bytes

MHA/GQA per-token cell
  = num_kv_heads × head_dim × dtype_bytes
  (K/V数量由num_kv_buffers或shape中的K/V维表示)

manager physical accounting
  = mapped_pages × page_size × num_layers × num_kv_buffers
```

### 11.2 vLLM backend shape

adapter识别：

- FlashAttention：`(2, num_blocks, block_size, heads, dim)`。
- FlashInfer：`(num_blocks, 2, block_size, heads, dim)`。
- packed KV：`(num_blocks, heads, block_size, 2*dim)`。
- MLA：`(num_blocks, block_size, latent_head_size)`。

virtual block可能比kernel block大，例如256-token virtual block拆成4个64-token kernel blocks。adapter必须按kernel-block粒度建立stride，否则zero/copy/attention kernel会跳错地址。

### 11.3 contiguous offset

```text
non-contiguous offset = page_id × PAGE_SIZE

contiguous compound offset
  = page_id × PAGE_SIZE × num_layers × num_kv_buffers
```

manager和FTensor创建时的`num_layers/num_kv_buffers`必须完全一致；只要compound stride不同，即使总bytes够，也会map到错误offset。vLLM interface因此保存created tensor capacity record，并让manager-first/tensor-first两种顺序都做交叉验证。

## 12. Controller 源码

controller不是VMM核心，但提供完整多模型应用示例：

| 文件 | 职责 |
|---|---|
| `controller/launch.py` | 解析YAML，构造vLLM/SGLang命令和env，以tmux启动实例/router |
| `controller/frontend.py` | aiohttp OpenAI-compatible入口和管理API |
| `controller/router.py` | model name → endpoint，转发stream/non-stream请求 |
| `controller/traffic_monitor.py` | request start/end、rate、idle duration |
| `controller/sleep_manager.py` | idle检测，调用vLLM sleep/wake或SGLang release/resume |

请求时序：

```text
Client        Frontend        SleepManager       Router          Engine
  │ request      │                 │                │               │
  ├─────────────►│                 │                │               │
  │              ├─ is sleeping? ─►│                │               │
  │              │◄─ status ───────┤                │               │
  │              ├─ wake if needed►│────────────── engine API ─────►│
  │              │◄─ ready ────────┤                │               │
  │              ├────────────────────────────────►│ route         │
  │              │                                 ├──────────────►│
  │              │◄────────────────────────────────┤ response      │
  │◄─────────────┤ stream/response                  │               │
  │              └─ record activity                │               │
```

## 13. 错误如何传播

| 错误 | 层 | 处理 |
|---|---|---|
| physical page暂时不足 | manager/ElasticBlockPool | 返回None或专用exhaustion，转scheduler retry |
| block/page geometry非法 | adapter/manager init | fail early，提示调整page size/config |
| 部分map失败且可回滚 | FTensorAllocator | rollback新增映射，allocation失败 |
| map rollback失败 | FTensor/PageAllocator | quarantine page，避免发布未知mapping |
| unmap prepare失败 | TP IPC | 对已prepare worker发送abort恢复 |
| unmap commit不明 | TP IPC | 幂等重试commit；仍不明则fail pool |
| queued GPU work未完成 | vLLM EngineCore patch | worker barrier后才drain retired pages |
| worker listener未drain | shutdown | 返回False，保留allocator供重试 |
| engine版本/runner无adapter | EngineCore/autopatch | fail loud，不允许半接入 |

“资源压力”可恢复，“状态一致性未知”不可恢复，这是整套错误语义的主线。

## 14. 源码文件索引

### KVCacheD 必读

| 顺序 | 文件 | 重点符号 |
|---|---|---|
| 1 | `kvcached/autopatch.py` | `autopatch_all` |
| 2 | `integration/patch_base.py` | `BasePatch`, `PatchManager` |
| 3 | `integration/sglang/autopatch.py` | patch顺序和version ranges |
| 4 | `integration/sglang/interfaces.py` | `init_kvcached`, `alloc_kv_cache`, `alloc_mamba_states`, `get_kv_cache_manager` |
| 5 | `integration/sglang/patches.py` | Elastic allocator/pool、capacity、Radix bound |
| 6 | `integration/vllm/autopatch.py` | V1/MRV2/worker/coordinator patch矩阵 |
| 7 | `integration/vllm/interfaces.py` | KV shape/view、created capacity guard |
| 8 | `integration/vllm/patches.py` | ElasticBlockPool、EngineCore、runner、worker、allocate_slots |
| 9 | `kv_cache_manager.py` | `_alloc`, `_pick_avail_page`, `free`, `resize`, `available_size`, `shutdown` |
| 10 | `tp_ipc_util.py` | listener、broadcast map、2PC unmap |
| 11 | `csrc/page_allocator.cpp` | page state、prealloc、map/unmap dispatch |
| 12 | `csrc/allocator.cpp` | FTensorAllocator create/map/transaction |
| 13 | `csrc/ftensor.cpp` | VA reservation与single tensor mapping |
| 14 | `csrc/inc/gpu_vmm.hpp` | CUDA/HIP API abstraction |

### SGLang 对照

| 文件 | 为什么读 |
|---|---|
| `srt/managers/scheduler.py` | request/batch主循环和memory pool初始化 |
| `srt/mem_cache/allocator/base.py` | allocator contract/free-group/eviction接口 |
| `srt/mem_cache/allocator/token.py` | 原生token free tensor |
| `srt/mem_cache/allocator/paged.py` | extend/decode page allocation |
| `srt/mem_cache/memory_pool.py` | MHA/MLA/Mamba/hybrid真实tensor shape |
| `srt/mem_cache/radix_cache.py` | prefix key/node/match/insert/evict |
| `srt/mem_cache/kv_cache_configurator.py` | virtual capacity如何转成pool size |

### vLLM 对照

| 文件 | 为什么读 |
|---|---|
| `v1/engine/core.py` | EngineCore初始化、step、sleep/shutdown、batch queue |
| `v1/core/block_pool.py` | native block/APC/null/ref/free queue contract |
| `v1/core/kv_cache_manager.py` | allocate_slots返回None的scheduler语义 |
| `v1/core/kv_cache_coordinator.py` | multi-group/hybrid block ownership |
| `v1/worker/gpu_worker.py` | capacity profile、sleep、worker lifecycle |
| `v1/worker/gpu_model_runner.py` | KV tensor allocation/bind/backend initialization |
| `v1/kv_cache_interface.py` | KV spec/config/tensor/group geometry |

## 15. 调试与验证路径

### 15.1 确认 patch 真正生效

1. 检查 `.pth` 在解释器执行的 site-packages。
2. 两个env都设置：`ENABLE_KVCACHED=true`、`KVCACHED_AUTOPATCH=1`。
3. 日志出现PatchManager检测版本和成功patch列表。
4. 运行时class/module alias指向Elastic实现。
5. `kvctl list`能看到pool，idle VRAM接近权重+reserve而不是完整KV reservation。

### 15.2 alloc 热路径观察点

```text
engine allocator get_new/alloc
  → KVCacheManager.available_size
  → KVCacheManager._alloc
  → PageAllocator.alloc_page
  → PageAllocator.map_pages
  → tp_ipc broadcast or FTensorAllocator.map
```

需要记录：requested blocks、logical free、physical free pages、selected page IDs、offsets、rank responses和耗时。

### 15.3 free 不降显存

按顺序排查：

1. block是否仍由running request引用。
2. 是否进入vLLM APC/SGLang RadixCache。
3. page occupancy是否仍非0。
4. empty page是否进入mapped reserve pool。
5. 是否在retired_pages等待async fence。
6. transactional unmap是否成功commit。
7. driver显示是否还有其它非KV allocation。

### 15.4 最重要测试簇

- `test_alloc_rollback.py`、`test_vmm_failure_policy.py`：失败与quarantine。
- `test_tp_ipc_atomic_map.py`、`test_tp_ipc_unmap_sync.py`、`test_tp_ipc_pp_fanout.py`：rank一致性。
- `test_vllm_pool_exhaustion.py`、`test_vllm_async_unmap_ordering.py`：scheduler miss与lifetime。
- `test_vllm_native_block_pool*.py`、`test_prefix_cache.py`：block/APC契约。
- `test_sglang_allocator_patch.py`、`test_sglang_mem_pool_seam.py`：SGLang seam。
- `test_*mamba*`、`test_*hybrid*`、`test_*packed*`：复杂layout。
- `test_shared_segment_lifecycle*`、`test_vllm_engine_core_shutdown.py`：资源清理。

## 16. 从源码得出的核心结论

1. KVCacheD 的本质不是“另一个KV allocator”，而是 engine logical ownership 与 GPU physical backing 之间的 translation layer。
2. FTensor让attention kernel透明；KVCacheManager让engine allocator透明；version patches让上游源码透明。这三层透明性分别对应VMM、ledger和compatibility成本。
3. SGLang适配复杂度主要来自pool种类和token/radix语义；vLLM适配复杂度主要来自BlockPool隐式contract、hybrid groups和EngineCore/worker进程分离。
4. correctness难点不在成功路径，而在partial map rollback、allocation race、queued GPU lifetime和distributed unmap。
5. prefix cache是上层metadata policy，physical elasticity是下层page policy；只有两层共同释放ownership，VRAM才真正归还。
6. 升级一个engine版本时，必须重新验证class alias捕获时机、method signature、KV shape/stride、runner选择和shutdown路径，不能只看import是否成功。

## 相关入口

- 三项目关系地图：[[kvcached-sglang-vllm-knowledge-system]]
- 完整架构来源：[[src-kvcached-architecture]]
- 核心概念：[[elastic-kv-cache]]
- 集成与实验：[[kvcached-integration-implementation-guide]]
- 项目实体：[[kvcached]]、[[sglang]]、[[vllm]]
- 引擎缓存算法：[[radix-attention]]、[[paged-attention]]
