---
title: KVCacheD × SGLang × vLLM 集成与实验手册
tags: [analysis, implementation, llm-inference, kv-cache, gpu-virtual-memory, operations]
date: 2026-10-02
sources: [src-kvcached-architecture, src-sglang-architecture, src-vllm-architecture]
related: [kvcached, sglang, vllm, elastic-kv-cache, kvcached-source-code-deep-dive, kvcached-sglang-vllm-knowledge-system]
---

# KVCacheD × SGLang × vLLM 集成与实验手册

本页把 [[kvcached-source-code-deep-dive]] 的实现知识转成可执行的学习和验证路径。目标不是给出一条“复制即可生产上线”的命令，而是让每一步都有可观察的系统假设、预期状态和失败解释。

## 1. 使用前的边界判断

先确认问题确实属于 [[elastic-kv-cache]]：

| 问题 | 若答案为“是” | 若答案为“否” |
|---|---|---|
| 同卡是否有两个以上模型/实例？ | 继续评估 | 单实例持续满载时收益可能有限 |
| 模型权重能否同时驻留？ | KV峰值可弹性共享 | 权重都放不下时，KVCacheD本身解决不了 |
| KV负载是否错峰或有空闲期？ | 有物理页回收机会 | 同时满峰仍受真实VRAM上限约束 |
| 是否愿意锁定engine版本？ | 可维护adapter矩阵 | rolling latest会带来高兼容风险 |
| 是否可以做GPU correctness测试？ | 可验证layout/lifetime | 只看启动成功不够安全 |

不要把下列目标误配给KVCacheD：

- 跨节点共享相同prefix内容：研究[[kv-cache-offload]]、KV connector和distributed serving。
- Kubernetes GPU allocation或强隔离：研究[[gpu-sharing]]、MIG、MPS、DRA/device plugin。
- 降低模型权重显存：使用量化、offload、sleep或模型并行。
- 提升单次attention kernel FLOPs：选择/优化FlashAttention、FlashInfer、Triton等backend。

## 2. 建立可复现版本清单

每次实验先记录：

```text
hardware
  GPU model / count / VRAM
  CUDA or ROCm driver/runtime

software
  PyTorch version and torch.version.cuda/hip
  KVCacheD package version + git commit
  vLLM or SGLang package version + git commit
  Python version

engine configuration
  model + revision
  dtype / quantization / KV dtype
  attention backend
  TP / PP / DP / EP
  block/page size
  prefix cache flags
  async scheduling / sleep mode / P-D connector

KVCacheD configuration
  IPC name
  VMM page size
  contiguous layout
  preallocation settings
  prefix cache bound
  memory limit
```

只写“vLLM latest + kvcached”无法复现实验。KV tensor layout 和runner选择可能在minor release间改变。

## 3. 环境准备

### 3.1 基础前提

当前KVCacheD build逻辑要求：

- Linux GPU环境；VMM核心不是macOS本地可执行路径。
- Python 3.9–3.13。
- PyTorch `>=2.10`，用于stable ABI build。
- CUDA或ROCm build能够提供对应VMM API。
- 目标vLLM/SGLang版本在adapter范围内。

### 3.2 安装顺序

```bash
# 1. 进入目标engine虚拟环境
source /path/to/venv/bin/activate

# 2. 先安装匹配GPU backend的PyTorch和engine
python -c 'import torch; print(torch.__version__, torch.version.cuda, torch.version.hip)'

# 3. 安装KVCacheD；build isolation会看不到已安装的torch，因此关闭
pip install kvcached --no-build-isolation

# 或源码开发安装
cd /path/to/kvcached
pip install -e . --no-build-isolation --no-cache-dir
```

如果构建报错，先分辨是哪一层：

| 错误位置 | 常见原因 |
|---|---|
| import torch失败 | 安装顺序错误或build isolation |
| stable ABI/version guard | PyTorch低于目标版本 |
| `libcuda`/CUDA headers | driver/toolkit/build环境不完整 |
| HIP symbols | ROCm/PyTorch backend不一致 |
| wheel安装后无`.pth` | 自定义packaging/install path没有把root data安装到site-packages |

### 3.3 验证自动注入文件

