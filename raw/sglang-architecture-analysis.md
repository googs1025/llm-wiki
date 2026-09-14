# SGLang 架构与设计思路分析

> 仓库：`/Users/zhenyu.jiang/sglang` · 分析日期：2026-09-14 · 版本：local HEAD `2fd835b9c1`

## 一句话定位

[[sglang]] 是面向 LLM/多模态模型的高性能 serving runtime，核心差异是 RadixAttention：用 radix tree 组织可共享前缀的 KV cache；再把结构化生成、连续批、chunked prefill、投机解码、attention/kernel backend 和多 GPU 并行组合为执行管线。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│ Client / OpenAI · Anthropic · Ollama · Native Engine                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP / gRPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / TokenizerManager                                         │
│  request lifecycle · tokenizer · structured program · streaming       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ ZMQ / shared memory
┌──────────────────────────────▼───────────────────────────────────────┐
│ Scheduler subprocess                                                  │
│  waiting/running batch · EXTEND/DECODE/MIXED · RadixCache · allocator  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ model input / metadata
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU ModelRunner                                                       │
│  attention backend · fused/quantized kernels · sampler                │
│       │                         │                                     │
│       ├─ TP/PP collectives         └─ EP token dispatch for MoE         │
│       └─ DP attention / batch partition                                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / states
┌──────────────────────────────▼───────────────────────────────────────┐
│ DetokenizerManager ──► stream response                                │
└──────────────────────────────────────────────────────────────────────┘
             │
             ├─ RadixCache / HiCache: GPU → host → storage tiers
             └─ PD/EPD disaggregation: transfer KV or encoder outputs
```

## 模块分层

| 层 / 模块 | 主要目录 / 文档 | 职责 |
|---|---|---|
| 接入与编程模型 | `python/sglang/`, README, serving docs | API、SGLang DSL、tokenize、流式输出 |
| 调度与批处理 | `python/sglang/srt`, continuous batching docs | request 状态、EXTEND/DECODE/MIXED、chunked prefill、overlap |
| 缓存层 | radix/session cache、`advanced_features/hicache*` | prefix sharing、eviction、GPU/CPU/storage 分层、量化 KV |
| 执行与 kernel | model runner、attention backend、`sgl-kernel` | attention、FFN/MoE、sampling、CUDA Graph、spec decode |
| 分布式拓扑 | TP/PP/DP/EP、PD/EPD docs、Model Gateway | collectives、expert routing、请求路由、P/D 分离 |

## 关键数据流

```
请求 / SGLang program
  │
  ├─ tokenizer + program state，形成可复用 token prefix
  ├─ RadixCache longest-prefix match：命中则复用 KV，否则分配 token/KV pool
  ├─ Scheduler 组成连续 batch：EXTEND / DECODE / MIXED
  │       └─ 长 prompt 以 chunked prefill 切片并与 decode 交错
  ├─ ModelRunner 选择 attention backend，执行 fused attention/FFN/MoE
  │       └─ TP/PP/DP/EP collective 或 all-to-all
  └─ sampler → DetokenizerManager → streaming response；完成后更新 radix tree
