# KVCacheD 与 SGLang、vLLM 架构关系及源码实现分析

> 仓库：`/Users/zhenyu.jiang/kvcached`，对照 `/Users/zhenyu.jiang/sglang`、`/Users/zhenyu.jiang/vllm` · 分析日期：2026-10-02 · 版本：KVCacheD `884108704f44`，SGLang `44ef8fecfe69`，vLLM `dc36fcce902a`

## 一句话定位

KVCacheD（项目名写作 `kvcached`，意为 KV cache daemon）不是第三个推理引擎，也不是 vLLM/SGLang 的远端 KV offload 系统；它是插入推理引擎 KV 分配路径的 **GPU 虚拟内存层**。它让引擎先获得容量很大的稳定虚拟 KV tensor，再按请求真实使用的 block/token 将 CUDA/HIP 物理页映射进去，并在 block 释放、prefix cache 淘汰或管理员收紧 limit 时解除映射，从而让多个 vLLM/SGLang 实例或其它 GPU 工作负载共享同一块 GPU 的物理显存。

SGLang 与 vLLM 仍分别拥有请求调度、prefix cache、block/token 元数据、attention kernel、模型执行和 API 服务；KVCacheD 只替换它们的 KV tensor 创建、逻辑槽位分配以及相关的容量画像、回收和多进程一致性路径。当前集成是 KVCacheD 一侧通过 `.pth + wrapt import hook + 版本化 monkey patch` 实现，两个上游仓库没有原生引用 KVCacheD，因此版本兼容层是项目最重要、也最脆弱的工程边界。

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

最关键的边界是：引擎看见的 KV tensor 指针和 shape 在初始化后保持稳定，attention kernel 仍按原有 tensor/block table 读取；变化的是这些虚拟地址当前是否由真实 VRAM page backing。KVCacheD 不能共享模型权重，也不让两个进程共享同一份 prefix KV 内容；它共享的是 **同一设备上的可用物理显存池**。

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 安装与自动注入 | `setup.py`、`kvcached_autopatch.pth`、`kvcached/autopatch.py` | 构建 stable-ABI C++ 扩展，把 `.pth` 放入 site-packages，在解释器启动时注册 import hook |
| 补丁框架 | `kvcached/integration/patch_base.py`、`version_utils.py` | 按引擎版本注册、筛选和幂等应用 patch；动态 import 目标模块 |
| SGLang 适配 | `integration/sglang/{autopatch,interfaces,patches}.py` | 替换 token/page allocator 和 MHA/MLA/Mamba/hybrid pool；修正虚拟容量、RadixCache 上限和 leak 检查 |
| vLLM 适配 | `integration/vllm/*.py` | 注入 ElasticBlockPool；替换 GPU KV tensor 分配/reshape；处理 V1/MRV2、hybrid、APC、NIXL 和 EngineCore/worker 生命周期 |
| Python KV 管理 | `kv_cache_manager.py`、`kv_geometry.py`、`pool_registry.py` | 把引擎 block id 分组到 VMM page；逻辑分配、best-fit、回滚、resize、limit、延迟物理释放 |
| 多进程一致性 | `tp_ipc_util.py`、`locks.py` | 用 Unix domain socket 把 map/unmap 发到 TP/PP worker；unmap 使用 prepare/commit/abort 协议 |
| C++ page allocator | `csrc/page_allocator.cpp`、`csrc/inc/page_allocator.hpp` | 管理 free/reserved/in-use/quarantined page；后台预映射；触发单进程或广播 map/unmap |
| C++ 虚拟 tensor | `csrc/allocator.cpp`、`csrc/ftensor.cpp`、`gpu_vmm.hpp` | 预留 GPU VA、创建 torch tensor view、映射/解绑真实 page、保留 zero page、事务性回滚 |
| 共享控制面 | `mem_info_tracker.*`、`control.py`、`cli/kvctl.py`、`cli/kvtop.py` | 用 POSIX shared memory 发布使用量与 limit/revision；CLI 动态设限和观察 |
| 多模型控制器 | `controller/{launch,frontend,router,sleep_manager,traffic_monitor}.py` | 拉起多个引擎、OpenAI-compatible 转发、流量统计、idle sleep/wakeup；不是核心 VMM 必需组件 |
| 验证与基准 | `tests/`、`benchmarks/`、`examples/` | 覆盖 page 几何、分配回滚、TP/PP、APC、hybrid、NIXL、shutdown、性能和多模型场景 |

KVCacheD 自身分成三个清晰平面：引擎 patch 是“语义适配面”，Python `KVCacheManager` 是“逻辑分配面”，C++ VMM 是“物理映射面”。跨实例配额通过 `/dev/shm` 协调，跨 rank 映射通过 `/tmp/kvcached-tp-*/*.sock` 协调，两者不是同一个 IPC 通道。

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

这里有两个开关：`KVCACHED_AUTOPATCH=1` 决定 import hook 是否应用补丁，`ENABLE_KVCACHED=true` 决定补丁包装器运行时是否走 KVCacheD 分支。只设置其中一个可能导致“装了但没生效”；`kvcached/__init__.py:31-72` 会在环境变量已开但 `.pth` 缺失时发出显式 warning。

