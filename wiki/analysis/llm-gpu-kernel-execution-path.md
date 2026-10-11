---
title: LLM 推理 GPU 执行路径：从 Framework Op 到 CUDA Kernel 与 SM
tags: [analysis, llm-inference, gpu, cuda, kernel, tensor-core, performance]
date: 2026-10-11
sources: []
related: ["[[llm-inference-request-lifecycle]]", "[[vllm-gpu-execution-path]]", "[[sglang-gpu-execution-path]]", "[[gpu-programming-learning]]", "[[paged-attention]]", "[[radix-attention]]", "[[kv-cache-offload]]", "[[disaggregated-serving]]"]
---

# LLM 推理 GPU 执行路径：从 Framework Op 到 CUDA Kernel 与 SM

本页接住 [[vllm-gpu-execution-path]] 与 [[sglang-gpu-execution-path]] 的下半段：ModelRunner 已经决定这一 iteration 要算哪些 token、使用哪些 KV page 和并行 rank，随后这些高层 tensor 运算如何变成 CUDA/Triton/custom kernels，最终由 NVIDIA GPU 的 SM、warp、Tensor Core、CUDA core 与内存系统执行。

“落到 CUDA 核心”是一个容易误导的说法。LLM 的大矩阵主计算通常尽量进入 Tensor Core 的 MMA pipeline；地址计算、激活、归一化、部分 reduction 和控制逻辑可能使用 CUDA cores；数据搬运依赖 LD/ST、copy engine、cache 和 HBM；跨 GPU 通信通常由 NCCL kernels 与互连共同完成。必须同时看 compute、memory、launch 与 communication。

## 核验快照与证据边界

核验日期：2026-10-11。官方材料与代码锚点如下：

