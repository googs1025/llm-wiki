---
title: vLLM 请求到 GPU Kernel 的执行路径
tags: [analysis, vllm, llm-inference, scheduler, kv-cache, cuda, gpu]
date: 2026-10-12
sources: [vllm-architecture-analysis.md]
related: ["[[vllm]]", "[[llm-inference-request-lifecycle]]", "[[llm-gpu-kernel-execution-path]]", "[[paged-attention]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]", "[[vllm-operational-lifecycle]]"]
---

# vLLM 请求到 GPU Kernel 的执行路径

本页沿 vLLM V1 的当前源码走完一次生成请求：API/`AsyncLLM` 把请求交给 EngineCore，`Scheduler` 在 token budget 和 KV capacity 下组成 iteration，worker 的 `GPUModelRunner` 准备 block table、slot mapping 和 tensor inputs，模型 forward 进入 attention/GEMM/MoE/custom ops，最后 sampling 结果回到 scheduler 与流式输出。

平台入口如何把请求送进 vLLM，分别见 [[aibrix-inference-request-flow]]、[[dynamo-inference-request-flow]] 和 [[llm-d-inference-request-flow]]；kernel 进入 SM、Tensor Core 和 HBM 后的细节见 [[llm-gpu-kernel-execution-path]]。

## 运维状态与执行状态的边界

本页假设 engine 已 ready 且 scheduler允许执行。Weights/KV/CUDA Graph/NCCL 在 Sleep、Wake、Reload 和 Shutdown 中如何分配/释放，见 [[vllm-operational-lifecycle]]；外部系统必须先drain并退出routing，不能在本页的GPU iteration仍访问资源时执行memory lifecycle动作。

## 当前源码快照

核验日期：2026-10-11。