```bash
python - <<'PY'
import site
from pathlib import Path

for directory in [*site.getsitepackages(), site.getusersitepackages()]:
    path = Path(directory) / "kvcached_autopatch.pth"
    if path.exists():
        print(path)
PY
```

源码只在`PYTHONPATH`可见，不代表`.pth`会执行。`.pth`必须位于解释器启动时处理的site-packages目录。

## 4. 环境变量分层

### 4.1 生效开关

```bash
export ENABLE_KVCACHED=true
export KVCACHED_AUTOPATCH=1
```

- `KVCACHED_AUTOPATCH`：engine import时是否改class/function/alias。
- `ENABLE_KVCACHED`：patched wrapper运行时是否走elastic分支。

两者缺一都可能表现为“服务能启动，但实际仍走原生内存”。

### 4.2 资源域

```bash
export KVCACHED_IPC_NAME=my-serving-pool
```

IPC name影响：

- `/dev/shm` memory information/limit segment。
- TP/PP socket root的namespace。
- `kvctl`显示和控制目标。

同一物理共享域应使用明确、稳定且长度适中的名称。独立租户或实验需要不同名称，避免limit和socket相互影响。

### 4.3 VMM page与layout

```bash
export KVCACHED_PAGE_SIZE_MB=2
export KVCACHED_CONTIGUOUS_LAYOUT=true
```

规则：

- page size必须是2 MiB的正整数倍。
- block/super-cell大于page时必须增大page。
- NVIDIA/CUDA默认contiguous；ROCm默认non-contiguous。
- P-D/NIXL、per-layer pointer注册或特定backend可能要求non-contiguous。
- layout改变tensor stride，是correctness配置，不只是性能配置。

### 4.4 reserve与cache策略

```bash
export KVCACHED_PAGE_PREALLOC_ENABLED=true
export KVCACHED_MIN_RESERVED_PAGES=5
export KVCACHED_MAX_RESERVED_PAGES=10
export KVCACHED_MAX_CACHED_TOKENS=16000
```

实验阶段建议：

1. 先关闭prefix cache或将cached tokens设为0。
2. 验证基本map/unmap和输出正确。
3. 再逐步增加cache bound，观察命中率和mapped pages。
4. 分别开/关preallocation，量化首page latency和idle footprint。

## 5. 实验 1：确认没有“假启用”

### 5.1 vLLM 最小启动

```bash
export ENABLE_KVCACHED=true
export KVCACHED_AUTOPATCH=1
export KVCACHED_IPC_NAME=vllm-lab
export VLLM_USE_V1=1
export VLLM_ATTENTION_BACKEND=FLASH_ATTN

vllm serve "$MODEL" \
  --no-enable-prefix-caching \
  --port 12346
```

### 5.2 SGLang 最小启动

```bash
export ENABLE_KVCACHED=true
export KVCACHED_AUTOPATCH=1
export KVCACHED_IPC_NAME=sglang-lab

python -m sglang.launch_server \
  --model "$MODEL" \
  --disable-radix-cache \
  --trust-remote-code \
  --port 30000
```

### 5.3 成功证据

必须同时看到：

- PatchManager检测到正确engine版本。
- 成功patch列表包含对应allocator/pool/runner/worker组件。
- C++ PageAllocator打印合理的layers、page size、block capacity和layout。
- `kvctl list`出现该IPC segment。
- idle状态下KV physical bytes接近reserve页，而不是完整virtual KV容量。
- 请求输出与关闭KVCacheD的固定seed基线一致。

只看到服务端口ready不算验证成功。

## 6. 实验 2：单实例按需增长和回收

### 6.1 流量设计

按顺序执行：

1. 启动后不发请求，记录idle状态。
2. 发一个短prompt/短output请求。
3. 发长prompt或高`max_tokens`请求，使更多KV pages映射。
4. 请求完成后等待cache/free路径。
5. 重复相同请求，观察prefix cache关闭和开启时的差异。

### 6.2 观察命令

```bash
kvctl list
kvctl watch -n 1
kvtop
nvidia-smi --query-compute-apps=pid,used_memory --format=csv
```

### 6.3 应建立的因果关系