| 证据 | 固定版本或入口 | 本页用途 |
|---|---|---|
| [CUDA Programming Guide](https://docs.nvidia.com/cuda/cuda-programming-guide/) | live docs，2026-10-11 访问 | programming model、thread hierarchy、memory、graphs |
| [PTX ISA](https://docs.nvidia.com/cuda/parallel-thread-execution/) | live docs，2026-10-11 访问 | warp-level 指令、memory space、MMA 语义 |
| [Nsight Systems](https://docs.nvidia.com/nsight-systems/UserGuide/) | live docs，2026-10-11 访问 | CPU/GPU timeline、launch gap、stream/collective overlap |
| [Nsight Compute](https://docs.nvidia.com/nsight-compute/NsightCompute/) | live docs，2026-10-11 访问 | 单 kernel memory/compute/occupancy 分析 |
| [NCCL](https://github.com/NVIDIA/nccl/tree/3e46c089f4ae4732722a419eb6096aead7e47a30) | `3e46c089f4ae4732722a419eb6096aead7e47a30` | collective 与 transport 边界 |
| [NIXL](https://github.com/ai-dynamo/nixl/tree/b69182fe73ac64221dcdbeeee744161f76006dda) | `b69182fe73ac64221dcdbeeee744161f76006dda` | P/D KV bulk transfer 边界 |
| [vLLM](https://github.com/vllm-project/vllm/tree/276fbcff2717bd934cfa37c8a2e4c391f3e7237b) | `276fbcff2717bd934cfa37c8a2e4c391f3e7237b` | custom ops、attention、MoE 示例 |
| [SGLang](https://github.com/sgl-project/sglang/tree/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b) | `e328c7ecbd69ebf77f38db9aa64eecefd760fe4b` | AOT/JIT CUDA kernels、Triton/backend 示例 |

本页解释稳定的 CUDA 执行模型，并用固定 commit 的代码目录说明 engine 如何接入；不声称某个模型、dtype、GPU 架构必然选中同一个 kernel。实际 backend 由模型结构、shape、dtype、量化格式、GPU compute capability、编译配置和运行时选择共同决定。

## Host 到 Device

Python 调用不是直接“在 GPU 上执行 Python”。Framework 先选择 eager、compiled graph 或 custom op，再由 host 准备参数并把 kernel work enqueue 到 CUDA stream。Launch 通常是异步的：CPU 返回只表示工作已经排入队列，不表示 GPU 已经完成。

```text
[CPU: Python]
Model layer / attention backend / fused op wrapper
       │ Python/C++ binding
       ▼
PyTorch dispatcher
       ├── ATen/CUDA implementation
       ├── torch.compile generated graph/kernel
       ├── Triton JIT kernel
       └── custom C++/CUDA extension / CUTLASS / FlashAttention
       │ resolve pointers · shapes · strides · dtype · stream
       ▼
[CPU: CUDA Runtime / Driver]
kernel launch descriptor
  function + gridDim + blockDim + sharedMemBytes + arguments + stream
       │ enqueue; host normally does not wait
       ▼
[GPU: stream queue]
dependency satisfied ──► blocks become eligible ──► SM executes warps
       │
       ▼
output tensor / event; later consumer observes stream ordering
```

### 三种常见提交形态

| 形态 | Host 做什么 | GPU 看见什么 | 主要代价/约束 |
|---|---|---|---|
| Eager | 每个 op 单独 dispatch/launch | 多个独立 kernels | 灵活；CPU dispatch 与 launch gap 可能明显 |
| `torch.compile` | 捕获/编译可优化的 op graph | 融合或重排后的 kernels | graph break、动态 shape、编译缓存决定收益 |
| CUDA Graph replay | 预先 capture 稳定 launch DAG，运行时更新有限参数并 replay | 已记录的 kernel/memcpy 节点序列 | shape/地址/控制流约束；减少 launch overhead，不减少数学工作 |

```text
CPU thread:  prepare ─ launch K1 ─ launch K2 ─ launch K3 ─ next iteration
CUDA stream:          [ K1 compute ][ K2 ][      K3 compute      ]
                      ▲ enqueue 早于执行完成

sync/event:                                      │ record event
other stream:                                    └──wait──► [consumer]
```

同步来源包括同一 stream 的先后顺序、显式 event、跨 stream wait、collective completion、host-side synchronize，以及 framework 为数据依赖插入的 barrier。随意添加全局 synchronize 会消除 overlap；缺少必要同步则可能让 consumer 读取尚未完成的 KV/activation。

## Grid、Block、Warp 与 SM

一个 kernel launch 产生 grid；grid 由 thread blocks（也称 CTA）组成；block 被放到某个 SM 上，block 内线程以 warp 为基本执行批次。NVIDIA CUDA warp 通常包含 32 threads。多个 block 可以驻留同一 SM，前提是 registers、shared memory、thread slots 和硬件上限允许。

```text
Kernel Grid
┌──────────────────────────────────────────────────────────────┐
│ Block(0)   Block(1)   Block(2)   ...   Block(N-1)           │
└────┬──────────┬──────────┬───────────────────────────────────┘
     │ schedule │          │
     ▼          ▼          ▼
┌──────────── GPU ─────────────────────────────────────────────┐
│ SM0                         SM1                         ...   │
│ ┌───────────────┐           ┌───────────────┐                 │
│ │ resident CTA0 │           │ resident CTA2 │                 │
│ │ warp0..warpW  │           │ warp0..warpW  │                 │
│ ├───────────────┤           ├───────────────┤                 │
│ │ resident CTA1 │           │ resident CTA3 │                 │
│ └───────────────┘           └───────────────┘                 │
│ warp scheduler → ready warp → issue to MMA/CUDA/LD-ST/SFU    │
└──────────────────────────────────────────────────────────────┘
```

线程多不等于同时执行更多。Block 是调度和共享内存边界，warp 是 SIMT issue 单位；一个 warp 中的分支分歧会让不同路径分阶段执行。Kernel 的可用并行度要足以填满多个 SM，同时 tile 又要复用数据，否则 launch 了很多线程仍可能被 HBM 或同步限制。

### Residency 与 occupancy

```text
每个 SM 的固定预算
  registers     shared memory     warp slots     block slots
      │              │                │              │
      └──────────────┴─────────┬──────┴──────────────┘
                               ▼
                     每个 block 的资源需求
                               │
                               ▼
              能同时 resident 的 blocks / active warps
                               │
                               ▼
                         theoretical occupancy

active warps --hide latency--> issue pipelines
      但过高 occupancy 不自动等于更高性能；tile reuse / ILP 也重要
```

Register 使用过多可能降低 resident warps，甚至发生 register spilling；shared memory tile 过大也会限制同时驻留 block 数。反过来，盲目缩小 tile 可能降低数据复用或 Tensor Core 效率。occupancy 是诊断信号，不是单独优化目标。

## GPU 内存层级

下面是逻辑视图，不按具体 GPU 给出固定容量和带宽；这些数值随架构、SKU 与配置变化。

```text
Host memory / remote GPU / storage tier
          │ PCIe / NVLink / RDMA / copy engine / transport
          ▼
┌──────────────────── Device ──────────────────────────────────┐
│ HBM / global memory                                         │
│ weights · KV cache · activations · block tables · outputs   │
│          │ cache line / transaction                          │
│          ▼                                                   │
│ Shared L2 cache  ←── peer/collective traffic may interact   │
│          │                                                   │
│          ▼                                                   │
│ Per-SM L1 / shared memory                                   │
│ shared: programmer/compiler managed tile + synchronization   │
│          │                                                   │
│          ▼                                                   │
│ Registers per thread                                        │
│ fragments · accumulators · addresses · scalars              │
│          │                                                   │
│          ├──► Tensor Core MMA pipeline                       │
│          ├──► CUDA core scalar/vector arithmetic             │
│          └──► LD/ST and special-function pipelines           │
└──────────────────────────────────────────────────────────────┘
```

关键区别：

- HBM 容量大，是 weights/KV/activation 的长期设备存储，但访问延迟和能耗高于片上存储。
- L2 在 SM 之间共享，能减少重复 HBM transaction；命中行为受访问模式与并发影响。
- shared memory 位于 SM 上，由同一 block 的 threads 协作复用，常承载 GEMM/attention tile。
- register 是每 thread 私有的最快状态，常保存 MMA fragment、partial sums 和地址。
- coalescing、alignment、vectorized access 与 contiguous tile 决定一个 warp 的访存能否合并成高效 transaction。

### KV cache 如何成为物理读取

[[paged-attention]] 或 [[radix-attention]] 描述的是逻辑组织和复用语义；kernel 最终仍要把逻辑 token/head 映射到 device address。

```text
request / sequence
      │ logical token position
      ▼
block table / page table / slot mapping
      │ block id + offset + layer/head/layout
      ▼
base pointer + stride/address calculation       [CUDA cores / integer units]
      │
      ▼
global load from KV pages                       [LD/ST → L2/HBM]
      │ stage/reorder if backend requires
      ▼
register/shared-memory tile
      │
      ▼
Q·Kᵀ / softmax / P·V                            [Tensor Core + CUDA/reduction]
```

Prefix 命中只说明部分 KV 已存在；它不保证地址连续、cache line 命中或 decode worker 已能读取。跨 worker P/D 还必须先完成 payload transfer 与 readiness 同步。

## Tensor Core 与 CUDA Core

Tensor Core 面向矩阵乘加（MMA）及特定 dtype/tile；CUDA cores 更适合普通标量/向量算术和控制相关工作。实际 kernel 会把它们与 LD/ST、special-function、shared-memory pipeline 组合起来，而不是只选择一种单元。

```text
                     one fused/model kernel
global memory
   │ LD/ST: load tiles, indices, scales, masks
   ▼
shared memory / registers
   ├── address/index/bounds ──► CUDA cores / integer pipeline
   ├── dequant/activation ────► CUDA cores or specialized fused instructions
   ├── matrix fragments ──────► Tensor Core MMA
   ├── exp/softmax/reduction ─► SFU + CUDA/reduction pipeline
   └── result store ──────────► LD/ST → L2/HBM
```

典型归属不是绝对规则：

| 工作 | 常见主要单元 | 仍需配合 |
|---|---|---|
| QKV/MLP GEMM | Tensor Core MMA | LD/ST、shared/register pipeline、epilogue |
| RMSNorm / elementwise activation | CUDA/vector pipelines | reduction、HBM/L2 |
| RoPE | CUDA/vector + transcendental/lookup | LD/ST |
| FlashAttention | Tensor Core MMA | online softmax reduction、shared/register、LD/ST |
| Paged decode attention | MMA 或 vector dot，取决于 backend/shape | page addressing、KV gather、reduction |
| Sampling | reduction/sort/top-k/top-p、RNG | GPU 或 CPU 路径取决于实现 |
| NCCL collective | communication kernels | NVLink/PCIe/network transport、copy/SM resources |

因此“Tensor Core 利用率不高”不一定异常：小 batch decode、memory-bound KV gather、sampling 或 communication 本来就不以大 GEMM 为主。反之，GPU busy 也不等于 Tensor Core 饱和。

## Transformer 单层 Kernel 序列

下图展示 decoder-only Transformer 的典型 dense layer。实际实现可能融合、重排或替换算子，MoE 还会插入 router、dispatch、grouped GEMM 和 combine。

```text
hidden states [tokens, hidden]
  │
  ├── RMSNorm kernel
  │      load → reduce(sum squares) → rsqrt/scale → store/fuse
  ▼
QKV projection GEMM                         [Tensor Core MMA]
  │ optional bias/quant epilogue
  ├── RoPE kernel / fused QK norm+RoPE       [CUDA/vector]
  ├── write K,V into paged/radix KV cache   [LD/ST]
  ▼
Attention
  Q·Kᵀ → scale/mask → online softmax → P·V   [MMA + reduction + memory]
  ▼
Output projection GEMM + TP collective      [MMA + NCCL if TP]
  ▼
residual add / RMSNorm                       [vector/reduction]
  ▼
Gate+Up projection GEMM                      [MMA]
  ▼
SwiGLU activation / multiply                 [CUDA/vector; often fused]
  ▼
Down projection GEMM + TP collective         [MMA + NCCL if TP]
  ▼
residual / next layer
```

### 单 token decode 时间线

Decode 每个 request 每轮通常只新增一个 token，但 continuous batch 会把多个 sequences 合并。与 prefill 相比，矩阵的 `M` 维可能更小，KV 读取随上下文增长，因而更容易受 memory bandwidth、launch gap 和 collective latency 影响。

```text
CPU scheduler     build batch | metadata H2D | wait/result | update requests
CUDA compute      [embed/norm][QKV][paged decode attention][MLP][logits][sample]
NCCL stream                    [AR/AG]                 [AR/AG]
KV memory                            <------ read historical K,V ------>
                                             │ write new K,V slot
                                             ▼
output token      <-------------------- device/host handoff ------------

next iteration    scheduler admits/continues/finishes sequences → repeat
```

若启用 CUDA Graph，`[QKV]...[sample]` 的一部分 launch DAG 可能 replay；动态请求集合、token 数、MoE routing 或不受支持的 op 可能触发不同 capture size 或 eager fallback。

### MoE 插入的额外路径

```text
hidden
  ──► router logits ──► top-k experts
       │
       ├── local reorder / permute
       ├══► EP all-to-all / dispatch (跨 rank 时)
       ▼
   grouped GEMM per expert
       │ activation / second grouped GEMM
       ├══► EP combine / all-to-all
       ▼
   weighted combine ──► output
```

MoE 可能同时受不均衡 expert load、small expert batch、dispatch bandwidth 和 grouped GEMM efficiency 限制。只看总 FLOPs 会漏掉 token permutation 与 collective。

## GEMM Tiling

大型 GEMM 不会让每个 thread 独立从 HBM 读取完整矩阵。高性能实现把输出矩阵分成 CTA tiles，再分给 warps/MMA fragments，通过多级 tile 和 pipeline 复用输入。

```text
C = A × B

Global/HBM:     A tiles                          B tiles
                   │ async/coalesced load           │
                   └──────────────┬──────────────────┘
                                  ▼
Shared memory:        CTA tile A_s × B_s
                      double/multi-stage buffers
                                  │ cooperative load
                ┌─────────────────┼─────────────────┐
                ▼                 ▼                 ▼
Registers:   warp tile 0       warp tile 1       warp tile N
                │ MMA fragments    │                 │
                └─────────────────┬─────────────────┘
                                  ▼
Registers:              accumulated C fragments
                                  │ epilogue: scale/bias/activation/quant
                                  ▼
Global/HBM:                   output C tile
```

设计目标是让每个从 HBM 取入的元素参与多次 MMA，并让 load 与 compute pipeline 重叠。约束来自：

- tile 必须匹配 dtype、Tensor Core instruction shape 与 layout；
- shared memory banking/alignment 会影响 load；
- register accumulator 太大会压低 occupancy；
- 小矩阵、小 batch 或尾块降低 tile 利用率；
- quantized GEMM 还需 scales、zero points、unpack/dequant 与特定 epilogue。

## Attention Tiling

Flash-style attention 避免把完整 score matrix 写回 HBM。它分块读取 Q/K/V，在 registers/shared memory 内维护 online softmax 状态，并累积输出。

```text
Q tile resident in registers/shared
        │
        │     for each K,V tile
        ▼
┌───────────────────────────────────────────────────────────────┐
│ load K tile ──► Q·Kᵀ MMA ──► mask/scale                      │
│                                  │                            │
│                                  ▼                            │
│ previous (m,l) + tile scores → online max/sum update         │
│                                  │                            │
│ load V tile ──► probability·V MMA ──► rescale output accum   │
└───────────────────────────────┬───────────────────────────────┘
                                │ repeat without materializing S
                                ▼
                         normalize + store O tile
```

Prefill 有较大的 query tile 和更多并行 work；decode query length 常为 1，历史 KV 很长，backend 会采用不同 layout、split-K/reduction 或 paged gather 策略。Paged/Radix cache 改变 K/V 的定位方式，Flash-style tiling 决定一次加载与计算多少数据；二者不是同一概念。

## CUDA Graph

CUDA Graph 优化 host submission，不替代 scheduler，也不改变模型数学。

```text
首次 capture / warmup
CPU: dispatch K1 ─ K2 ─ K3 ─ NCCL? ─ K4
                     │ capture stable DAG
                     ▼
GraphExec: [K1]→[K2]→[K3]→[K4] + fixed dependencies

后续 replay
CPU: prepare dynamic buffers/params ──► graphLaunch
GPU: [K1]→[K2]→[K3]→[K4]
     ^ fewer individual host launch gaps; same kernel work remains

shape/control mismatch ──► choose another captured graph OR eager path
```

Serving engine 常按 batch/token shape 维护 capture variants。Graph replay 的收益在短 decode iteration 尤其明显，因为 host launch overhead 占比可能更高；但动态 shape、conditional path、MoE routing、某些 collective/custom op 会限制捕获范围。

## Kernel Fusion

Fusion 的主要收益常是少一次 HBM round trip 和少一次 launch，而不只是“少一个函数”。

```text
Unfused:
HBM ─load─► RMSNorm ─store─► HBM ─load─► Quantize ─store─► HBM
                 kernel 1                     kernel 2

Fused:
HBM ─load─► [RMSNorm + Quantize in registers/shared] ─store─► HBM
                         one kernel
```

但 fusion 不是越大越好：

- live values 增多会提高 register pressure；
- 更大 shared memory 或更长代码可能降低 occupancy / instruction cache efficiency；
- 动态分支和 shape 让通用 fused kernel 难以保持所有 case 高效；
- fusion 可能减少 framework 可调度点，使 overlap 或复用变难；
- 数值顺序变化必须验证精度。

分析时应比较 bytes moved、launch count、achieved bandwidth、Tensor Core utilization、registers/thread、shared memory/block 与 active warps，而不是只看 kernel 数量。

## NCCL 与 NIXL

NCCL 和 NIXL 位于不同抽象：NCCL 面向 rank 间 collective；NIXL 面向内存区域间的数据移动/transport abstraction。两者都可能使用 NVLink、PCIe 或网络，但不能互换为“attention kernel”。

```text
Tensor Parallel / Expert Parallel                         P/D KV transfer

[GPU rank 0] activation                                  [Prefill GPU]
      │                                                       │
      ├══ NCCL all-reduce / all-gather / all-to-all           │ register/export memory
      │   ring/tree/transport kernels                          │ metadata ──► coordinator
      ▼                                                       ├══ KV payload
[GPU rank 1..N] synchronized tensor                            │   NIXL/IPC/RDMA/backend
                                                              ▼
                                                        [Decode GPU/cache]
                                                              │ readiness/event
                                                              └──► decode attention
```

### 通信与计算重叠

```text
compute stream: [layer compute]──event──►[independent compute]────wait──►[consumer]
                                      │                         ▲
comm stream:                          └──►[NCCL collective]────┘

P/D control:   route/handoff metadata ───────────────────────────────►
P/D data:      KV region transfer ═══════════════════════════════════►
decode stream:                                             wait ready [attention]
```

真正的 overlap 要有独立 work、正确 stream/event dependency，以及足够的 SM、copy/transport 和内存带宽资源。NCCL kernels 也可能占用 SM 或内存带宽，与计算竞争；“不同 stream”并不保证硬件并行。

## 性能观测

应先用 Nsight Systems 找“时间去哪了”，再用 Nsight Compute 看关键 kernel 为什么慢。Engine metrics、DCGM 和 request trace 用来把用户 SLO 与 GPU timeline 对齐。

```text
Request symptom
     │
     ├─ queue / CPU gap / launch gap?
     │      └── Nsight Systems + engine trace
     │
     ├─ one kernel dominates?
     │      └── Nsight Compute
     │          ├─ memory throughput / cache / transactions
     │          ├─ Tensor Core / instruction mix
     │          ├─ stalls / dependency / synchronization
     │          └─ register/shared-memory/occupancy
     │
     ├─ collective or transfer dominates?
     │      └── NCCL/NIXL trace + topology + network counters
     │
     └─ system saturation / thermal / errors?
            └── DCGM / GPU telemetry
```

| 现象 | 优先检查 | 不应直接下的结论 |
|---|---|---|
| TTFT 高 | gateway/queue、prefill tokens、GEMM/attention、P/D transfer/readiness | “GPU 算得慢” |
| ITL 高或抖动 | batch composition、decode attention、launch gap、collective、preemption | “一定是 KV cache miss” |
| GPU busy 高 | kernel timeline 与 instruction/memory mix | “Tensor Core 已吃满” |
| HBM throughput 高 | KV/weight bytes、cache hit、coalescing、fusion | “算力不足” |
| occupancy 低 | registers、shared memory、block size、可用 parallel tiles | “occupancy 拉满就会快” |
| NCCL 时间长 | message size、collective、rank placement、NVLink/PCIe/NIC topology | “网络带宽标称值不够” |
| launch gap 多 | CPU scheduling、Python/C++ dispatch、graph capture/replay 命中 | “需要更大的 batch” |

### 从 SLO 映射到 GPU 时间

```text
TTFT
├─ L0–L3: gateway + routing + admission + queue
├─ L4: schedule + prefix/KV allocation
├─ L5–L8: prefill kernels + collectives
├─ P/D only: KV transfer + readiness
└─ first decode/sample + stream encode

ITL / TPOT
├─ scheduler gap / batch wait
├─ one decode model iteration
│  ├─ KV reads + attention
│  ├─ GEMM / MoE
│  └─ TP/EP collectives
├─ logits / sampling
└─ output handoff
```

## 从引擎页进入本页时要携带什么

从 vLLM 或 SGLang 下钻时，至少带上以下上下文，否则“看 kernel”很难解释系统行为：

1. 当前是 prefill、chunked prefill 还是 decode；
2. scheduled tokens、sequences 与 batch shape；
3. model、dtype、quantization、attention/MoE backend；
4. KV layout、block/page table 与 prefix hit；
5. TP/PP/EP/DP ranks 及 topology；
6. eager、compiled 或 CUDA Graph replay；
7. 是否存在 NCCL collective 或 P/D KV transfer dependency。

完整上游入口见 [[llm-inference-request-lifecycle]]。逻辑 KV 管理分别参考 [[paged-attention]]、[[radix-attention]] 和 [[kv-cache-offload]]；本页只解释这些抽象最终如何转化为 address、memory transaction、kernel 和同步关系。