```

RadixAttention 以 token prefix 为树路径，适合 system prompt、few-shot、agent loop 和多轮会话。HiCache 增加 host/storage 层；PD disaggregation 通过 KV transfer 连接独立的 prefill/decode 实例。

## 设计决策与哲学

- **Radix tree 优先优化前缀复用**：牺牲比固定 block 更复杂的树维护与 eviction，换取任意 token 边界共享。
- **显式 batch mode**：EXTEND、DECODE、MIXED 与 chunked prefill 让算力型 prefill 和带宽型 decode 共存，并支持 overlap。
- **进程与 backend 解耦**：TokenizerManager、Scheduler、ModelRunner、DetokenizerManager 异步协作；attention、量化、speculation、KV transfer 可配置替换。
- **并行轴按模型结构组合**：TP/PP 解决规模，DP 解决副本吞吐，EP 解决 MoE 专家分布；DP attention 可复制 attention、保留 FFN/MoE 的 TP/EP。

## 推理优化专题

### KV Cache

RadixCache 做 GPU 内 token-level prefix sharing；session cache 保持会话树状态；eviction 释放冷叶节点。HiCache 扩展 GPU/host/storage 层，量化 KV 降低容量；P/D 分离用 NIXL/Mooncake 等 backend 搬运 KV。

### 连续批处理

Scheduler 每轮重新决定可执行 token 数量，新请求可插入 running batch；长 prompt 通过 chunked prefill 切片，EXTEND 与 DECODE/MIXED 调整公平性。overlap scheduler、two-batch/single-batch overlap 重叠 CPU 调度、通信和 GPU 计算。

### 算子融合与并行

FlashInfer、FlashAttention、Triton、AITER 等 attention backend，配合 sgl-kernel、JIT/torch.compile、CUDA Graph、fused MoE/量化 kernel，减少 launch 与中间读写。TP 切权重，PP 切层，EP 分布专家，DP 分区请求/批/KV；收益取决于 GPU 拓扑、shape、精度和负载。

## 与 vLLM 对比

vLLM 的 PagedAttention 以固定 block 获得简单、稳健的 allocator；SGLang 的 RadixAttention 以树获得更细粒度 prefix sharing。两者已在 kernel、量化、spec decode、P/D、TP/PP/EP/DP 上高度重叠，应以 prefix reuse、TTFT/ITL、吞吐和硬件 backend 实测选择。

## 来源

## 代码级关键流程

### 1. Scheduler 事件循环与 batch 生命周期

关键入口：`python/sglang/srt/managers/scheduler.py:1853`、`:3512`、`:4212`、`:4561`、`python/sglang/srt/managers/schedule_batch.py:2248`。

```text
run_event_loop()
  ├─ 接收 request / abort / control message
  ├─ get_next_batch_to_run()
  │    ├─ 选择 running batch 继续 decode
  │    ├─ 从 waiting queue 取新请求
  │    ├─ match prefix / check memory
  │    └─ 形成 EXTEND / DECODE / MIXED ForwardMode
  ├─ run_batch(ScheduleBatch)
  │    └─ TP worker / ModelRunner forward
  ├─ process_batch_result()
  │    ├─ 更新 Req output / seq_lens
  │    ├─ 处理 stop / abort / grammar
  │    ├─ verify speculative result
  │    └─ cache_finished_req()
  └─ 继续下一轮 event loop
```

SGLang 的 scheduler 是单独进程，并通过多种 mixin 叠加 P/D、PP、DP attention、speculative、DLLM、LoRA、profiler 等横切能力。`ScheduleBatch` 同时携带 request 列表、`forward_mode`、`req_to_token_pool`、`token_to_kv_pool_allocator`、`tree_cache`、`sampling_info` 与 `spec_info`，是 scheduler 到 ModelRunner 的主要状态载体。

### 2. 连续批与内存检查

`get_next_batch_to_run()` 将新请求 admission 与已有 decode batch 合并；`ScheduleBatch.prepare_for_extend()` / `prepare_for_decode()` 将 batch 转换为不同 forward metadata。内存不足时 `check_decode_mem()` 与 `retract_decode()` 回收/撤回部分 decode 请求，保证当前 batch 能继续推进。

```text
waiting reqs + running batch
          ↓ get_new_batch_prefill()
match prefix + alloc_for_extend()
          ↓
ScheduleBatch(EXTEND)
          ↓ prepare_for_extend()
          ├─ mixed chunked prefill + decode
          └─ no memory → retract_decode() / defer request
          ↓
ModelRunner forward
          ↓
process_batch_result()
          ↓ merge next batch / finish requests
```

### 3. Unified Radix Cache 与 token pool

当前主路径可从 `python/sglang/srt/mem_cache/unified_radix_cache.py:548`、`:576`、`:596` 和 `python/sglang/srt/mem_cache/allocation.py:344`、`:587`、`:731` 追踪。

```text
Req input_ids + extra_key
          ↓