### 从逻辑 block 到物理 VRAM

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

`FTensor` 构造时预留虚拟地址并用一个 zero page 初始化整个区域，再通过 `torch::stable::from_blob` 暴露为 tensor（`csrc/ftensor.cpp:91-102`）。真实请求到来后，`FTensor::map` 先解除目标 zero-page 映射，再分配物理页并映射到相同 VA（`csrc/ftensor.cpp:127-187`）。解除映射时先把地址重新映回 zero page，再释放真实 page handle（`csrc/ftensor.cpp:210-249`），因此 tensor 对象和指针不需要重建。

### SGLang 请求路径

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

SGLang 的核心语义仍是 `ReqToTokenPool → TokenToKVPool → RadixCache`。KVCacheD 将 `TokenToKVPoolAllocator`/`PagedTokenToKVPoolAllocator` alias 到 elastic 版本，把 `alloc/free/available_size` 委托给 `KVCacheManager`；同时将 `MHATokenToKVPool`、`MLATokenToKVPool`、Mamba 和 hybrid pool 的 buffer 创建改为 VMM-backed tensor。Radix tree 本身不被替换，只在 `cache_finished_req` 后按 `KVCACHED_MAX_CACHED_TOKENS` 主动 evict，以防 prefix cache 永久占住所有物理页。

### vLLM 请求路径

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

vLLM 的 `Request`、block hash、coordinator/single-type manager、scheduler 和 attention backend 都继续工作。`ElasticBlockPool` 复刻 native `BlockPool` 的 null block、ref count、full-block cache、duplicate hash 和 LRU 行为，但最终 block id 来自 KVCacheD。物理容量是一份跨进程共享的瞬时状态，因此 `available_size()` 之后仍可能被同 GPU 的另一个实例抢走；补丁把专门的 `KVCachePoolExhausted` 转为 `allocate_slots() -> None`，让原生 scheduler 按“本轮不能分配”处理，而不是杀死 EngineCore（`integration/vllm/patches.py:3145-3231`）。

### TP/PP 一致性与异步释放

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

Map 失败可以回滚刚刚映射的 offsets；若回滚本身失败，page 被 quarantine，防止继续使用状态不明的地址。Unmap 更危险，因为某些 rank 成功、某些 rank 失败会让同一个 block table 在不同 GPU 上指向不同物理状态，所以 `tp_ipc_util.py:567-676` 使用 prepare/commit/abort；commit 结果不明时只重试 commit，不能 abort 已可能释放的 handle。`PageAllocator` 一旦判定 state consistency 未知就 fail-loud，后续分配不再冒险运行。

### 多模型控制器路径

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

控制器是示例级的单机编排和流量入口，不是生产级 Kubernetes operator，也不参与单次 block 分配。它解决的是“多个模型进程如何拉起、路由、空闲休眠”，核心 VMM 解决的是“活跃实例之间 KV 物理显存如何随负载弹性变化”。

## 设计决策与哲学

- **稳定 VA，弹性 backing**：预留的是地址空间，不是同等大小 VRAM；engine/kernel 看见稳定 tensor，物理页按需出现。核心见 `csrc/allocator.cpp:128-161`、`csrc/ftensor.cpp:91-102`。
- **适配引擎分配语义，不改 attention kernel**：SGLang 继续用 token/page index + RadixCache，vLLM 继续用 block table + block hash。适配器构造正确 shape/stride 的 tensor view，让原生 backend 无感读取，见 `integration/sglang/interfaces.py:125-234`、`integration/vllm/interfaces.py:448-791`。
- **KVCacheD page 不等于引擎 block/page**：默认物理页为 2 MiB；一个物理页可装多个 vLLM block 或 SGLang token page。只有整页内所有 block 都 free，VRAM 才能释放，因此 manager 使用 page-affine/best-fit 分配，prefix eviction 也优先清空整页。
- **逻辑容量和瞬时物理容量分离**：引擎初始化时按虚拟预算建立 block/token capacity，运行时 `available_size()` 同时考虑空闲逻辑槽和 device-wide 物理页。另一个进程会改变后者，所以预检不是 reservation，必须允许可恢复的 allocation miss。
- **少量 reserve page 换取热路径延迟**：`PageAllocator` 默认后台预映射 5–10 个 page，alloc 快路径直接取 reserved page；代价是少量 idle footprint，可由 `KVCACHED_PAGE_PREALLOC_ENABLED`、`MIN/MAX_RESERVED_PAGES` 控制（`csrc/page_allocator.cpp:169-260,637-742`）。
- **跨 rank unmap 采用事务语义**：map 可回滚新增页；unmap 则显式保留 handle 到 commit，防止部分 rank 释放后再也无法恢复。该选择把一致性优先级放在可用性之上。
- **fail-loud 优于静默 fallback**：block/page 几何不合法、runner 版本无适配器、layout 不匹配、事务状态未知时直接报错；否则“部分补丁成功、部分走原生”会产生 silent KV corruption。
- **版本化 monkey patch 换取零上游侵入**：用户可以在原有 vLLM/SGLang 环境里安装 plugin，无需维护 fork；代价是上游内部类名、签名和布局每次变化都可能要求新 patch。最近 Git 历史中大量兼容修复正是这个代价。
- **prefix reuse 必须受物理弹性约束**：原生 APC/RadixCache 倾向保留已完成请求的 KV；无限缓存会让 elastic pool 退化成静态占用，因此默认 `KVCACHED_MAX_CACHED_TOKENS=16000`，`-1` 才是无限，`0` 是立即淘汰。
- **SGLang 与 vLLM 的 rank 所有权不同**：SGLang 每个 TP worker 本地拥有并驱动自己的 pool，manager 以 `world_size=1` 创建；vLLM 的 EngineCore/coordinator 可以与 worker 分进程，因此由 coordinator manager 通过 worker IPC fan-out map/unmap。见 `integration/sglang/interfaces.py:463-496` 与 `integration/vllm/interfaces.py:57-121,926-968`。

