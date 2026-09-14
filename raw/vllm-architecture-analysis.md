# vLLM 架构与设计思路分析

> 仓库：`/Users/zhenyu.jiang/vllm` · 分析日期：2026-09-14 · 版本：local HEAD `dc36fcce90`

## 一句话定位

[[vllm]] 是面向在线 LLM serving 的高吞吐推理引擎。它以 V1 Engine Core 为调度与执行中枢，用 PagedAttention 管理非连续 KV block，用 continuous batching、CUDA Graph/torch.compile、量化与并行通信把 GPU 计算、显存和网络带宽组合起来。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Client / OpenAI API                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ request / stream tokens
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / LLM entrypoint                                           │
│  request validation · tokenizer · output streaming · metrics          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ IPC / multiprocessing
┌──────────────────────────────▼───────────────────────────────────────┐
│ V1 Engine Core                                                        │
│  Scheduler ──► Sequence groups ──► KV cache manager / block table     │
│      │                         │                                      │
│      └──────────────► Model input / sampling metadata                 │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ collective / IPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU Worker(s): ModelRunner                                           │
│  embedding → transformer blocks → attention backend → logits         │
│       │              │                    │                           │
│       │              ├─ TP all-reduce / all-gather                     │
│       │              ├─ PP send / receive between layer stages         │
│       │              └─ EP all-to-all for MoE experts                   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / logprobs
┌──────────────────────────────▼───────────────────────────────────────┐
│ Detokenization / output processor ──► API stream                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要目录 / 文档 | 职责 |
|---|---|---|
| 接入层 | `vllm/entrypoints`, serving docs | OpenAI-compatible API、离线 LLM API、tokenize、流式输出 |
| 引擎与调度 | `vllm/v1`, `docs/design/arch_overview.md` | Engine Core、调度 token budget、请求生命周期、batch metadata |
| 内存层 | `docs/design/paged_attention.md`, `features/automatic_prefix_caching.md` | block allocator、block table、prefix hash、KV eviction/offload |
| 模型执行 | model runner、attention backends、model implementations | Transformer forward、sampling、speculative decoding |
| Kernel/编译层 | `docs/design/attention_backends.md`, `optimization_levels.md` | FlashAttention/FlashInfer/Triton/CUDA Graph、torch.compile、fused ops |
| 分布式层 | `distributed`, parallelism/data/expert deployment docs | TP、PP、DP、EP、通信 backend、跨节点部署 |

## 关键数据流

```
新请求
  │
  ├─ tokenize，计算 prompt token 与可复用 prefix hash
  │
  ├─ Scheduler 按 token budget 选择 waiting/running 请求
  │       ├─ 命中 block table → 只 prefill 未命中的 suffix
  │       └─ 未命中 → 分配 KV blocks；空间不足则 eviction / 等待
  │
  ├─ Prefill：批量处理 prompt，写入 paged KV cache
  │
  ├─ Decode：每轮为每条活跃序列生成一个 token；新序列可随时加入，完成序列释放 blocks
  │       └─ continuous batching + chunked prefill 平衡 TTFT 与 ITL
  │
  ├─ attention backend 通过 block table gather K/V，执行 fused attention
  │
  └─ logits → sampler → detokenize → stream；停止/异常时回收 sequence 与 KV blocks
```

PagedAttention 把每条序列的 KV cache 切成固定大小 block，逻辑 block 由 block table 映射到物理 GPU block，因此序列可增长、暂停和复用而不要求物理连续显存。Automatic Prefix Caching 对完整 KV block 做 hash，命中时复用；它不会改变采样结果，只减少重复 prefill。

## 设计决策与哲学

- **PagedAttention 优先解决显存碎片**：牺牲 block 粒度的边界灵活性，换取可预测的分配、共享与高并发。
- **调度以 token budget 为核心**：连续批不是固定 batch；每轮动态组合 prefill/decode，让短请求完成后立即补位，同时限制长 prompt 对 decode 的干扰。
- **计算与通信后端可替换**：attention backend、量化 kernel、collective、CUDA Graph 与 compile level 根据硬件/shape 选择，避免把单一 kernel 写死在引擎里。
- **并行策略按模型结构组合**：TP 切分层内权重，PP 切分层，DP 复制模型提升吞吐，MoE 用 EP 分布专家；不同轴的收益受通信拓扑和 batch shape 约束。