```text
longer active context / more concurrent tokens
  → more engine blocks/tokens
  → more KVCacheManager pages become occupied
  → more VMM physical mappings
  → mapped/used KV bytes increase

request completion
  → logical IDs released or cached
  → only fully empty pages become reclaimable
  → reserve/cache policy may keep part of memory mapped
```

如果请求结束后显存不降，不能直接判断leak。先查prefix ownership、page occupancy、reserve pages和async retirement。

## 7. 实验 3：两个同引擎实例共置

### 7.1 两个 vLLM

分别使用不同端口。是否使用相同IPC name取决于要测试的控制域：同名用于统一观察/limit语义，独立命名用于隔离实验；底层GPU physical headroom无论如何都由同一device竞争。

```text
phase A: instance 1 idle, instance 2 idle
phase B: only instance 1 peak
phase C: instance 1 drains, instance 2 peak
phase D: both peak
phase E: one process graceful shutdown
```

验证：

- A阶段不应各自长期占满完整KV reservation。
- B/C阶段physical capacity应随活跃实例迁移。
- D阶段总需求超过VRAM时应出现scheduler miss/preemption/等待，而非silent corruption。
- E阶段对应segment/socket被清理，其它实例继续工作。

### 7.2 两个 SGLang

重点观察每个worker本地pool ownership。TP>1时，不应把一个rank的local manager operation误广播给其它rank；日志中的pool和device必须与rank对应。

## 8. 实验 4：vLLM 与 SGLang 跨引擎共置

这是最能验证项目关系的实验：两者没有共享block table或radix tree，但会竞争同一GPU VRAM。

```text
vLLM instance
  BlockPool/APC metadata ──► its KVCacheManager ─┐
                                                ├─► same GPU physical headroom
SGLang instance                                 │
  RadixCache/token metadata ─► its KVCacheManager┘
```

测试阶段：

1. 两者prefix cache均关闭，建立纯allocation基线。
2. 交替流量，验证物理页能在两者之间复用。
3. 同时压力，观察两个scheduler如何分别处理allocation miss。
4. 只开vLLM APC，测其cached pages是否压缩SGLang headroom。
5. 只开SGLang RadixCache，做相反实验。
6. 两者均开cache并设置不同bound，观察公平性与尾延迟。

KVCacheD没有全局request priority scheduler。两个engine的公平性来自physical竞争、各自cache bound和外部limit配置，不应假设自动实现SLO公平。

## 9. 实验 5：prefix cache边界

### 9.1 三组设置

```text
KVCACHED_MAX_CACHED_TOKENS=-1
  unlimited; highest reuse potential, weakest elasticity

KVCACHED_MAX_CACHED_TOKENS=0
  immediate eviction after cache ownership becomes evictable

KVCACHED_MAX_CACHED_TOKENS=N
  bounded reuse; tune N against page occupancy and workload prefixes
```

### 9.2 流量

使用三类请求：

- 完全相同长system prompt。
- 共享大部分prefix、尾部不同。
- 完全不同prompt。

记录：prefix hit、prefill tokens、TTFT、mapped pages、eviction blocks/tokens、page occupancy。

### 9.3 解释差异

- vLLM APC通常在full logical block边界缓存；partial tail通常不能同样复用。
- SGLang RadixCache可按token或page-aligned边界split/match。
- KVCacheD physical page比两者logical unit大，一个cache entry可能只占page的一部分。
- page-aware eviction只在能清空整页时直接降低physical bytes。

## 10. 实验 6：动态memory limit

### 10.1 操作

```bash
kvctl list
kvctl limit "$IPC" 8G
kvctl limit-percent "$IPC" 25
```

命令格式以当前`kvctl help`为准。实验时逐步收紧，不要在未知pool上直接设极小值。

### 10.2 预期状态机

```text
limit revision increases
  → C++ resize watcher notices target
  → manager enters shrink state
  → new allocations avoid retired logical tail
  → running/cached blocks gradually release
  → empty/reserved pages unmap
  → effective capacity converges to target
```

limit不是强杀running request，也不会绕过prefix/cache ownership直接释放live page。收敛速度取决于流量、cache eviction和page fragmentation。

### 10.3 需要验证

- 收缩期间已有请求输出正确。
- 新请求在容量不足时进入engine正常backpressure/preemption路径。
- limit放宽后logical capacity可以恢复。
- resize中不存在超出FTensor reserved range的page id。