UnifiedRadixCache.match_prefix()
          ├─ longest prefix → device/host KV indices
          └─ partial match → tree split / suffix boundary
          ↓
alloc_for_extend/decode/spec_decode()
          ↓
ReqToTokenPool → TokenToKVPool / paged allocator
          ↓
ModelRunner writes KV
          ↓
cache_finished_req() → insert() → evict()/host tier
```

与旧的单一 `radix_cache.py` 相比，unified cache 将 full attention、MLA、Mamba、SWA、HiCache/storage、external linker 与 KV events 放进统一接口；`MatchPrefixParams` 的 `extra_key` 可隔离不同 LoRA、cache version 或不应共享的上下文。

### 4. Attention Backend 的两阶段选择

SGLang 在 `model_executor/model_runner_components/attention_backend_setup.py:166` 通过 `ATTENTION_BACKENDS` registry 创建 backend；随后 hybrid attention 在 `layers/attention/hybrid_attn_backend.py:63` 按 `ForwardMode` 选择 prefill/decode/verify 实现。也就是说 backend 选择不是一次性的：启动时决定能力与实例，forward 时还可能按 EXTEND、DECODE、MIXED、TARGET_VERIFY 选择具体子路径。

```text
server args / model / hardware
          ↓ get_attention_backend()
ATTENTION_BACKENDS registry
          ↓ backend instance
ForwardMode
  ├─ EXTEND → prefill backend
  ├─ DECODE → decode backend
  ├─ MIXED  → hybrid dispatch
  └─ TARGET_VERIFY → verify mask/backend
          ↓
FlashInfer / FlashAttention / Triton / AITER / MLA / hybrid kernels
```

### 5. Speculative Decode

SGLang 用 `SpeculativeAlgorithm`、`SpecInput`/`spec_info` 和 `BaseSpecWorker` 组织多个 draft/verify 实现。scheduler 把 speculative 状态放进 `ScheduleBatch.spec_info`，ModelRunner 根据 `ForwardMode.TARGET_VERIFY` 构造 verify metadata；`process_batch_result()` 再把 accepted token、rejected tail、seq lens 和 KV 状态写回 request。

```text
Decode batch
    ↓ BaseSpecWorker / draft worker
draft tokens + draft KV metadata
    ↓ target verify forward
TARGET_VERIFY + verify mask
    ↓ accepted length / rejected tail
update ScheduleBatch.spec_info + Req.seq_lens
    ↓
next draft or normal decode
```

当前代码中可见 EAGLE、multi-layer EAGLE、DFlash、NGRAM、DSpark、UNO、FrozenKV-MTP 等实现；它们共享抽象，但具体 draft input、verify layout、CUDA Graph 和 KV 写入策略不同。

### 6. P/D Disaggregation 的状态机

SGLang 的 decode 侧 `DecodeRequest` 与 transfer queue 负责等待 prefill 端 KV；`disaggregation/base/conn.py` 定义注册、传输、poll、失败和 abort 等通用连接契约。HiCache decode mixin 还可在 L1/L2/L3 层查找并恢复 prefix。

```text
decode request created
        ↓ register / bootstrap prefill
WAITING_FOR_KV_TRANSFER
  ├─ poll complete → waiting queue
  ├─ pending       → keep transfer queue
  ├─ failed        → abort / retry / rebootstrap
  └─ timeout       → cleanup receiver resources
        ↓
skip prefill forward, populate local metadata
        ↓
DECODE running batch
```

### 7. TP / PP / EP / DP 的通信边界

SGLang 在 `python/sglang/srt/distributed/bootstrap.py:271-290` 根据 `tp_size`、`pp_size`、`attn_dp_size`、`moe_ep_size`、`moe_dp_size` 计算 rank/world size 并初始化 process groups。collective 原语集中在 `python/sglang/srt/distributed/parallel_state.py:649`（all-reduce）、`:1155`（all-to-all）、`:1280`（all-gather）以及 send/recv helpers。

```text
bootstrap rank geometry
          ↓