## 推理优化专题

### KV Cache

Paged KV 是“容量与碎片”优化；Prefix Caching 是“重复 prompt”优化；KV offload/connector 是“容量层级”优化。典型链路是 GPU block → CPU/远端存储 → 需要时异步加载。KV dtype 可用 FP8 等低精度降低容量，但要验证 attention 数值误差、scale 与硬件支持。

### 连续批处理

调度器把请求拆成可推进的 token 工作量，而不是等待整批完成。Prefill 更偏算力，decode 更偏带宽；chunked prefill 将长 prompt 分块，并与 decode 交错。优化目标应同时看 TTFT、ITL、吞吐、队列等待和 KV 使用率。

### 算子融合与张量执行

官方设计文档列出 attention backend、CUDA Graph、torch.compile fusion、RMSNorm/量化/ROPE/KV cache 写入及 Fused MoE modular kernel 等路径。融合减少 kernel launch、global-memory round trip 和中间 tensor；但动态 shape、稀疏路由、量化格式和 graph capture 会限制可融合范围。应按 prefill/decode、batch size、head size、GPU 架构分别 benchmark。

### TP / PP / EP / DP

| 并行 | 切分/复制对象 | 主要通信 | 适用重点 |
|---|---|---|---|
| TP | 每层权重、attention heads | all-reduce/all-gather | 单节点或高速互联上装下大模型 |
| PP | 不同 transformer layers | stage 间 send/receive | 跨节点、深而窄模型；需 micro-batch 降低 bubble |
| DP | 完整模型副本与请求 | 副本间通常独立；MoE 可能需对齐 | 模型能放入单副本、目标是吞吐 |
| EP | MoE experts | token dispatch/reduce 的 all-to-all | 专家权重很大、需要分摊 MoE 计算 |

vLLM 文档特别指出，DP+TP 时 attention 可在 DP 副本内使用 TP；启用 EP 后，MoE expert group 通常按 DP×TP 组织。DP 部署还需要考虑每个 rank 独立 KV cache 带来的 prefix locality 与负载均衡问题。

## 关键组件深入解读

### V1 Engine Core

V1 将 API/前端与 Engine Core、GPU worker 分开。Core 接收请求并维护 waiting/running 状态、调度预算、KV block 生命周期和输出；worker 只接收结构化 model input，在 GPU 上完成 forward 与 sampling，再返回 token/output。这个边界让调度策略、执行后端和进程模型可以分别演进，也为 DP coordinator、KV events 与 P/D disaggregation 留出接口。

### PagedAttention + Prefix Cache

Attention 不读取连续的 `[sequence, token, head, dim]` 大数组，而是依据 block table 找到物理 block 并执行 paged gather。Prefix cache 以 token prefix 与模型/LoRA 等上下文生成 hash，只有完整且可验证的 block 才能共享；因此 block size 是内存碎片、hash 开销、prefix 命中率之间的折中。

## 与 SGLang 对比

vLLM 的核心优势是成熟、通用的 block allocator 与广泛模型/部署生态；SGLang 以 radix tree 做 token 级 prefix sharing，更适合高度重复的结构化程序、agent prompt 和多轮共享前缀。两者都已扩展到量化、投机解码、P/D 分离及 TP/PP/DP/EP，实际选择应以 workload、硬件和 benchmark 为准。

## 来源

## 代码级关键流程

### 1. Engine Core → Scheduler → GPU Worker

关键入口：`vllm/v1/engine/core.py:589`、`vllm/v1/core/sched/scheduler.py:562`、`vllm/v1/worker/gpu_model_runner.py:4187`。

```text
EngineCore.step()
  ├─ scheduler.has_requests()
  ├─ Scheduler.schedule()
  │    ├─ new_step_starts()
  │    ├─ 先遍历 running requests
  │    ├─ 再从 waiting queue admission
  │    ├─ KVCacheManager.allocate_slots()
  │    ├─ 空间不足 → preempt lowest-priority / tail request
  │    └─ 生成 SchedulerOutput
  ├─ model_executor.execute_model(non_block=True)
  ├─ future.result() / sample_tokens()
  └─ scheduler.update_from_output()
```