- 官方仓库：[vllm-project/vllm@`276fbcff2717bd934cfa37c8a2e4c391f3e7237b`](https://github.com/vllm-project/vllm/tree/276fbcff2717bd934cfa37c8a2e4c391f3e7237b)。
- 本地 `/Users/zhenyu.jiang/vllm` 为 `dc36fcce902a`，落后于本页固定 upstream；它只用于快速定位，所有 symbol 已在固定 commit 重新核验。
- 本页聚焦 V1 decoder-only generation 主路径。Pooling、multimodal encoder、speculative decoding、hybrid Mamba cache 和新 GPU runner 分支会增加路径，正文在影响主契约的位置标出。

### 源码入口

| 阶段 | 固定 commit 文件 / symbol | 输入 → 输出 |
|---|---|---|
| 异步生成入口 | [`vllm/v1/engine/async_llm.py: AsyncLLM.generate`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/engine/async_llm.py#L691) | prompt/request params → async output generator |
| 加入 engine | [`AsyncLLM.add_request`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/engine/async_llm.py#L381) | processed request → EngineCore request |
| 单轮核心 | [`vllm/v1/engine/core.py: EngineCore.step`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/engine/core.py#L647) | scheduler state → EngineCoreOutputs |
| 调度 | [`vllm/v1/core/sched/scheduler.py: Scheduler.schedule`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/core/sched/scheduler.py#L580) | waiting/running + budgets → SchedulerOutput |
| KV prefix | [`KVCacheManager.get_computed_blocks`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/core/kv_cache_manager.py#L264) | request hashes → cached blocks/tokens |
| KV slots | [`KVCacheManager.allocate_slots`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/core/kv_cache_manager.py#L371) | cached/external/new/lookahead tokens → blocks |
| GPU iteration | [`vllm/v1/worker/gpu/model_runner.py: GPUModelRunner.execute_model`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/worker/gpu/model_runner.py#L1713) | SchedulerOutput → forward state/intermediate tensors |
| Sampling | [`GPUModelRunner.sample_tokens`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/worker/gpu/model_runner.py#L2080) | hidden states + sampling state → ModelRunnerOutput |
| 状态回写 | [`Scheduler.update_from_output`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/core/sched/scheduler.py#L2025) | scheduler/model outputs → per-client EngineCoreOutputs |
| Attention 选择 | [`vllm/v1/attention/selector.py`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/attention/selector.py) / [`backends/registry.py`](https://github.com/vllm-project/vllm/blob/276fbcff2717bd934cfa37c8a2e4c391f3e7237b/vllm/v1/attention/backends/registry.py) | platform/model/cache config → backend class |

## 进程与队列边界

vLLM V1 把 API/`AsyncLLM`、EngineCore 与 GPU workers 作为不同责任边界。实际部署可选择 in-process、multiprocess 或分布式 executor，因此下图表达逻辑进程/transport 边界，不把某一种 IPC 写成唯一实现。

```text
[API / frontend process]
OpenAI route / request processor
        │ normalized prompt + SamplingParams
        ▼
AsyncLLM.generate
        │ AsyncLLM.add_request
        ▼
EngineCoreClient ── request/control transport ──► [EngineCore process]
                                                      │
                                             Scheduler queues/state
                                                      │ SchedulerOutput
                                                      ▼
                                             ModelExecutor abstraction
                                                      │ RPC/IPC/direct call
                          ┌───────────────────────────┼──────────────────────┐
                          ▼                           ▼                      ▼
                    [GPU worker rank 0]         [GPU worker rank 1]    [...]
                    GPUModelRunner              GPUModelRunner
                          │ model output / intermediate tensors
                          └──────────────► EngineCore / output transport
                                             │
                                             ▼
                              AsyncLLM output processor / request stream
```

三类队列/状态不要混淆：

- Frontend output stream 管理客户端消费、取消与 backpressure。
- EngineCore `Scheduler` 管理 waiting/running、computed tokens、KV ownership 与优先级。
- GPU runner 保持 device-side input buffers、request slots、block tables、sampling state 和 CUDA Graph state。

## 请求进入 EngineCore

`AsyncLLM.generate` 创建/使用异步输出流，通过 `add_request` 把请求提交到 `EngineCoreClient`。EngineCore 把 `Request` 加入 scheduler；后台循环持续调用 `EngineCore.step`。在固定 commit 中，`step` 的主干非常清晰：schedule → execute → sample（必要时）→ update。

```text
AsyncLLM.generate(request)
  │
  ├── request processing / tokenization / validation
  ├── AsyncLLM.add_request
  │      └── EngineCoreClient.add_request_async
  ▼
EngineCore.add_request
  └── Scheduler.add_request → waiting/request map

EngineCore.step
  ├── Scheduler.schedule(_should_throttle_prefills)
  │      └── SchedulerOutput
  ├── ModelExecutor.execute_model(output, non_block=True)
  ├── future.result()
  ├── if forward did not sample: ModelExecutor.sample_tokens(...)
  ├── process abort queue
  └── Scheduler.update_from_output
         └── EngineCoreOutputs ──► AsyncLLM output processor ──► client
```

`non_block=True` 允许 executor 将 GPU work 与 EngineCore 的 host-side 行为解耦，但 `future.result()`/后续 sampling 仍建立本轮输出依赖。启用 batch queue/async scheduling 时，EngineCore 可以让多个 batch 处于 pipeline 中；这不会取消 scheduler 对 request/KV state 的一致性责任。

## Scheduler 与 Continuous Batch

固定 commit 的 `Scheduler.schedule` 注释明确说明：内部不依赖一个硬编码的“prefill phase / decode phase”状态机。统一量是 `request.num_computed_tokens` 与 `num_tokens_with_spec` 的差；scheduler 每步分配 token，使 computed state 追上要计算的 tokens。这一模型自然覆盖 prefix hit、chunked prefill、decode 与 speculative tokens。

```text
Scheduler state at iteration N
┌───────────────────────────────────────────────────────────────┐
│ running: R1(computed=1024,target=1025)  → 1 decode token      │
│          R2(computed=512,target=768)    → 256 prefill tokens  │
│ waiting: R3(prefix hit=640,prompt=800)  → admit 160 tokens    │
│ preempted/resumed requests · encoder/spec/connector state     │
└───────────────────────────────────────────────────────────────┘
                 │ budgets / KV capacity / priority / constraints
                 ▼
token_budget = max_num_scheduled_tokens
input_budget = max_num_batched_tokens
                 │
       running requests first; then eligible waiting requests
                 │ allocate/cache blocks per accepted work
                 ▼
SchedulerOutput
  num_scheduled_tokens{R1:1,R2:chunk,R3:chunk}
  new/resumed/cached request data
  block ownership + connector/encoder/spec metadata
```

关键限制依次影响“本轮能算多少”：

1. 全局 token/input budget；
2. request 剩余 tokens、model length 与 speculative placeholders；
3. long prefill threshold、chunk alignment、encoder budget；
4. KV blocks 是否够用，必要时 preempt/free/recompute；
5. KV connector 的 external tokens、同步/异步 load readiness；
6. PP/async cadence、DP prefill throttling 等并行约束。

Continuous batching 的核心是 iteration 之间可以加入新请求、继续 running 请求、恢复 preempted 请求或移除 finished 请求。它不是把每个 HTTP 请求独占 GPU 到结束。

## KVCacheManager 与 Block Table

`KVCacheManager` 在 scheduler 侧管理逻辑 KV blocks 和 prefix cache ownership；worker 侧 block table/slot mapping 把逻辑安排变成 attention backend 能消费的 device metadata。

```text
Request token IDs
  │ block hashing
  ▼
KVCacheManager.get_computed_blocks
  ├── prefix lookup disabled? → zero hit
  ├── coordinator.find_longest_cache_hit
  └── full blocks + num computed tokens + shared-prefix boundary
                    │
                    ▼
KVCacheManager.allocate_slots
  inputs:
    local cached blocks
    external connector tokens
    new scheduled tokens
    speculative lookahead
  │ capacity/refcount/free-block decision
  ▼
KVCacheBlocks / request ownership
  │ SchedulerOutput
  ▼
GPUModelRunner block_tables.apply_staged_writes
  ├── prepare_attn → block tables
  └── prepare_attn → slot mappings
          │
          ▼
attention backend: logical token/head ──► physical KV address
```

### `allocate_slots` 的五段布局

固定 commit 的 docstring 把序列空间拆成：已计算 (`comp`)、新 prefix hit (`new_comp`)、connector 提供 (`ext_comp`)、本轮新算 (`new`) 与 speculative lookahead。只有最后两类或未完整 external hit 的部分需要本轮计算，但都可能需要逻辑 block ownership。

```text
tokens in request order
┌──────────┬────────────┬──────────────┬────────────┬─────────────┐
│ comp     │ new_comp   │ ext_comp     │ new        │ lookahead   │
│ existing │ local hit  │ remote/conn. │ compute now│ reserve     │
└──────────┴────────────┴──────────────┴────────────┴─────────────┘
                         │<---- allocate / validate blocks ---->│
                                      │<-- model computes ----->│
```

当 prefix 全命中时，通常仍需重算至少最后一个 token 才能得到 logits；block alignment 可能让重算粒度大于一个 token。External connector load 失败或 block 无效时，`Scheduler.update_from_output` 可降低 computed state 并触发重新计算，而不是盲信远端 KV。

## GPUModelRunner

当前主 GPU runner 位于 `vllm/v1/worker/gpu/model_runner.py`。`execute_model` 首先同步 request/device state，再根据 batch shape 与配置选择 CUDA Graph/compiled/eager，准备 input 和 attention metadata，执行 model forward；`sample_tokens` 在 last PP rank 上把 hidden states 变成 logits/sampled IDs。

```text
GPUModelRunner.execute_model(SchedulerOutput)
  ├── finish/free/add/update request state
  ├── block_tables.apply_staged_writes
  ├── gather_batch_req_state / DP sync
  ├── dispatch_cg_and_sync_dp
  │      └── batch descriptor: graph variant / eager / padding
  ├── prepare_inputs
  ├── prepare_attn
  │      └── block tables + slot mappings + attention metadata
  ├── kv_connector.pre_forward
  ├── model(**model_inputs) OR compiled/ubatch/fullgraph path
  ├── kv_connector.finish_forward
  └── save ExecuteModelState
          │
          ▼
GPUModelRunner.sample_tokens(grammar_output)
  ├── receive PP hidden states if last rank
  ├── compute logits / apply processors
  ├── sampler.sample
  └── ModelRunnerOutput(sampled IDs, logprobs, connector output, stats)
```

### 从 tensor op 到 kernel

`self.model(**model_inputs)` 进入具体 model implementation；每层调用 linear/quantization、norm、rotary、attention、MoE 等 layer。Backend 可能落到 ATen、Triton、FlashAttention/FlashInfer、CUTLASS 或 vLLM custom CUDA ops。

```text
GPUModelRunner
  └── model.forward
       └── decoder layer × N
            ├── RMSNorm / rotary custom op
            ├── QKV GEMM
            ├── Attention layer
            │    └── selected v1 attention backend
            │         ├── prefill kernel
            │         ├── paged decode kernel
            │         └── KV reshape/cache write
            ├── output GEMM + TP collective
            └── MLP or fused MoE + collectives
                  │
                  ▼
      PyTorch dispatcher / compile / Triton / CUDA extension
                  │
                  ▼
      [[llm-gpu-kernel-execution-path|CUDA streams、kernels 与 GPU]]
```

## Prefill、Chunked Prefill 与 Decode

vLLM 的统一 scheduler 不代表 GPU kernel 完全相同。`num_scheduled_tokens`、query length、prefix hit 与 attention metadata 会使 backend 选择或内部路径不同。

```text
                         one Scheduler iteration
                  ┌────────────┼──────────────┐
                  ▼            ▼              ▼
             new prefill   prefill chunk    decode request
             q_len ≫ 1     q_len > 1        q_len ≈ 1
                  │            │              │
                  └────────────┼──────────────┘
                               ▼
                    packed/ragged model inputs
                               │
            ┌──────────────────┴───────────────────┐
            ▼                                      ▼
  prefill attention path                 paged decode path
  larger Q tiles / causal mask           block-table KV gather
  writes K,V for many tokens             writes one/few new slots
            └──────────────────┬───────────────────┘
                               ▼
                  logits only for required positions
                               │
                               ▼
                          sampling/output
```

- Prefill 通常包含较大的 GEMM 和 attention tiles，偏 compute throughput。
- Chunked prefill 限制单轮 prompt tokens，使它能与 decode work 共存，但增加 iteration/state 边界。
- Decode 的小 query 读取不断增长的历史 KV，常更偏 memory/latency；continuous batch 用更多 sequences 增大有效 batch。
- 同一 iteration 混合 prefill/decode 时，backend 必须根据 per-request lengths、slot mapping 和 mask 正确分段。

## CUDA Graph 与 Attention Backend

`dispatch_cg_and_sync_dp` 根据 batch/request/token shape、LoRA、profile/eager requirement 等选择 batch descriptor。Full graph 可直接经 `cudagraph_manager.run_fullgraph`；piecewise/compiled 和 eager 路径仍在 forward context 中调用 model。

```text
SchedulerOutput + request state
          │
          ▼
dispatch_cg_and_sync_dp
  ├── FULL graph match ──► copy/update buffers ──► graph replay
  ├── PIECEWISE/compile ─► compiled model pieces + graph segments
  └── EAGER / fallback ──► raw self.model(**inputs)
          │
          ▼
Attention selector / registry
  inputs: platform · head size · dtype · cache dtype · model features · env
          │
          ├── FlashAttention family
          ├── FlashInfer family
          ├── Triton attention / paged ops
          ├── MLA / linear / Mamba-specific backends
          └── platform-specific backend
```

CUDA Graph 解决 launch submission；attention backend 解决计算/layout。Graph 命中不代表 attention 选择改变，也不保证 kernel compute 更少。反之，prefix cache 减少要 prefill 的 tokens，会改变 batch shape，可能间接影响 graph variant。

## TP、PP、EP、DP

这些并行维度作用于不同对象，不能都简写成“多卡”。

```text
Data Parallel (DP)
  independent request/batch ownership per DP rank
  optional DP coordination balances/aligns work

Pipeline Parallel (PP)
  rank/stage 0: layers 0..k ─═ IntermediateTensors ═► stage 1: layers k+1..N
  only last PP rank produces final hidden/logits/sample

Tensor Parallel (TP)
  one layer's tensor shards across ranks
  local GEMM ─═ all-reduce/all-gather/reduce-scatter ═► next op

Expert Parallel (EP)
  router top-k ─═ token dispatch/all-to-all ═► expert ranks
               ◄═ combine/all-to-all ═──────── expert outputs
```

- TP collective 位于单层内部，直接影响每轮 latency。
- PP 让 `GPUModelRunner.execute_model` 在非最后 rank 返回 `IntermediateTensors`，最后 rank 才 sampling。
- EP 的 token permutation、all-to-all 与 grouped GEMM 对 MoE 性能同等重要。
- DP 通常让每个 rank/replica 处理不同 requests；它与跨实例 router 的 endpoint picking 仍是不同层。

## P/D Connector 边界

vLLM 提供 KV connector 接口与多种实现，但“谁选择 Prefill/Decode endpoint、怎样把两个 HTTP 请求关联起来”通常属于上层平台或示例 proxy；engine 内负责 scheduler-side KV accounting 与 worker-side data movement hook。

固定 commit 的 connector 目录包括 NIXL、Mooncake、LMCache、MoriIO、FlexKV、offloading 等实现。不同 connector 的 push/pull、同步/异步、layout 和 side-channel 契约不同。

```text
[Platform / P-D coordinator]
select prefill endpoint ──► request + transfer/session metadata
                              │
                              ▼
[Prefill vLLM Scheduler]
allocate slots / mark transfer intent
                              │ SchedulerOutput connector metadata
                              ▼
[Prefill GPUModelRunner]
kv_connector.pre_forward → model writes KV → finish_forward
                              │ export/register/notify
                              ├── control metadata ──► coordinator/decode scheduler
                              └══ KV payload via connector transport ══►

[Decode vLLM Scheduler]
external computed tokens + block reservation + load readiness
                              │
                              ▼
[Decode GPUModelRunner]
kv_connector.pre_forward/load → wait readiness → decode attention reads KV
```

所有权边界：

- `KVCacheManager.get_computed_blocks_for_connector`/scheduler 侧逻辑决定 local hit、external tokens、block reservation 与失败后的 recompute。
- `GPUModelRunner` 在 forward 前后调用 worker-side connector hook，连接 device KV buffers 与 transport。
- Connector output 把 failed receive、invalid blocks 或 completion 等信息带回 scheduler。
- 上层平台负责 endpoint pairing、request lifecycle 与 client stream；connector 不自动提供跨平台通用路由。

延迟释放很重要：异步 transfer 尚未结束时，scheduler 不能让同一 blocks 被新请求复用。固定 commit 的 `Scheduler.update_from_output` 也包含 deferred-free drain 和 connector failure handling，这说明正确性不仅是“数据拷贝成功”。

## Token 返回与取消

ModelRunner 的 sampled token IDs 不是直接的 SSE。它们先回到 scheduler 更新 request state，再成为 `EngineCoreOutputs`，最后由 frontend output processor 生成用户可见对象和文本增量。

```text
[GPU]
hidden states ──► logits ──► processors/grammar ──► sampler
                                                   │ token IDs/logprobs
                                                   ▼
[EngineCore]
Scheduler.update_from_output
  ├── update computed/output/spec state
  ├── detect stop/max length/abort/stale output
  ├── free/defer KV blocks when safe
  └── EngineCoreOutputs
              │
              ▼
[Frontend]
output processor ──► detokenize / RequestOutput ──► async generator
              │                                           │
              └──────────────── SSE/final JSON ───────────► Client
```

取消有竞态：request 可能在 GPU 执行期间被 abort。固定 commit 的 `EngineCore.step` 在处理 model output 前先处理 abort queue；`Scheduler.update_from_output` 也检查 request 已完成/消失、in-flight token 和 stale output。已经向客户端输出 token 后，简单地把 request 重发到另一个 worker 可能改变采样流，不能视为透明 retry。

### 一次 aggregated 请求的全链

```text
Client
  ──► API / AsyncLLM.generate
  ──► EngineCoreClient
  ──► Scheduler.add_request(waiting)
  ──► Scheduler.schedule
       ├── prefix hit / KV allocate
       └── SchedulerOutput
  ──► GPUModelRunner.execute_model
       ├── block table / slot mapping / inputs
       ├── model forward → attention/GEMM/MoE CUDA kernels
       └── sample_tokens
  ──► Scheduler.update_from_output
  ──► output processor / detokenizer
  ──► SSE token
       │ unfinished
       └── next schedule iteration ──► ...
```

这条链是三个平台页向 vLLM 下钻时的共同 handoff。平台可能在 API 之前增加 gateway/router，在 scheduler/runner 周围配置 connector，也可能直接把请求代理给 vLLM endpoint；但进入 V1 engine 后，token budget、KV blocks、model execution 与 output update 仍由以上对象负责。
