---
title: SGLang 请求到 GPU Kernel 的执行路径
tags: [analysis, sglang, llm-inference, scheduler, radix-cache, cuda, gpu]
date: 2026-10-11
sources: [sglang-architecture-analysis.md]
related: ["[[sglang]]", "[[llm-inference-request-lifecycle]]", "[[llm-gpu-kernel-execution-path]]", "[[radix-attention]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]"]
---

# SGLang 请求到 GPU Kernel 的执行路径

本页沿 SGLang Runtime 当前主路径追踪一次生成请求：`TokenizerManager` 规范化并 tokenize，经 IPC 送入 `Scheduler`；scheduler 把请求组织成 `ScheduleBatch`，用 `RadixCache` 匹配 prefix、用 request/token pools 分配 KV locations；`ModelRunner` 根据 `ForwardMode` 选择 eager 或 CUDA Graph 路径，调用具体 attention/model kernels 并 sampling；结果再经 scheduler 与 `DetokenizerManager` 返回流式文本。

它与 vLLM 的问题域相似，但对象和状态机不同。详细对照见 [[vllm-gpu-execution-path]]；platform 如何接入 SGLang 见 [[aibrix-inference-request-flow]]、[[dynamo-inference-request-flow]] 与 [[llm-d-inference-request-flow]]。

## 当前源码快照

核验日期：2026-10-11。