V1 的核心抽象不是固定的 prefill/decode 两个 scheduler，而是每个 request 的 `num_computed_tokens` 追赶 `num_tokens_with_spec`。因此 chunked prefill、普通 decode、speculative decode 和未来的 jump decoding 都能落在同一个 `schedule()` 中。`token_budget` 控制本轮总 token，`input_budget` 约束 batch 输入；scheduler 先推进 running，再尝试 waiting admission。

### 2. KV Cache 分配、命中与抢占

关键入口：`vllm/v1/core/kv_cache_manager.py:370`、`vllm/v1/core/sched/scheduler.py:700-820`。

```text
waiting Request
    ↓ get_computed_blocks(request)
local prefix hit + external connector hit
    ↓
num_computed_tokens / shared_prefix_boundary
    ↓ allocate_slots(num_new_tokens, num_lookahead_tokens)
 ┌───────────────┴────────────────┐
 │ 有足够 block                   │ 无足够 block
 │ 返回 new_blocks                │ 选择 running victim
 │                                │ _preempt_request()
 └───────────────┬────────────────┘
                 ↓
SchedulerOutput.req_to_new_blocks
                 ↓
GPU ModelRunner 写入 KV block table
```

`allocate_slots()` 同时处理本地 prefix、connector 提供的 external KV、待计算 token 和 speculative lookahead token；这意味着 KV admission 与 scheduler admission 是一个原子决策，而不是“先排队、后发现显存不够”。vLLM 当前还支持 hybrid KV cache group、sliding window、Mamba state、KV connector watermark 和 DP 下的 dummy forward 协调。

### 3. ModelRunner 与 Attention Backend

`GPUModelRunner.execute_model()` 先同步/更新 persistent batch state，再调用 `_prepare_inputs()` 构造 token、slot mapping、block table 和 attention metadata，之后按 token 数、请求数、uniform decode、DP 等条件决定 eager/CUDA Graph/ubatching。模型层的 `Attention` 在 `vllm/model_executor/layers/attention/attention.py:225` 初始化时通过 `vllm.v1.attention.selector.get_attn_backend()` 选择 backend，具体 backend 再消费统一 metadata。

```text
SchedulerOutput
    ↓
_prepare_inputs()
    ├─ token ids / positions
    ├─ slot mapping / block table
    ├─ CommonAttentionMetadata
    └─ speculative metadata
    ↓
determine batch execution
    ├─ eager
    ├─ CUDA Graph
    └─ ubatching / DP synchronization
    ↓
Transformer Attention.forward()
    ↓ selected backend (FlashAttention / FlashInfer / Triton / ...)
    ↓ logits → proposer/target verify → sampler
```

这里的“算子融合”主要发生在 backend、compiled graph、quantization/fused MoE 和 cache write 路径；scheduler 不直接操作 kernel，只负责把动态请求压缩成 GPU 可消费的 metadata。

### 4. Speculative Decode

当前 vLLM V1 通过 `vllm/v1/spec_decode/*` 的 proposer 体系选择 EAGLE、DFlash、MTP、Medusa、N-gram、Suffix 等实现。scheduler 为 speculative lookahead 预留 KV slots，并在 `scheduled_spec_decode_tokens` 中携带已生成 draft；GPU runner 的 proposer 生成 draft，target model 在同一执行框架内验证，随后 scheduler 根据 accepted/rejected token 修正 request 的 computed token 数和 KV 状态。

```text
running request
    ↓ allocate main + lookahead slots
draft proposer
    ↓ draft tokens / draft KV
target model verify
    ↓ accepted prefix + rejected tail
update computed tokens / output placeholders
    ↓
next schedule()；只保留可验证 token 的 KV
```

### 5. P/D 与 KV Connector

KV connector 的统一接口在 `vllm/distributed/kv_transfer/kv_connector/v1/base.py:185`：scheduler 侧可调用 `get_num_new_matched_tokens()`，worker 侧调用 `start_load_kv()` / `wait_for_save()`，并通过 `KVConnectorMetadata` 把 transfer state 放入 `SchedulerOutput`。因此 P/D 分离、CPU offload、NIXL、Mooncake、LMCache 和其他 connector 共享同一条 scheduler/worker 边界。