## 11. 实验 7：TP/PP

### 11.1 TP

启动TP=2或更高时，记录：

- rank → GPU device映射。
- worker socket path。
- 每次map的offset集合和rank response。
- 任一rank失败时其它rank的rollback。

vLLM的关键不变量：同一logical page在相关worker上必须全部mapped或全部unmapped。SGLang当前是每个worker local pool，各rank操作各自tensor。

### 11.2 PP

PP stage使用独立socket namespace。检查：

```text
pp0/w0.sock ...
pp1/w0.sock ...
...
```

coordinator `pp_rank=-1` 的map/unmap必须覆盖所有stage。测试一个stage listener缺失时，应得到明确失败而不是只更新部分stage。

### 11.3 async/queued execution

对于vLLM PP或async scheduler：

1. 制造长GPU batch。
2. CPU scheduler尽早逻辑free部分blocks。
3. 验证page进入retired而非立即unmap。
4. worker collective barrier完成后才physical release。

## 12. 实验 8：故障注入

### 12.1 map失败

可以通过测试stub或受控fault injection让一个target mapping失败。预期：

- 已成功target反向rollback。
- 已成功rank收到rollback。
- 若rollback完整，allocation失败但pool仍可继续。
- rollback不确定时page quarantine或pool fail-loud。

### 12.2 unmap prepare失败

预期：

- 已prepare worker保留physical handle。
- coordinator发送abort。
- worker恢复原mapping。
- 没有rank提前release handle。

### 12.3 commit响应丢失

预期：

- coordinator重试commit。
- worker根据finalized transaction幂等返回committed。
- 不允许从ambiguous commit回退abort。

### 12.4 进程退出

分别测试：

- graceful engine shutdown。
- SIGTERM。
- SIGKILL。
- worker在VMM handler中退出。

观察 `/dev/shm`、socket目录、GPU memory和其它实例健康。SIGKILL无法执行Python/C++ cleanup，需要外部生命周期清理策略。

## 13. 输出正确性验证

显存曲线正常不代表KV地址正确。至少做：

### 13.1 固定输出对照

同一model revision、prompt、seed、sampling参数，比较：

- KVCacheD关闭。
- KVCacheD开启、prefix关闭。
- KVCacheD开启、prefix开启。
- 单实例与共置压力。

允许的数值差异要符合backend/dtype已知行为，不能接受随机乱码、重复token、长上下文后漂移。

### 13.2 场景覆盖

- short/long prefill。
- long decode。
- request abort/preemption。
- prefix hit/miss。
- sliding window/hybrid attention。
- MLA或Mamba模型（若目标使用）。
- TP/PP。
- sleep/wake。
- P-D/NIXL（若目标使用）。

### 13.3 检测silent layout corruption

高风险信号：

- 只有某attention backend错误。
- 短上下文正常，跨block/page边界后错误。
- 只有odd page id、某layer或某KV group错误。
- prefix miss正常，prefix hit错误。
- Mamba state跨request复用后错误。
- async模式偶发，sync模式正常。

这些分别指向stride/compound offset、group geometry、cache ownership和unmap lifetime。

## 14. 性能实验设计

### 14.1 不要只测平均吞吐

建议指标：

| 类别 | 指标 |
|---|---|
| 服务体验 | TTFT p50/p95/p99、ITL、E2E latency、throughput |
| KV逻辑层 | allocated blocks/tokens、prefix hit、evictions、preemptions |
| VMM层 | mapped/reserved/free/quarantined pages、map/unmap latency |
| GPU层 | process VRAM、device free memory、SM utilization |
| 稳定性 | allocation misses、IPC timeouts、rollback、failed transactions |

### 14.2 对照组

```text
A: engine native static memory split
B: KVCacheD, prealloc off, prefix off
C: KVCacheD, prealloc on, prefix off
D: KVCacheD, bounded prefix cache
E: KVCacheD, unlimited prefix cache
```

### 14.3 工作负载

- steady single model：证明KVCacheD自身开销。
- alternating peaks：证明跨模型弹性。
- simultaneous peaks：暴露真实physical上限和backpressure。
- prefix-heavy：测cache bound trade-off。
- highly fragmented request lengths：测page occupancy。
- burst after idle：测preallocation对cold map latency影响。