## 关键组件深入解读

### FTensorAllocator / FTensor：让 tensor 地址与物理显存解绑

`FTensorAllocator::init` 建立进程级 allocator，并记录 device、page size 和 contiguous layout。每个 hybrid KV group 可通过 `group_id` 懒创建独立 allocator（`csrc/allocator.cpp:79-121`）。`create_kv_tensors` 把每层空间向 page 对齐：

- non-contiguous：每层一个 FTensor；MHA/GQA 通常在同一层 tensor 的前后半部分放 K/V；MLA/unified pool 只映射单 buffer。
- contiguous：所有 layer 和 K/V 共享一段大 VA；一个 compound physical page 同时覆盖所有 layer/buffer，offset 为 `page_id * page_size * num_layers * num_kv_buffers`。

前者给每层 dense/contiguous view，适合要求独立 per-layer region 的 PD/NIXL；后者一次 map 即覆盖所有层，映射次数少，但每层 view 带 stride/interleave，一些 ROCm backend 或 per-layer pointer-copy kernel 无法正确处理。源码因此在 CUDA 默认 contiguous、ROCm 默认 non-contiguous（`utils.py:159-180`）。

`map_to_kv_tensors_with_result` 对一个 logical offset 的所有 layer/K/V target 做组级检查：全部已映射则幂等跳过，部分映射视为 state inconsistency；映射中途失败会反向 unmap 已成功 target。回滚失败时抛 `MapQuarantinedError`，上层 quarantine 未发布 page（`csrc/allocator.cpp:169-272`）。

### KVCacheManager：block ledger、page affinity 与回收

`KVCacheManager` 的输入不是 tensor shape，而是 `num_blocks × block_size × cell_size × num_layers × num_kv_buffers` 的统一几何。构造阶段先检查一个物理 page 是否至少容纳一个完整 block、block 跨页是否会造成零容量 page，再创建 C++ `PageAllocator`（`kv_cache_manager.py:101-200`）。

核心状态：

- `avail_pages`：已映射且有空闲 block 的 page。
- `full_pages`：所有 block 已分配的 page。
- `reserved_blocks`：逻辑预留但未交给普通分配的 block。
- `retired_pages`：异步 vLLM 路径中逻辑已空、等待 worker fence 后才能物理 unmap 的 page。
- `in_shrink/target_num_blocks`：外部 limit 收紧时的渐进式缩容状态。

`_alloc` 先消费 reserved block，再在 `avail_pages` 里选择能完整容纳 remaining run 的最小 page；没有 page 时调用 C++ allocator 映射新页。这个 best-fit/page-affine 策略避免一个长请求散落到很多 page，导致 prefix cache 仅保留少量 block 却 pin 住大量物理页（`kv_cache_manager.py:417-569`）。若物理竞争导致中途 `alloc_page` 失败，已拿到的 block 会按来源回滚，返回 `None` 而不是泄漏。

`free` 按 page 聚合 block。page 清空后可能进入 reserve pool，也可能 unmap；异步 scheduler 下先进入 `retired_pages`，由 `capture_physical_release_marker/release_retired_pages_through` 在 EngineCore worker barrier 后释放。`available_size()` 取 `min(logical_free, device_physical_capacity)`，并给昂贵的 driver free-memory query 加短 TTL，所有本实例 mutation 都主动失效缓存。

### SGLang patch：替换 allocator 和 pool，保留 RadixCache

SGLang 原生分配链是 `Scheduler → BaseTokenToKVPoolAllocator → KVCache buffer`。KVCacheD 的 `ElasticAllocatorPatch` 动态定义两个类并覆盖模块 alias：

- token path：`ElasticTokenToKVPoolAllocator.alloc(n)` 直接从 manager 取 n 个 token slot，再构造 GPU int64 index tensor。
- paged path：先按 SGLang `page_size` 计算 page 数，从 manager 取 block ids，再展开为连续 token indices；extend/decode 仍调用 SGLang 原生 allocator kernel 填充位置。