- 官方仓库：[sgl-project/sglang@`e328c7ecbd69ebf77f38db9aa64eecefd760fe4b`](https://github.com/sgl-project/sglang/tree/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b)。
- 本地 `/Users/zhenyu.jiang/sglang` 为 `ba8612ced518`，比固定 upstream 早；本地仅用于定位，所有核心 symbol 已在固定 commit 重新核验。
- 主线按普通 text generation 描述。Multimodal、speculative、DLLM、HiCache/HiSparse、hybrid linear attention 等会扩展 batch/cache/backend 行为，不应由基础图推断其全部细节。

### 源码入口

| 阶段 | 固定 commit 文件 / symbol | 输入 → 输出 |
|---|---|---|
| 请求入口 | [`TokenizerManager.generate_request`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/tokenizer_manager.py#L863) | API object → async response stream |
| IPC dispatch | [`TokenizerManager._send_one_request`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/tokenizer_manager.py#L1728) | tokenized request → scheduler IPC |
| 普通循环 | [`Scheduler.event_loop_normal`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/scheduler.py#L1929) | inbound queues/state → repeated batches |
| 选 batch | [`Scheduler.get_next_batch_to_run`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/scheduler.py#L3682) | waiting/running/last batch → NextBatchPlan |
| Extend 准备 | [`ScheduleBatch.prepare_for_extend`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/schedule_batch.py#L2710) | prefix/extend requests → tensors + KV locations |
| Decode 准备 | [`ScheduleBatch.prepare_for_decode`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/schedule_batch.py#L3538) | running batch → next-token slots/state |
| Prefix lookup | [`RadixCache.match_prefix`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/mem_cache/radix_cache.py#L358) | RadixKey → MatchResult |
| KV extend allocation | [`PagedTokenToKVPoolAllocator.alloc_extend`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/mem_cache/allocator/paged.py#L204) | prefix/sequence lengths → KV indices |
| KV decode allocation | [`PagedTokenToKVPoolAllocator.alloc_decode`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/mem_cache/allocator/paged.py#L279) | next sequence lengths → new KV indices |
| Model forward | [`ModelRunner.forward`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/model_executor/model_runner.py#L1755) | ForwardBatch → ModelRunnerOutput |
| Sampling | [`ModelRunner.sample`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/model_executor/model_runner.py#L2030) | logits + sampling state → next token IDs |
| Detokenize | [`DetokenizerManager.event_loop`](https://github.com/sgl-project/sglang/blob/e328c7ecbd69ebf77f38db9aa64eecefd760fe4b/python/sglang/srt/managers/detokenizer_manager.py#L180) | scheduler token outputs → decoded outputs |

## 进程与 IPC 边界

SGLang Runtime 将 HTTP/tokenization、scheduler/model worker 与 detokenization 分成明确的 manager 边界，并使用 IPC channels 传递 typed request/output objects。部署配置可能增加 data-parallel controller、多个 tokenizer workers 或 pipeline ranks。

```text
[HTTP / API process]
route handler
    │ GenerateReqInput
    ▼
TokenizerManager
    ├── normalize / validate / tokenize
    ├── rid_to_state: client-side request stream state
    └── TokenizedGenerateReqInput
             │ ZMQ/IPC dispatch
             ▼
[Scheduler process / TP rank group]
Scheduler.ingest_requests
    ├── waiting/running/chunked state
    ├── RadixCache + memory pools
    └── ScheduleBatch
             │ model worker call / rank communication
             ▼
[GPU ModelRunner rank(s)] ──► kernels / collectives
             │ token IDs / logprobs / batch result
             ▼
Scheduler.process_batch_result
             ├── output IPC ──► [DetokenizerManager]
             │                         │ decoded text/output IPC
             └─────────────────────────▼
                              TokenizerManager request state
                                        │ async yield
                                        ▼
                                      Client
```

三份状态有不同所有权：`TokenizerManager.rid_to_state` 负责客户端等待/取消/流；Scheduler 的 `Req` 与 batches 负责计算和 KV 生命周期；ModelRunner 负责 device buffers、attention backend 与 graph runner。IPC 传递的是必要字段或输出，不是让同一个 Python object 跨进程共享可变状态。

## TokenizerManager

`TokenizerManager.generate_request` 先规范化 batch/arguments、建立 request state、处理暂停和 model-update reader lock，再 tokenize 并调用 `_send_one_request`。固定 commit 中 `_send_one_request` 还处理 multimodal feature transport、time stats、pickle wrapping 与“已成功 dispatch”标记。

```text
HTTP body / internal GenerateReqInput
  │
  ▼
TokenizerManager.generate_request
  ├── normalize_batch_and_arguments
  ├── default priority / validation
  ├── _init_req_state(rid)
  ├── wait if paused
  ├── validate/resolve LoRA
  ├── _tokenize_one_request
  └── _send_one_request
         ├── prepare multimodal feature transport if needed
         ├── wrap IPC fields
         ├── _dispatch_to_scheduler
         └── mark rid state dispatched
  │
  └── _wait_one_response ──async yield──► API route/client
```

“TokenizerManager”不等于只有 tokenizer。它是 API 侧 request lifecycle manager：维护 rid 到 response state 的映射，区分尚未 dispatch 的本地失败与已经进入 scheduler 的 abort，并把 scheduler/detokenizer 输出关联回客户端 stream。

## Scheduler Event Loop

普通循环的主链是 ingest → plan → run → process result → update last batch。它比“每个请求调用一次 model”更接近实际运行模型：一个循环 iteration 处理一个动态 `ScheduleBatch`，batch 可以包含多个请求。

```text
Scheduler.event_loop_normal
while running:
  ingest_requests()
       │ new / abort / control messages
       ▼
  get_next_batch_to_run(running_batch, last_batch)
       │ NextBatchPlan
       ├── running_batch for future decode
       └── batch_to_run
              │
              ├─ batch exists ──► run_batch
              │                    └── model forward/sample result
              │                         │
              │                         ▼
              │                    process_batch_result
              └─ no batch ──────► on_idle / maintenance
       │
       └── last_batch = batch → next iteration
```

`get_next_batch_to_run` 会处理已完成/中止请求、chunked request、上一轮 extend 到 decode 的合并、waiting prefix matching、prefill admission 与 running decode。它优先尝试可行的新 prefill，同时保证 running batch 的延续；具体 policy、token budget、memory availability 和并行配置影响结果。

### Prefill 与 running batch 合并

```text
last_batch(EXTEND completed)
      │ filter finished / exclude active chunk
      ▼
running_batch(DECODE candidates) ◄── merge surviving extended requests
      │
waiting_queue ── prefix match / PrefillAdder / budget ──► new_batch(EXTEND)
      │                                                     │
      └────────────── scheduling constraints ───────────────┘
                              │
                    choose batch_to_run
                    EXTEND / DECODE / IDLE / other mode
```

这和 vLLM 的统一 computed-token scheduler 不同：SGLang 显式使用 `ForwardMode` 与 `ScheduleBatch` preparation 路径表达 extend/decode 等模式。

## ScheduleBatch 与 ForwardMode

`ScheduleBatch` 是 scheduler 和 ModelRunner 之间的主要 batch object。它持有 requests、sequence lengths、prefix lengths、request-pool indices、KV output locations、sampling info 与并行/backend metadata。

```text
Req objects
  ├── origin_input_ids / output_ids
  ├── prefix_len / extend_len / seq_len
  ├── cache node / request pool slot
  └── sampling / stop / priority state
             │
             ▼
ScheduleBatch
  ├── ForwardMode.EXTEND
  │     prepare_for_extend
  │     flatten uncached input tokens
  │     alloc KV for extend range
  │     build prefix/sequence tensors
  │
  ├── ForwardMode.DECODE
  │     prepare_for_decode
  │     consume prior output token
  │     alloc one/few new KV locations per request
  │     increment sequence lengths
  │
  ├── IDLE / PREBUILT / TARGET_VERIFY / DRAFT_EXTEND ...
  └── ForwardBatch.init_new → ModelRunner-facing tensors/metadata
```

### Extend 不只是首次 Prefill

EXTEND 表示从已有 prefix 后继续计算一段 tokens：首次 prompt、prefix-cache suffix、chunked prefill 或某些 speculative 路径都可能使用 extend 语义。`prepare_for_extend` 依据每个 request 的 `prefix_len` 截取未计算 tokens，并将其 flatten 成本轮 input。

### Decode 不只是 `seq_len += 1`

`prepare_for_decode` 还需分配新 KV location、维护 penalties/sampling state、更新 request/sequence tensors，并处理 overlap、beam/speculative/hybrid state 等条件。普通路径每 request 新增一个 token slot，但不能把所有配置推广成永远固定一个。

## RadixCache

[[radix-attention]] 的核心在 SGLang 中体现为 prefix tree 与 KV pool indices 的联合管理。`RadixCache.match_prefix` 用 token IDs 加可选 `extra_key`/cache namespace 查最长 page-aligned prefix，返回 `MatchResult`，并更新 eviction 使用的访问元数据；匹配落在 node segment 内部时可能 split node 暴露精确边界。

```text
RadixKey(tokens, extra_key/cache namespace)
root
 ├── [A B C]
 │      ├── [D E] ──► KV indices for prefix A B C D E
 │      └── [X Y]
 └── [M N]

new request: [A B C D Q ...]
                  │ page-align + tree walk
                  ▼
match [A B C D] (node may split at D)
  ├── device_prefix_len
  ├── last_device_node / best_match_node
  └── KV indices reused by request row
```

### Ownership、锁与回收

```text
Radix tree node
  key segment + KV index values
  lock_ref > 0 ──► protected: active request/path depends on it
  lock_ref = 0 ──► evictable candidate under configured policy

request starts/extends
  match prefix ──► lock/ref path ──► use KV

request finishes/chunks
  insert page-aligned newly computed KV
  deduplicate overlapping entries
  release request ownership / adjust locks
  allocator.free only for KV no longer owned by request or cache
```

Tree key 表达 token prefix identity，value 表达 KV pool indices；它不是直接存放每层 K/V tensor bytes 的 Python tree。Active request 与 cache 各自持有引用，错误地提前 free 会让 attention 读取被复用的 slot；错误地不释放则导致 cache capacity 逐渐耗尽。

## Token 到 KV 分配

SGLang 把“request 的第 i 个 token 对应哪个 KV slot”和“KV tensor storage”分开。Request-to-token pool 保存 row mapping；token-to-KV pool/allocator 管理实际 slot/page indices。

```text
Req.kv.req_pool_idx
       │ row in ReqToTokenPool
       ▼
req_to_token[request_row, token_position] = kv_slot_index
                                                   │
                                                   ▼
TokenToKVPool / per-layer K,V tensors[kv_slot_index]

EXTEND:
prefix_lens + seq_lens + last_loc + extend_num_tokens
       └── PagedTokenToKVPoolAllocator.alloc_extend
             └── page-aligned output indices for uncached suffix

DECODE:
next seq_lens + last_loc
       └── PagedTokenToKVPoolAllocator.alloc_decode
             └── one/few output indices; allocate a page only at boundary
```

固定 commit 的 paged allocator 可以选择 Triton allocation kernels 或 naive implementation。它只分配 indices，不执行 attention；ModelRunner/attention backend 之后用 `out_cache_loc` 把新 K/V 写入相应 slot。

### Page boundary 示例

```text
page_size = 4
free pages: P7, P9, P12

request A current slots: [P3:0 P3:1 P3:2]
decode next token       → reuse P3:3, no new page
next decode boundary    → alloc P7, use P7:0

request B extend 6 tokens from aligned prefix
                       → alloc enough pages/locations for six suffix positions
```

真实 allocator 用 device tensors 和 vectorized/Triton kernels 计算 indices；示例只表达 ownership，不暗示物理地址连续。

## ModelRunner

Scheduler 的 `run_batch` 最终经 model worker 将 `ScheduleBatch` 转为 `ForwardBatch` 并调用 `ModelRunner.forward`。Runner 的 `_forward_raw` 依据 forward mode 与 graph eligibility 选择 decode graph、prefill graph、split-prefill 或 eager runner。

```text
ScheduleBatch
  └── ModelWorker.forward_batch_generation
       └── ForwardBatch.init_new
            └── ModelRunner.forward
                 ├── forward context(attn_backend)
                 ├── graph eligibility
                 ├── decode CUDA Graph replay, if eligible
                 ├── prefill CUDA Graph, if eligible
                 ├── split-prefill path, if selected
                 └── eager runner otherwise
                        │
                        ▼
                  model.forward
                    ├── embedding / norm / QKV
                    ├── attention backend + KV write/read
                    ├── Dense MLP or MoE
                    └── logits processor
                        │
                        ▼
                 ModelRunner.sample
                    └── next_token_ids + logprobs/aux output
```

Attention backend 是 runner 初始化/forward context 的依赖，候选包括 FlashInfer、FlashAttention、Triton、FlashMLA/TRT-LLM 及模型/硬件专用 backend。选中哪个取决于 GPU、dtype、attention 类型、模型结构与配置；RadixCache 本身不等于某个 attention kernel。

### Model op 到 CUDA

```text
SGLang model/layer
  ├── Linear / quantized GEMM
  ├── RMSNorm / RoPE
  ├── attention backend
  ├── fused MoE / expert dispatch
  └── sampler
        │
        ├── PyTorch/ATen
        ├── Triton kernels
        ├── sgl-kernel AOT/JIT CUDA
        ├── CUTLASS / FlashInfer / FlashAttention / other backend
        └── NCCL / EP communication
                │
                ▼
      [[llm-gpu-kernel-execution-path|stream、kernel、warp、Tensor Core、HBM]]
```

## Overlap 与 CUDA Graph

Overlap scheduler 让 CPU 在上一 batch 的 GPU work 未完全完成时准备下一 batch，并通过 future indices、streams/events 和 result queue 延后结果处理。它不是“取消同步”，而是把必要同步缩小到数据真正被消费的位置。

```text
normal:
CPU scheduler: [plan N][launch N][process N][plan N+1][launch N+1]
GPU:                         [forward N]                 [forward N+1]

overlap:
CPU scheduler: [plan N][launch N][plan N+1 / process N-1][launch N+1]
GPU forward:              [forward N]────────────[forward N+1]
schedule stream:     metadata/copies ─event/wait─ metadata/copies
result queue:              enqueue N ─────later process N
```

Fixed commit 的 `Scheduler.event_loop_overlap` 会在 result queue 中保留 batch/result，并根据 batch 类型决定何时禁止 overlap、先处理上一结果或加 WAR barrier。Cross-stream tensor lifetime、request object 被下一轮修改、KV slot 回收都需要显式保护。

CUDA Graph 是另一维度：

```text
ForwardBatch
  ├── decode graph eligible ──► decode_cuda_graph_runner.execute
  ├── extend + prefill graph eligible ──► prefill_cuda_graph_runner.execute
  ├── split prefill ──► split-forward path
  └── dynamic/ineligible ──► eager_runner.execute

overlap scheduling = CPU/GPU iteration pipeline
CUDA Graph          = replay a captured GPU launch graph
```

二者可以组合，但解决的问题不同。Graph 要求 shape/buffer/control path 可复用；overlap 要求正确的 future values 与 stream dependency。

## TP、PP、EP

```text
Tensor Parallel (TP)
  one Scheduler coordinates rank group
  sharded linear/attention work ─═ collective ═► next layer

Pipeline Parallel (PP)
  stage 0 ForwardBatch ─═ PPProxyTensors ═► stage 1 ... last stage
  scheduler PP mixin coordinates microbatch/event-loop variants

Expert Parallel (EP)
  router top-k
    ─═ dispatch/all-to-all ═► expert ranks
    ── grouped expert GEMM
    ◄═ combine/all-to-all ═─ outputs
```

- TP 影响单层 tensor partition 与 collective。
- PP 在 stage 间传 `PPProxyTensors`，最后 stage 产生最终 logits/sampling；它也约束 overlap。
- EP 使 MoE token routing、load balance 与 grouped GEMM 成为执行关键路径。
- Data-parallel controller/attention DP 负责不同 requests/ranks 的协调，仍不等于平台 gateway 的跨 endpoint routing。

## P/D Bootstrap 边界

SGLang 有专门的 disaggregation prefill/decode scheduler mixins 和 common bootstrap 模块。P/D 模式不是把普通 `event_loop_normal` 中间简单切一刀：Prefill 与 Decode 分别维护 request、KV 与 transfer 状态，并用 bootstrap/transfer metadata 建立两端对应关系。

```text
[Platform / router]
choose Prefill endpoint and Decode endpoint
       │ request + bootstrap/transfer identity
       ▼
[SGLang Prefill Scheduler]
event_loop_*_disagg_prefill
  ├── RadixCache.match_prefix
  ├── ScheduleBatch EXTEND / prefill forward
  ├── maybe send cached-prefix chunk
  └── publish KV availability / transfer state
       │ control metadata ──► Decode scheduler
       └══ KV payload through selected transfer backend ══►

[SGLang Decode Scheduler]
event_loop_*_disagg_decode
  ├── bootstrap/register receiving buffers
  ├── PREBUILT / decode-side request state
  ├── wait/poll transfer readiness
  └── prepare_for_decode → attention reads transferred KV
```

职责分界：

- Platform 决定两个 endpoints 与客户端路由。
- Bootstrap/control path 交换 request/rank/memory/transport identity。
- Transfer backend 移动 KV payload，可能是 GPU direct、RDMA、IPC 或其他实现。
- Radix/request/token pools 必须把 transferred KV 映射到 decode 本地可读 indices。
- Decode 在 readiness 前不能启动依赖这些 KV 的 attention。

Prefix cache hit 还会改变传输范围：Prefill 端可能已有 cached prefix，Decode 端也可能已有部分 prefix。两端必须用相同 token/cache namespace 和 layout 计算实际缺口；不能仅凭“prefix hash 一样”假设 bytes 已就绪。

## Detokenizer 与流式返回

GPU sampling 得到 token IDs 后，scheduler 先更新 `Req`、stop state、cache ownership 和 batch，然后发送输出。`DetokenizerManager.event_loop` 接收 scheduler output，增量 decode，并把结果发回 TokenizerManager；后者唤醒对应 request 的异步响应流。

```text
[GPU]
ModelRunner.sample ──► next_token_ids / logprobs
        │
        ▼
[Scheduler]
process_batch_result
  ├── append output token / stop check
  ├── cache finished/chunked request state
  ├── free or preserve KV ownership
  ├── update running batch
  └── send output IPC
        │
        ▼
[DetokenizerManager]
incremental decode token IDs → text delta
        │ output IPC
        ▼
[TokenizerManager]
rid_to_state queue/event → _wait_one_response → API stream → Client
```

取消同样跨越多个 owner：HTTP disconnect/abort 从 TokenizerManager 进入 scheduler，scheduler 移除 waiting/running request 并在安全时释放 KV；已 launch 的 GPU batch 可能仍返回结果，必须识别为已取消或过期输出。已经发给客户端的 token 不能靠重新发起请求透明撤销。

### Aggregated 请求全链

```text
Client
 ──► TokenizerManager.generate_request
 ──► tokenize + _send_one_request
 ──► Scheduler.ingest_requests
 ──► RadixCache.match_prefix
 ──► PrefillAdder / get_next_batch_to_run
 ──► ScheduleBatch.prepare_for_extend
 ──► PagedTokenToKVPoolAllocator.alloc_extend
 ──► ModelRunner.forward/sample ──► GPU kernels
 ──► Scheduler.process_batch_result
 ──► ScheduleBatch.prepare_for_decode + alloc_decode
 ──► repeated decode forwards
 ──► DetokenizerManager.event_loop
 ──► TokenizerManager async response ──► SSE/client
```

这条链是三个平台页进入 SGLang engine 后的共同下半段。平台可以添加自己的 gateway、router、P/D coordinator 和 autoscaling，但不应把 RadixCache、ScheduleBatch 或 GPU backend 的状态所有权画到平台路由器里。