ParallelState(TP / PP / DP-attn / EP / MoE-DP)
          ↓
ForwardBatch / ScheduleBatch metadata
  ├─ TP Linear / Attention head shard → all-reduce/gather
  ├─ PP stage → activation send/recv
  ├─ EP MoE gate → token all-to-all → local experts → reduce
  └─ DP attention → request/batch partition + rank-consistent padding
          ↓
tp_worker.forward_batch_generation()
          ↓
merge output / next Scheduler step
```

SGLang 的 DP attention 会改变 attention 与 FFN/MoE 的分工：attention 可在 DP rank 复制，FFN/MoE 继续沿 TP/EP 分片；因此 `ScheduleBatch` 中同时存在 per-rank batch、global token counts、KV pool 和 DP cooperation metadata。

### 8. Accepted / rejected KV 修正

投机解码的关键不是只生成 draft，而是 verify 之后维护“已提交长度”和“设备上乐观写入长度”的差异。当前实现可从 `scheduler_components/batch_result_processor.py:776-804`、`speculative/dflash_info_v2.py:160-218` 以及 `speculative/spec_info.py` 追踪。

```text
draft worker propose
        ↓ optimistic draft KV / spec_info
target verify (TARGET_VERIFY)
        ↓ accepted draft count + bonus token
┌───────────────┴────────────────┐
│ accepted                        │ rejected tail
│ kv_committed_len += accepted    │ drop/discard tail
│ commit output + grammar state   │ restore live seq_lens
└───────────────┬────────────────┘
                ↓
batch_result_processor
                ↓
Req.seq_lens / kv_committed_len / spec_info
                ↓
next draft or normal decode
```

`kv_committed_len` 是理解 SGLang overlap/spec 的关键：verify 可能暂时扩展 batch 的 target-attention 长度，但只有 accepted contiguous run 才能提交给下一轮；失败/取消路径必须释放 receiver、draft KV 和未提交 tail。

## SGLang 代码设计要点

- `ScheduleBatch` 是状态密集型对象，优势是新特性可复用同一 batch；代价是字段和 mixin 组合复杂。
- `UnifiedRadixCache` 把 token prefix、host tier、不同 attention state 和 external linker 纳入统一 cache contract。
- `ForwardMode` 是 backend dispatch 的关键协议，避免每个 backend 自己判断请求阶段。
- speculative、P/D、HiCache 和 overlap 都会改变 batch metadata 生命周期，必须在 scheduler、runner、result processor 三处保持一致。

## 与 vLLM 的代码级对照

| 维度 | SGLang | vLLM |
|---|---|---|
| 主循环 | `run_event_loop → get_next_batch_to_run → run_batch → process_batch_result` | `EngineCore.step → schedule → execute_model → update_from_output` |
| 状态载体 | `ScheduleBatch` + `Req` + mixins | `SchedulerOutput` + `Request` + KV block records |
| batch mode | `EXTEND / DECODE / MIXED / TARGET_VERIFY` | 以 computed-token 差值统一描述阶段 |
| KV cache | `UnifiedRadixCache` + token/page pools | `KVCacheManager` + block coordinator/table |
| prefix hit | radix longest-prefix，支持 split | block/hash prefix，受 cache block 边界约束 |
| backend | registry 创建 + ForwardMode 二次选择 | selector 选择 backend class/enum |
| spec | `BaseSpecWorker` + `SpecInput` + target verify | proposer + lookahead slots + scheduled spec tokens |
| P/D | mixin + DecodeRequest/transfer queue/receiver | KVConnector metadata + scheduler/worker hooks |


- https://github.com/sgl-project/sglang/blob/main/README.md
- https://github.com/sgl-project/sglang/blob/main/docs/index.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hicache_design.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hicache.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/pipeline_parallelism.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/expert_parallelism.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/pd_disaggregation.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/attention_backend.mdx