`ElasticMemoryPoolPatch`/`ElasticMLAMemoryPoolPatch` 跳过原生 `torch.empty/zeros` 大块真实分配，调用 `alloc_kv_cache` 建 VA tensor，再以 `as_strided` 暴露 SGLang 期望的 `[token, head, dim]` 或 MLA shape。Mamba 使用 per-slot super-cell，把多个 convolution state 和 temporal state 按字节 offset 打包；cell 被 pad 到 `PAGE_SIZE` 的因数，避免一个逻辑 slot 跨物理 page 后容量高估（`integration/sglang/interfaces.py:237-460`）。

SGLang 的 `_profile_available_bytes` 原本受设备当前 free memory 影响，多实例同时启动会彼此干扰。patch 改成 `total_memory * mem_fraction_static - 当前进程 PyTorch reserved`，并对所有 rank 取 min；这给每个进程稳定的虚拟上限，而真实共享竞争留到运行时 manager 处理（`integration/sglang/patches.py:113-256`）。

### vLLM patch：BlockPool 语义复制与 worker tensor 替换

vLLM 的集成面更宽，因为 V1 EngineCore 和 GPU worker 通常分进程：

1. `EngineCorePatch` 在 engine 初始化前记录 TP/PP 和 async/queued execution，之后安装 worker collective release barrier。
2. `KVCacheCoordinatorPatch` 读取 `KVCacheConfig`，推导 block size、每 block 字节、group size、K/V buffer 数，再把 native `block_pool` 替换为 `ElasticBlockPool`。
3. `GPUWorkerPatch` 不再用 whole-device free delta 推导 KV 容量，而使用进程本地 weights + activation peak；保留显式 `kv_cache_memory_bytes` 和 startup plan。
4. `GPUModelRunnerPatch` 在 worker 初始化 VMM，拦截 KV tensor 分配，把 raw VA tensor reshape 成 FlashAttention/FlashInfer/Triton/MLA/hybrid backend 需要的 view，然后仍调用 native `bind_kv_cache`。
5. `KVCacheManagerAllocateSlotsPatch` 将共享物理池竞争导致的分配失败翻译回 scheduler 的 `None` 语义，并在新版本 hybrid coordinator 中回滚本次跨 group 部分分配。

`ElasticBlockPool` 必须复刻不少隐藏契约：block 0 是 null、cached full block 有 hash、重复 prefix 可能并存、`touch` 增 ref 并撤出 evictable LRU、partial uncached block 完成立即 free、full cached block ref=0 后保留、APC cap 超限才真正还给 KVCacheD。0.26+ 上游增加 native block pool 行为后，项目通过 `NativeBlockPoolMixin` 补齐兼容。

### Layout / geometry：集成最容易出错的地方

三个“page/block”概念必须分开：

| 名称 | 所有者 | 含义 |
|---|---|---|
| VMM physical page | KVCacheD | CUDA/HIP 映射粒度，默认 2 MiB，可配置为 2 MiB 倍数 |
| KV block/token page | vLLM/SGLang | scheduler 和 attention backend 的逻辑索引粒度，如若干 token |
| kernel block | attention backend | kernel 真正处理的 block；vLLM virtual block 可能拆成多个 kernel block |

`block_mem_size = engine_block_size × cell_size`。一个 KVCacheD page 可能装多个 engine blocks，但不能让某 block 跨 page 后留下无法表示的洞。vLLM hybrid group 还要求各 group 的物理 block bytes 可统一；异构 attention geometry 可建立不同 `as_strided` view，但 hybrid-linear + heterogeneous attention geometry 被明确拒绝。新 MRV2 对 virtual block/kernel block split、shared layer owner、packed KV 和 page alignment 都有单独适配。

### Prefix cache：缓存命中率与释放显存的冲突

SGLang RadixCache 的 value 是 token-slot index；vLLM APC 的 value 是 fixed block id。两者只要继续保留 index，就意味着相应 KV 物理页不能释放。KVCacheD 的策略不是禁用 prefix cache，而是建立 memory bound：

- SGLang：完成请求插入 RadixCache 后检查 `evictable_size_`，超限调用原生 `evict`；allocator free 最终落入 manager。
- vLLM：ElasticBlockPool 维护 cached map + evictable LRU；内存不足先按纯 LRU 淘汰，主动 trim/cap 时优先找能整页清空的 victims。

因此 `KVCACHED_MAX_CACHED_TOKENS=-1` 最接近原生缓存命中率，却可能完全牺牲弹性；`0` 最容易归还显存，但没有跨请求 prefix reuse；正数是二者之间的预算。

### Shared-memory limit 与 CLI

C++ `MemInfoTracker` 将 limit、used、preallocated、revision 等写到 POSIX shared memory。`kvctl list/watch/limit/limit-percent/delete` 和 `kvtop` 可以在引擎外读取或修改；PageAllocator 的 resize watcher 看见 revision 后计算新的 per-layer target，Python manager 在下一次 alloc/resize 流程中收缩逻辑容量并释放空页。

`KVCACHED_IPC_NAME` 是资源域名称。相同名称的进程参与同一 limit/usage 域；不同名称隔离统计和控制。它不是用于交换 KV 内容的 shared-memory buffer。生产中必须给租户/服务明确命名，并确保 `/dev/shm` 与 `/tmp/kvcached-tp-*` 生命周期随 Pod/进程清理。