README的2–28× TTFT是特定A100-80G三模型间歇峰值实验。复现时必须保留其workload结构，不能当作任意模型的固定加速倍数。

## 15. 版本升级流程

升级vLLM/SGLang时按以下顺序：

### 15.1 静态差异

检查上游是否改变：

- patch target module/class路径。
- constructor/method signature。
- allocator/pool alias被捕获的import时机。
- KVCacheConfig/spec/group结构。
- block size与kernel block size。
- tensor shape/stride/layout。
- runner默认选择。
- prefix cache/ref count/null block contract。
- worker/executor/shutdown lifecycle。

### 15.2 patch coverage

确认每个注册patch：

- version range包含目标版本。
- `can_apply`找到目标class。
- patch marker正确。
- 成功日志不是“部分成功后静默fallback”。
- 不兼容runner/layout能fail early。

### 15.3 回归层级

```text
CPU unit tests
  → single-GPU allocation/layout tests
  → engine smoke inference
  → prefix/hybrid/model-specific tests
  → TP
  → PP/async
  → dual-instance contention
  → shutdown/fault injection
```

不要从“server能启动”直接跳到生产共置。

## 16. 常见故障决策树

```text
服务启动失败
├─ 没有patch日志
│  ├─ .pth不存在/未执行
│  └─ AUTOPATCH开关未设
├─ patch target missing
│  └─ engine版本超出adapter或上游模块移动
├─ geometry/layout error
│  ├─ block > VMM page
│  ├─ num_layers/buffers与tensor不一致
│  └─ backend layout/packed/inline-scale不支持
└─ worker socket错误
   ├─ IPC name不一致
   ├─ rank/device错误
   └─ PP namespace/listener未ready

运行时错误
├─ allocation miss
│  ├─ 正常物理竞争 → scheduler retry
│  └─ prefix cache/reserve占用过高
├─ 显存不回收
│  ├─ live/cached block
│  ├─ partial page occupancy
│  ├─ reserve page
│  └─ async retired page
├─ illegal memory access
│  ├─ stride/layout错误
│  └─ premature unmap
└─ 输出错误
   ├─ K/V offset或kernel-block geometry
   ├─ hybrid group/shared layer绑定
   └─ Mamba state/partial-tail处理
```

## 17. 扩展一个新engine版本的方法

1. 找到logical allocator seam：谁决定block/token ID ownership。
2. 找到KV tensor seam：谁创建实际GPU storage，谁保存view。
3. 写最小adapter，先只支持MHA、单GPU、prefix关闭。
4. 明确null/padding block契约。
5. 建立engine block bytes到VMM page geometry。
6. 保持上游scheduler的allocation miss语义。
7. 再增加prefix cache，复制其hash/ref/eviction contract。
8. 再增加TP/PP，定义coordinator和CUDA-context owner。
9. 再增加async lifetime fence。
10. 最后扩展MLA/hybrid/Mamba/packed/quantized/P-D。

每一步都应有fail-loud guard。不要让不支持的layout悄悄落回一半原生、一半KVCacheD的状态。

## 18. 学习完成标准

能够独立完成以下任务，才算真正理解三项目关系：

- 从一次vLLM `allocate_slots`追到`FTensor::map`，再追free/unmap返回。
- 从SGLang `RadixCache.match_prefix`解释哪些token需要新physical backing。
- 根据model KV shape手算block bytes、blocks/page和compound offset。
- 解释为什么logical free不能保证physical allocation成功。
- 解释为什么vLLM需要worker IPC而SGLang当前采用worker-local manager。
- 从日志区分资源压力、配置不兼容和state consistency failure。
- 设计一组能发现premature unmap和stride corruption的测试。
- 在升级engine后列出必须复核的patch targets和数据契约。

## 相关入口

- 三项目知识体系：[[kvcached-sglang-vllm-knowledge-system]]
- 源码逐函数深潜：[[kvcached-source-code-deep-dive]]
- 完整架构分析：[[src-kvcached-architecture]]
- 项目边界：[[kvcached]]、[[vllm]]、[[sglang]]
- 核心概念：[[elastic-kv-cache]]