### 6. TP / PP / EP / DP 的通信边界

并行初始化入口是 `vllm/distributed/parallel_state.py:1977`；基础 collective 通过 `vllm/distributed/communication_op.py:12-31` 暴露。模型层把这些原语封装进列并行/行并行 Linear（`vllm/model_executor/layers/linear.py:428`、`:1621`）、pipeline tensor dict send/recv（`vllm/v1/worker/gpu_worker.py:1179`、`:1216`）以及 MoE all-to-all（`vllm/model_executor/layers/fused_moe/all2all_utils.py`）。

```text
initialize_model_parallel(TP, PP, DP, EP)
          ↓ process groups / rank mapping
Transformer block
  ├─ ColumnParallelLinear → local shard
  │       └─ optional all-gather
  ├─ RowParallelLinear → local partial output
  │       └─ tensor_model_parallel_all_reduce
  ├─ PP stage boundary → send/recv intermediate tensors
  └─ MoE gate → expert token dispatch all-to-all
          ↓
logits / sampler → DP shard gather or rank-local result
```

DP 不是简单复制后完全独立：MoE/EP 需要 rank 对齐，DP attention 还可能要求空 rank 做 dummy forward；因此调度器、model runner 和 collective group 三者必须共同定义同步点。

## Attention 与并行的实现对比

vLLM 的 backend selector 偏向“按模型配置/硬件选择一个 AttentionBackend class，再由统一 metadata 执行”；TP/PP/EP 的通信更多下沉到 Linear、MoE、worker 和 parallel_state。SGLang 则显式把 `ForwardMode` 传入 backend，在同一个 runner 中按 EXTEND/DECODE/TARGET_VERIFY 切换子 backend，并把 DP attention/PP/EP 的状态放进 `ForwardBatch`/`ScheduleBatch`。

## vLLM 代码设计要点

- `Scheduler.schedule()` 把 token budget、KV capacity、prefix hit、preemption、spec lookahead 和 DP/encoder 限制汇总成一个输出对象。
- `KVCacheManager` 通过 coordinator/single-type managers 支持多种 KV cache group，而不是只维护一个简单 block pool。
- `Attention` 通过 selector/registry 选择 backend，模型实现可以针对 MLA、Mamba、cross attention 包装或替换底层 backend。
- `EngineCore` 可用 batch queue 把下一轮 scheduling 与上一轮 GPU future 重叠，形成 CPU/GPU pipeline。

## 代码级与 SGLang 的实现对照

| 维度 | vLLM | SGLang |
|---|---|---|
| 主循环 | `EngineCore.step()` 显式串起 schedule/execute/update | Scheduler event loop + `get_next_batch_to_run/run_batch/process_batch_result` |
| batch 状态 | `SchedulerOutput` + request 字段 | 大型 `ScheduleBatch`，由 mixin/组件持续变换 |
| 调度单位 | 每 request 的 computed token 追赶目标 token | batch 的 forward mode、request 队列与动态 chunk |
| KV 索引 | block table + block pool/coordinator | radix/unified tree + token pool / page allocator |
| Prefix sharing | hash 完整 block，connector 可提供 external hit | `match_prefix()` 最长 radix prefix，支持 token 边界 split |
| Spec decode | scheduler lookahead + v1 proposer/target verify | `BaseSpecWorker` + `SpecInput/spec_info` + target verify mode |
| backend 选择 | `get_attn_backend()` selector/enum/class | `ATTENTION_BACKENDS` registry + `get_attention_backend()`，还可按 forward mode 二次选择 |
| P/D | KVConnectorBase_V1 metadata/worker hooks | disaggregation mixin、DecodeRequest/receiver/transfer queue 与多种 backend |


- https://github.com/vllm-project/vllm/blob/main/README.md
- https://github.com/vllm-project/vllm/blob/main/docs/design/arch_overview.md
- https://github.com/vllm-project/vllm/blob/main/docs/design/paged_attention.md
- https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md
- https://github.com/vllm-project/vllm/blob/main/docs/configuration/optimization.md
- https://github.com/vllm-project/vllm/blob/main/docs/serving/data_parallel_deployment.md
- https://github.com/vllm-project/vllm/blob/main/docs/serving/expert_parallel_deployment.md