## 三个项目的项目级关系

### 它们是什么关系，而不是什么关系

| 问题 | 答案 |
|---|---|
| KVCacheD 是 vLLM/SGLang fork 吗？ | 不是。它是独立 Python/C++ plugin，通过运行时 patch 接入上游安装包。仓库仍保留早期版本的 static patch 文件，但当前主线是 autopatch。 |
| vLLM 与 SGLang 依赖 KVCacheD 吗？ | 不依赖。两仓源码中没有真实 `kvcached` 集成引用；关闭环境变量后应走原生路径。 |
| KVCacheD 替换 PagedAttention/RadixAttention 吗？ | 不替换。它改变 KV storage backing 和分配器；vLLM block table、SGLang radix tree 与原生 attention kernel仍在。 |
| 两个引擎能共享同一请求的 KV 内容吗？ | 不能。它们可以弹性竞争同一 GPU 的物理显存，但 KV layout、index 和 cache metadata 各自独立。 |
| KVCacheD 等同 CPU/NVMe KV offload 吗？ | 不等同。核心是 GPU VA ↔ GPU physical page 的映射/回收；NIXL/P-D 是额外兼容路径。 |
| KVCacheD 等同 MPS/MIG/HAMi 吗？ | 不等同。它是应用内 KV 内存管理，不提供硬件分区、通用 CUDA quota 或调度隔离，只管理接入的 KV buffer。 |
| 它能动态释放模型权重吗？ | 核心 allocator 只管理 KV。controller 可调用引擎 sleep/release API 释放更多内存，但权重生命周期仍归引擎。 |

### 为什么两个引擎需要不同适配策略

SGLang 的 token allocator 和 KV pool 同处 scheduler/worker 运行时，slot ownership 直接围绕 token index 展开，因此替换 allocator/pool class 就能覆盖主路径；每个 TP worker 本地做映射，不应把本 rank 的 pool 操作重复广播给 peers。

vLLM V1 将 scheduler-side BlockPool/KV coordinator 与 worker-side physical tensor 分开，EngineCore 可能完全看不到 CUDA tensor。因此 scheduler manager 分配 block id 后，必须通过 Unix socket 通知所有 worker 在相同 offset 建立 backing；queued/async execution 下，还必须先保证 GPU 不再读取待释放 page。vLLM 适配因此包含更多生命周期和故障翻译代码。

## 当前版本与兼容边界

分析快照：KVCacheD 本地 HEAD `8841087`，`pyproject.toml` 包版本仍为 `0.1.5`；README 声明 SGLang `>=0.4.9`、测试至 `0.5.15`，vLLM `>=0.8.4`、测试至 `0.24.0`，但本地代码已经包含更高版本适配（SGLang 0.5.17+/0.5.20、vLLM 0.28/0.29）。README 的“tested up to”与 HEAD 新增代码不是同一强度的证据，上生产必须以目标版本测试矩阵为准。

| 能力 | SGLang 路径 | vLLM 路径 | 注意事项 |
|---|---|---|---|
| MHA/GQA | Elastic MHA pool | V1/MRV2 tensor adapter | backend layout 必须匹配 |
| MLA | Elastic MLA pool | MLA KV spec/view | 2×page 对齐和单 buffer |
| Sliding window/hybrid attention | SWA allocator + hybrid pool | multi-group coordinator | group geometry和共享 block pool复杂 |
| Mamba/linear attention | super-cell/Mamba slot adapter | HYBRID_LINEAR + native state mixin | cell/page、partial tail、state copy都有专门限制 |
| Prefix cache | 原生 RadixCache + token bound | ElasticBlockPool APC + block LRU | cache bound决定弹性与命中率 |
| TP | worker-local pool（当前实现） | EngineCore fan-out 至 worker listeners | socket/device/rank必须一致 |
| PP | stage-local rank namespace | pp-rank socket目录 + coordinator fan-out | `KVCACHED_PP_SIZE`参与目标选择 |
| Async scheduling | pool lock + engine语义 | retired pages + collective barrier | 不能提前 unmap queued batch仍在读的page |
| P/D / NIXL | contiguous per-layer要求限制 | NIXL connector compatibility | smoke-tested不等于所有connector/backend组合支持 |
| ROCm | 默认 non-contiguous | 默认 non-contiguous | contiguous view可能被ROCm kernel误读 |
| Quantized KV | 部分 storage dtype；quant recipe有限制 | 某些 packed/FP8路径；inline scale有限制 | 必须按 model/backend/version 验证 |

明确的 avoid-if 条件：

- 目标引擎版本超出 adapter 明确范围，且无法固定版本或跑 GPU regression。
- attention backend 要求 KV layout 不在适配器支持集合；例如某些 HND、packed ROCm、inline scale/padded page 组合。
- 依赖严格的 KV cache events，而 ElasticBlockPool 当前断言 `enable_kv_cache_events=False`。
- 需要跨实例共享 prefix 内容、远端持久 KV 或集群级 locality routing；这应选 KV connector/offload/index 层。
- 需要强显存隔离或恶意租户安全边界；KVCacheD 只对接入路径做协作式管理。
- 无法容忍 monkey patch 随上游内部 API 演进的维护成本。

## 如何安装与集成

### 最小接入

1. 在目标 vLLM 或 SGLang Python 环境先安装匹配 GPU backend 的 PyTorch，当前构建要求 `torch>=2.10` stable ABI。
2. 安装 KVCacheD：`pip install kvcached --no-build-isolation`，或在仓库执行 `pip install -e . --no-build-isolation --no-cache-dir`。
3. 确认 site-packages 根目录存在并执行 `kvcached_autopatch.pth`；如果只把源码加入 `PYTHONPATH`，import hook 不一定注册。
4. 启动前设置 `ENABLE_KVCACHED=true` 和 `KVCACHED_AUTOPATCH=1`。
5. 首次验证先关闭 prefix cache，缩小变量面；确认分配与释放后再打开 APC/RadixCache 并设置 bound。
6. 日志应出现 `Applying ... patches` 和 `Successfully patched ...`；再用 `kvctl list`、`kvtop`、`nvidia-smi` 观察 idle KV physical footprint。

vLLM 示例：

```bash
export ENABLE_KVCACHED=true
export KVCACHED_AUTOPATCH=1
export VLLM_USE_V1=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN
vllm serve "$MODEL" --no-enable-prefix-caching --port 12346
```

SGLang 示例：

```bash
export ENABLE_KVCACHED=true
export KVCACHED_AUTOPATCH=1
python -m sglang.launch_server --model "$MODEL" \
  --disable-radix-cache --trust-remote-code --port 30000
```

README 提醒启用 KVCacheD 后通常不再需要用 `--gpu-memory-utilization`/`--mem-fraction-static` 做僵硬的跨实例静态切分；但当前 patch 仍会读取这些参数来形成虚拟预算，是否省略以及默认值必须结合目标版本验证。

### 生产化建议流程

1. **锁版本**：记录 KVCacheD commit、engine commit/package、PyTorch/CUDA/ROCm、attention backend、model architecture。
2. **做几何预检**：输出 block size、cell size、page size、num layers/buffers、contiguous layout 和 group geometry；block 大于 page 直接调整 `KVCACHED_PAGE_SIZE_MB` 或停用。
3. **单实例 correctness**：比较固定 seed 输出，覆盖 prefill/decode、长 context、abort、prefix hit、sleep/wake。
4. **双实例压力**：交替峰值、同时峰值、物理池耗尽、一个实例退出/崩溃、limit 动态收缩。
5. **多 rank**：分别验证 TP、PP、async scheduling；注入一个 listener 失败，确认事务 fail-loud 而不是 silent divergence。
6. **缓存策略**：从 `MAX_CACHED_TOKENS=0` 建立基线，再逐步增大，测 TTFT/ITL/throughput 与释放页数。
7. **可观测和清理**：检查 `/dev/shm/<ipc>`、`/tmp/kvcached-tp-*`、worker socket、shutdown 后 segment unlink。
8. **镜像固化**：使用 engine-specific Dockerfile 或固定 wheel，避免运行环境升级引擎后 monkey patch 仍“表面成功”。

### 关键环境变量

| 变量 | 作用 | 默认/建议 |
|---|---|---|
| `ENABLE_KVCACHED` | 运行时走 elastic path | 必须 `true/1` |
| `KVCACHED_AUTOPATCH` | import 时应用 patch | 必须 `true/1` |
| `KVCACHED_IPC_NAME` | shared-memory/worker socket 资源域 | 多服务显式命名 |
| `KVCACHED_PAGE_SIZE_MB` | VMM page，必须为 2 MiB 正倍数 | 默认 2；大 cell 模型增大 |
| `KVCACHED_GPU_UTILIZATION` | 可使用物理 GPU 空闲页比例 | 默认 0.95 |
| `KVCACHED_PAGE_PREALLOC_ENABLED` | 后台预映射 reserve page | 默认 true；测 idle footprint |
| `KVCACHED_MIN_RESERVED_PAGES` / `MAX_RESERVED_PAGES` | reserve 水位 | 默认 5/10 |
| `KVCACHED_MAX_CACHED_TOKENS` | 两引擎 prefix cache 物理保留上限 | 默认 16000；先从 0 验证 |
| `KVCACHED_CONTIGUOUS_LAYOUT` | compound vs per-layer VA layout | CUDA 默认 true，ROCm 默认 false |
| `KVCACHED_IPC_TIMEOUT` | rank IPC 超时 | 默认 60 秒 |
| `KVCACHED_SANITY_CHECK` | 更强 ledger 检查 | 调试打开，生产评估开销 |

## 运维、故障与排查

| 症状 | 最可能原因 | 证据与动作 |
|---|---|---|
| 日志无 patch 信息，显存行为与原生相同 | `.pth` 未执行或只设置一个开关 | 检查 site-packages `kvcached_autopatch.pth`、两个 env，直接 import 后看 warning |
| 启动时报 block/page geometry 错误 | block/cell 超过或不整齐适配 VMM page | 记录 bytes/block，增大 `KVCACHED_PAGE_SIZE_MB`；不要绕过 guard |
| TP/PP 报 socket ENOENT/timeout | rank listener 尚未启动、IPC name/PP rank 不一致、socket 残留 | 检查 `/tmp/kvcached-tp-*`、device/rank 日志和 `KVCACHED_PP_SIZE` |
| 共享池耗尽导致请求等待 | 正常瞬时竞争或 prefix cache 占用 | 查看 `kvtop`、cached tokens、reserved pages；vLLM 应变成 scheduling miss而非崩溃 |
| 释放后 VRAM 没下降 | page 中仍有 live/cached block，或 reserve page保留 | 降 cache bound、trim、关 prealloc，对照 page occupancy |
| illegal memory access / 输出错误 | tensor stride/layout/backend 不匹配，或提前 unmap | 固定支持 backend/layout；检查 async barrier、hybrid/packed/quantized限制 |
| shutdown 后 `/dev/shm` 或 socket 残留 | 强杀进程或 teardown 未到 patch | 用 `kvctl delete` 谨慎清理明确实例；生产使用优雅退出和 Pod 生命周期清理 |
| SGLang leak detector 行为变化 | KVCacheD 只抑制其管理的 token/KV static-pool invariant | req_to_token_pool leak check仍应保留；不要把所有 leak 告警都归因于 elastic pool |
| vLLM memory profile 抖动 | 原生 whole-device delta 被共置进程干扰 | 确认 GPUWorker patch生效，优先使用进程本地预算/显式 startup plan |

安全边界：TP IPC 使用本机 Unix socket 和 Python pickle，假定同主机同信任域；能连接 socket 的恶意本地进程可能发送构造消息。`/dev/shm` control segment 和 `/tmp` socket 的权限、容器 IPC namespace、hostIPC 使用方式需要按多租户威胁模型加固。项目的目标是一致性和资源效率，不是 hostile multi-tenancy sandbox。

## 性能 / 资源开销

README 报告在 A100-80G 上共置三个 Llama-3.1-8B、间歇峰值 workload 时，KVCacheD 相对静态切分获得 2–28× TTFT 降低；这是特定 multi-model overprovisioning 场景，不应外推为单模型 kernel 加速。KVCacheD 不优化 attention FLOPs，收益来源是让空闲模型不长期占满 KV reservation，从而允许活跃模型得到更多 cache、减少排队/驱逐或避免额外 GPU。

成本包括：

- 首次触碰新 page 的 VMM map 延迟；reserve/prealloc 用少量 VRAM换掉部分热路径延迟。
- Python manager 的 page ledger 和 IPC；best-fit 当前为 O(available pages)，但按 page 而非按 block 运行。
- 多 TP/PP rank map/unmap 的 socket round trip 和 unmap 两阶段事务。
- contiguous layout 的 strided view 可能让某些 copy/PD/backend fast path不可用。
- prefix cache 为释放整页做 page-aware eviction，可能牺牲部分 LRU 命中率。
- large virtual tensor 占用 VA 而非等量 VRAM；仍需考虑设备 VA、driver handle和 tensor metadata上限。

应同时测：idle VRAM、峰值 VRAM、map/unmap p50/p99、TTFT/ITL、吞吐、prefix hit、page occupancy、reserve pages、allocation miss/preemption 和 shutdown cleanup，不能只看 `nvidia-smi` 某一时刻。

## Git 演进揭示的真实复杂度

2025-08 的自动 monkey patch 之后，项目持续增加：vLLM/SGLang 新版本签名兼容、MLA、PP、APC bound、hybrid linear/Mamba、ROCm、heterogeneous groups、NIXL、stable ABI、shared layer、packed KV、MRV2、async unmap fence、shutdown cleanup。2026-09 至 10 月的近期提交集中修复：

- SGLang 0.5.16+ allocator/capacity hook、SWA/hybrid pool、storage dtype、TP worker pool ownership。
- vLLM 0.28/0.29 MRV2、cross-layer sharing、hybrid block alignment、allocation retry state、async queued batch unmap。
- manager/tensor capacity 不一致导致越界 VMM map、prefix cache page-aware eviction、shared-memory/socket lifecycle。

这说明项目已从“替换一个 allocator”的原型演化成深度理解两套引擎内部 KV contract 的兼容层。理解和采用时必须同时保留两个结论：“零上游修改的接入体验”与“对上游内部实现的高版本耦合”。

## 与相关方案对比

| 维度 | KVCacheD | vLLM 原生 | SGLang 原生 | KV offload/connector | MIG/MPS/vGPU |
|------|-----------|-----------|-------------|----------------------|--------------|
| 主要对象 | GPU KV physical backing | 单引擎 KV block | 单引擎 token/radix KV | KV 内容跨 tier/node 搬运 | 整体 GPU 执行/显存资源 |
| 地址稳定、物理按需 | 是，GPU VMM | 通常启动时建真实 KV pool | 通常启动时建真实 KV pool | 取决于实现 | 不属于该抽象 |
| 多引擎同卡弹性 | 核心目标 | 通常静态预算 | 通常静态预算 | 不是主要目标 | 提供不同程度共享/隔离 |
| prefix metadata | 复用引擎并加 bound | block hash/APC | radix tree | 可保存/传输内容 | 无 |
| attention kernel | 复用原生 | 原生 | 原生 | 需 connector hook | 无关 |
| 隔离强度 | 协作式 KV 管理 | 进程内 | 进程内 | 系统依实现 | MIG最强，MPS/time-slice不同 |
| 集成成本 | monkey patch + layout/version测试 | 最低 | 最低 | connector/storage/network | 平台/调度/runtime配置 |
| 最佳场景 | 同卡多模型、间歇峰值、compound AI、训练推理共置 | 单模型高吞吐 | prefix-rich/复杂推理程序 | P/D、远端缓存、容量层级 | 多租户资源切分/执行共享 |

## 知识体系与阅读路线

### 六层知识模型

1. **推理服务语义层**：先掌握 prefill/decode、continuous batching、prefix cache、TP/PP，以及 KV 为什么随 sequence length 和并发增长。
2. **引擎逻辑缓存层**：分别理解 vLLM `Request → KVCacheManager → KVCacheCoordinator → BlockPool → block table`，以及 SGLang `Req → RadixCache → TokenToKVPoolAllocator → KVCache`。这一层管理“哪些逻辑槽属于谁”。
3. **KVCacheD 适配层**：理解 patch 如何保留引擎元数据契约，只替换 allocator 与 tensor allocation；重点比较 SGLang worker-local ownership 和 vLLM EngineCore/worker split ownership。
4. **弹性分配层**：理解 `KVCacheManager` 如何把 engine block 聚合到 VMM page，处理 best-fit、page occupancy、prefix eviction、limit resize、allocation rollback。
5. **GPU VMM 物理层**：理解 virtual address reservation、zero page、physical handle、map/unmap、contiguous compound page 与 per-layer layout。
6. **一致性与运维层**：理解 TP/PP 广播、transactional unmap、async release barrier、shared-memory limit、observability、shutdown cleanup 和版本矩阵。

不要从 patch 文件的某个函数开始硬读。先建立“引擎逻辑 block/token”和“KVCacheD physical page”是两个独立层次，再追踪一次完整 alloc/free，源码关系会清晰很多。

### 应能回答的关系问题

- 为什么创建“看起来占满 GPU 的 tensor”却不真的占满 VRAM？
- attention kernel 为什么无需修改？
- 一个 block free 后为什么显存可能不下降？
- prefix cache 和弹性为何天然冲突？
- vLLM 为什么需要 coordinator→worker IPC，而 SGLang 当前每个 TP worker本地管理？
- 为什么 unmap 比 map 更需要事务？
- 同一 GPU 上两个实例同时 alloc，`available_size` 为什么可能失效？系统如何恢复？
- contiguous layout 为什么映射简单，但与某些 backend、PD 或 ROCm 不兼容？
- KVCacheD 与 PagedAttention、RadixAttention、KV offload、MIG/MPS分别在哪一层？
- 什么情况下不应该采用 KVCacheD？

### 源码阅读顺序

1. `README.md` 与 `examples/01_simple_two_models`：建立使用目标。
2. `kvcached_autopatch.pth` → `autopatch.py` → `patch_base.py`：理解注入时机。
3. `vmm_ops.py` → `csrc/torch_bindings.cpp`：理解 Python/C++ API 边界。
4. `csrc/ftensor.cpp` → `allocator.cpp` → `page_allocator.cpp`：理解 VA、物理页和状态机。
5. `kv_cache_manager.py`：理解 block-to-page ledger、回滚、resize、retire。
6. `integration/sglang/interfaces.py` + `patches.py`，对照 SGLang `mem_cache/allocator/*`、`memory_pool.py`、`radix_cache.py`。
7. `integration/vllm/interfaces.py` + `patches.py`，对照 vLLM `block_pool.py`、`kv_cache_manager.py`、`gpu_model_runner.py`、`gpu_worker.py`。
8. `tp_ipc_util.py`：理解多 rank 事务和失败语义。
9. `mem_info_tracker` + `kvctl/kvtop` + controller：理解外部控制与运维。
10. tests 中按主题阅读：`test_alloc_rollback`、`test_tp_ipc_*`、`test_vllm_*`、`test_sglang_*`、`test_prefix_cache`、`test_*shutdown*`。

## 结论与选型

最佳适配场景是：同一 GPU 上长期驻留多个模型/服务，KV 需求呈错峰或突发，模型权重能同时容纳，而静态 KV reservation 是主要浪费；或者推理需与 fine-tuning/diffusion 等工作负载共置，并愿意固定引擎版本、跑完整 GPU correctness/regression。

不应把它当成引擎替代品、跨节点 KV 系统或安全隔离层。采用成本主要不是两条环境变量，而是验证 engine version × model attention type × backend × layout × TP/PP × cache policy 的组合。若团队能够承担这条兼容测试线，KVCacheD 提供了一个很有价值的系统能力：把 vLLM/SGLang 原本“启动时静态占有”的 KV cache，变成“地址稳定、物理按需、跨实例可调度”的 GPU 内存资源。
