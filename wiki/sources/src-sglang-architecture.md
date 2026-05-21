---
title: SGLang 架构与设计思路分析
tags: [architecture, llm-inference, ai-infra, kv-cache, speculative-decoding]
date: 2026-05-15
sources: [sglang-architecture-analysis.md]
related: [[sglang], [[radix-attention]], [[paged-attention]], [[speculative-decoding]], [[prefill-decode-disaggregation]], [[vllm]], [[flash-attention]], [[mooncake]]]
---

# SGLang 架构与设计思路分析

> 原文：`raw/sglang-architecture-analysis.md` · 仓库：https://github.com/sgl-project/sglang · 分析版本：HEAD `50f4058`（main，2026-05-13）· 范围：`python/sglang/`

## 一句话定位

[[sglang]] 是面向大规模 LLM 推理的高性能引擎：**4 进程异步流水线**（HTTP / TokenizerManager / Scheduler / DetokenizerManager）把 CPU 分词、GPU 推理、CPU 反分词彻底解耦；[[radix-attention]] 把 KV 缓存复用从 [[vllm]] 的 16-token block 粒度做到 **token 级**，叠加 **7 套可插拔投机解码**（EAGLE / EAGLE-v2 / 多层 EAGLE / FrozenKV-MTP / NGRAM / DFLASH / Standalone）+ **[[prefill-decode-disaggregation]]**（Mooncake / NIXL / Mori / Ascend 4 后端）+ **10+ attention 后端**（FlashInfer / FA3 / Triton / FlashMLA / NSA / DSV4 / ...），是 vLLM 之外的主流开源推理栈。

## 核心架构图

```
                              ┌────────────────────────────────────────────────────┐
                              │   sglang/launch_server.py  (Process 0: HTTP main)  │
                              │   ├─ Default: http_server.py:launch_server()       │
                              │   ├─ --grpc-mode → grpc_server.py:serve_grpc       │
                              │   ├─ --encoder-only → disaggregation/encode_*      │
                              │   └─ --use-ray → ray/http_server.py                │
                              └───────────────────┬────────────────────────────────┘
                                                  │ FastAPI/uvicorn
                                                  v
                            ┌─────────────────────────────────────────────┐
                            │  OpenAI / Anthropic / Ollama adapters       │
                            │  entrypoints/openai/serving_chat.py …       │
                            │  (ChatCompletionRequest → GenerateReqInput) │
                            └─────────────────────┬───────────────────────┘
                                                  │ in-process call
                                                  v
       ╔═══════════════════════════════════════════════════════════════════════════╗
       ║  TokenizerManager  (managers/tokenizer_manager.py)  — main process        ║
       ║  • async generate_request() @ L516                                        ║
       ║  • tokenize text → input_ids                                              ║
       ║  • send_to_scheduler.send_pyobj(TokenizedGenerateReqInput)                ║
       ║  • _wait_one_response() ← stream from detokenizer                         ║
       ╚════════════════╤═══════════════════════════════════╤══════════════════════╝
                        │ ZMQ PUSH                          ▲ ZMQ PULL
        scheduler_input_ipc_name                      tokenizer_ipc_name
                        v                                   │
       ╔═══════════════════════════════════════╗  ╔════════╧═══════════════════════╗
       ║  Scheduler (subprocess, TP rank 0..N) ║  ║  DetokenizerManager (subproc.) ║
       ║  managers/scheduler.py                ║  ║  managers/detokenizer_manager  ║
       ║  • event_loop_normal/_overlap @ 1537  ║  ║  • event_loop @ L140           ║
       ║  • recv_requests @ 1656               ║  ║  • batch_decode(token_ids)     ║
       ║  • get_next_batch_to_run @ 2485       ║  ║    → BatchStrOutput            ║
       ║  • run_batch → ModelRunner.forward    ║  ╚════════╤═══════════════════════╝
       ║  • process_batch_result @ 3170        ║           ▲ ZMQ PULL
       ║    → send BatchTokenIDOutput          ║───────────┘ detokenizer_ipc_name
       ╚════════════════╤══════════════════════╝
                        │  owns the GPU
                        v
       ┌──────────────────────────────────────────────────────────────────────────┐
       │                    Inference Core (within Scheduler proc)                │
       │                                                                          │
       │  ┌──── ScheduleBatch (in-flight) ────┐    ┌──── Mem subsystem ──────┐   │
       │  │ Req[]:                            │    │ RadixCache (tree)       │   │
       │  │   prefix_indices  (cached KV)     │◄──▶│   match_prefix / insert │   │
       │  │   extend_input_len (new tokens)   │    │ ReqToTokenPool          │   │
       │  │   out_cache_loc   (new KV slots)  │    │   (req → token idx)     │   │
       │  │ forward_mode: EXTEND/DECODE/MIXED │    │ TokenToKVPool           │   │
       │  └─────────────────┬─────────────────┘    │   MHA/MLA/NSA variants  │   │
       │                    │                      └─────────────────────────┘   │
       │                    v                                                    │
       │  ┌──── ModelRunner (model_executor/) ────────────────────────────────┐  │
       │  │  ForwardBatch (forward_batch_info.py)                             │  │
       │  │  → AttentionBackend (FlashInfer / FA3 / Triton / FlashMLA / ...)  │  │
       │  │  → CUDA Graph runner (decode replay) / piecewise / breakable      │  │
       │  │  → Sampling (constrained vocab mask, grammar)                     │  │
       │  └───────────────────────────────────────────────────────────────────┘  │
       │                                                                          │
       │  ┌──── Optional mixins (composed into Scheduler via inheritance) ────┐  │
       │  │ • SpeculativeWorker  (EAGLE-2 / NGRAM / MTP / DFLASH / Standalone)│  │
       │  │ • SchedulerDisaggregationPrefillMixin                             │  │
       │  │ • SchedulerDisaggregationDecodeMixin                              │  │
       │  │ • SchedulerPPMixin   (pipeline-parallel)                          │  │
       │  │ • SchedulerDPAttnMixin (DP-attention)                             │  │
       │  │ • SchedulerDllmMixin (diffusion-LLM)                              │  │
       │  └───────────────────────────────────────────────────────────────────┘  │
       └──────────────────────────────────────────────────────────────────────────┘

  External cluster (P/D-disagg mode):
                ┌──────────────────┐    KV transfer    ┌──────────────────┐
                │ Prefill instance │ ════════════════> │ Decode instance  │
                │  (full SGLang)   │  Mooncake / NIXL  │  (full SGLang)   │
                └──────────────────┘  Mori / Ascend    └──────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| **HTTP / RPC 入口** | FastAPI/uvicorn + gRPC + 离线 Engine API；`launch_subprocesses()` 启动 4 进程流水线 |
| **协议适配** | OpenAI / Anthropic / Ollama 三套协议统一翻译成 `GenerateReqInput`，下游无感切换 |
| **TokenizerManager** | 主进程做分词 + ZMQ 出/入；DetokenizerManager 在独立进程做反分词；ZMQ 三段管道 |
| **Scheduler（GPU 主进程）** | 事件循环 + 准入控制 + batch 组装 + 调用 ModelRunner；用 8+ Mixin 拼装 disagg/PP/DPAttn/Dllm 横切特性 |
| **Memory 子系统** | 4 套 RadixCache 变体（vanilla / hi / mamba / swa / cpp）+ 两级 pool（Req→Token, Token→KV）+ 4 种 evict 策略 |
| **ModelRunner** | ForwardMode 调度（EXTEND/DECODE/MIXED/TARGET_VERIFY/DRAFT_EXTEND）；CUDA Graph 预捕获 decode 路径 |
| **Attention 后端** | 10+ 可插拔后端：FlashInfer / FA3-4 / Triton / FlashMLA / NSA / DSV4 / FlexAttention / TorchNative / Wave / AITER / Intel-AMX |
| **投机解码** | 7 算法走 `BaseSpecWorker` + `spec_registry`：EAGLE-2 / EAGLE-v2 / 多层 EAGLE / NGRAM / FrozenKV-MTP / DFLASH / Standalone |
| **P/D 分离** | prefill / decode 节点独立扩容 + 5 KV transfer backend：[[mooncake]] / NIXL / Mori / Ascend / Fake |
| **结构化输出** | xgrammar / outlines / llguidance / reasoner backend；在 sampling 前 apply vocab mask |
| **模型库** | 100+ 模型（LLaMA / Qwen / DeepSeek / Mixtral / Gemma / GPT-OSS / 多模态…） |
| **多模态** | image / audio / video 预处理 + KV 缓存；audio 走 Whisper / Qwen-ASR adapter |
| **分布式** | TP / PP / DP / EP + 专家并行 load balancing |
| **前端 DSL** | SGLang DSL（fork / gen / select）—— 论文里的 "Structured Generation Language" |

**分层约束**：TokenizerManager 不持有 GPU；Mixin 之间互不依赖（disagg prefill / decode mixin 互斥）；RadixCache 4 变体按 attention 类型（MHA/MLA/Mamba/SWA）启动时绑死，不可混用；speculative + chunked prefill + disagg 三选二。

## 关键数据流：端到端请求生命周期

```
Client HTTP POST /v1/chat/completions
   │
   v
┌──────────────────────────────────────────────────────────────────────┐
│ FastAPI handler (http_server.py) → OpenAIServingChat                 │
│   • parse ChatCompletionRequest                                      │
│   • build GenerateReqInput (text or input_ids, sampling_params,      │
│     stream, return_logprob, ...)                                     │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ tokenizer_manager.generate_request(obj)
                             v
┌──────────────────────────────────────────────────────────────────────┐
│ TokenizerManager.generate_request()  (tokenizer_manager.py:516)      │
│   • tokenizer(text) → input_ids                                      │
│   • build TokenizedGenerateReqInput                                  │
│   • send_to_scheduler.send_pyobj(obj)        ─── ZMQ PUSH ───┐       │
│   • await _wait_one_response(rid)   ◄──── ZMQ PULL ────┐     │       │
└──────────────────────────────────────────────────────────│─────│─────┘
                                                          │     │
       scheduler_input_ipc_name (ZMQ PUSH/PULL) ◄─────────│─────┘
                             │                            │
                             v                            │
┌──────────────────────────────────────────────────────────────────────┐
│ Scheduler.event_loop_normal()  (scheduler.py:1537)                   │
│   step 1: recv_requests()                  → drain waiting_queue     │
│   step 2: get_next_batch_to_run()                                    │
│           • RadixCache.match_prefix(req)   → req.prefix_indices      │
│           • PrefillAdder budget check:                               │
│             rem_input_tokens, rem_chunk_tokens, rem_total_tokens     │
│           • chunked prefill if extend_input_len > chunk_size         │
│           • policy = LPM / FCFS / LOF / DFS_WEIGHT                   │
│   step 3: run_batch(batch)                                           │
│           → ModelRunner.forward(ForwardBatch)                        │
│             • ForwardMode = EXTEND / DECODE / MIXED                  │
│             • DECODE: CUDA graph replay (固定 BS)                    │
│             • EXTEND/MIXED: 原生 attention kernel                    │
│             • AttentionBackend.forward_decode / forward_extend       │
│             • sampling (with constrained vocab mask if any)          │
│   step 4: process_batch_result()                                     │
│           • write output_ids                                         │
│           • if finished: tree_cache.insert(req.last_node, new_kv)    │
│           • send_to_detokenizer.send_pyobj(BatchTokenIDOutput) ──┐   │
└──────────────────────────────────────────────────────────────────│───┘
                                                                  │
       detokenizer_ipc_name (ZMQ PUSH/PULL)  ◄───────────────────┘
                             │
                             v
┌──────────────────────────────────────────────────────────────────────┐
│ DetokenizerManager.event_loop()  (detokenizer_manager.py:140)        │
│   • tokenizer.batch_decode(token_ids) → strings                      │
│   • build BatchStrOutput                                             │
│   • send_to_tokenizer.send_pyobj(BatchStrOutput) ─── ZMQ PUSH ───┐   │
└──────────────────────────────────────────────────────────────────│───┘
                                                                  │
       tokenizer_ipc_name (ZMQ PUSH/PULL)  ◄───────────────────── ┘
                             │
                             v
TokenizerManager (main proc) ── SSE stream / final JSON ──> HTTP Client
```

**流水线 overlap**：`event_loop_overlap`（scheduler.py:1564）让 GPU 算 batch N 的同时 CPU 准备 batch N+1，TokenizerManager 同时分词 batch N+2，DetokenizerManager 反分词 batch N−1 —— 4 进程同时活跃。

## RadixCache 复用 + KV pool 联动

```
┌─────────────────────────────────────────────────────────────┐
│ RADIXCACHE (radix_cache.py)                                 │
│ Root                                                        │
│  ├─ [101, 102, 103] → Node A  (value=[kv_0, kv_1, kv_2])    │
│  │   ├─ [104] → Node B  (value=[kv_3])                      │
│  │   └─ [104, 105] → Node C  (value=[kv_4, kv_5])           │
│  └─ [101, 102, 106] → Node D  (value=[kv_6, kv_7, kv_8])    │
│                                                             │
│  match_prefix(input_ids=[101,102,103,104,X]):               │
│    walk tree → match A → match B → return                   │
│      prefix_indices = [kv_0, kv_1, kv_2, kv_3]   (device)   │
│      last_node = B                                          │
│      extend_input_len = len(input) - 4                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ value pointers
                          v
┌─────────────────────────────────────────────────────────────┐
│ TokenToKVPool (memory_pool.py:789, MHA/MLA/NSA variants)    │
│ Physical GPU K, V tensors, flat token-indexed:              │
│  [kv_0] [kv_1] [kv_2] [kv_3] [kv_4] [kv_5] [kv_6] [kv_7]... │
│   └─Node A──────┘ └─B─┘ └─C─────┘ └─D───────────────┘       │
│                                                             │
│ alloc(n) → returns n new token slots (out_cache_loc)        │
│ free(indices) → returns slots after eviction                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ReqToTokenPool (memory_pool.py:128)                         │
│ Shape: [num_reqs+1, max_ctx_len], int32                     │
│ Row i = req_pool_indices[i] holds full KV index list:       │
│   req_0: [kv_0, kv_1, kv_2, kv_3, kv_NEW_0, kv_NEW_1, ...]  │
│   req_1: [kv_6, kv_7, kv_8, kv_NEW_2, ...]                  │
│                                                             │
│ 在 attention kernel 里：                                    │
│   for i in batch:                                           │
│     k_cache[req_to_token[i, :seq_lens[i]]] = ...            │
└─────────────────────────────────────────────────────────────┘
```

## 投机解码（EAGLE-2 默认）

```
Decode step (target accepted last token T_n)
   │
   v
┌─────────────────────────────────────────────────────────────┐
│ Draft model (eagle_worker.py:91)                            │
│  • 1 step forward                                           │
│  • build_tree_kernel_efficient (line 818)                   │
│    propose topk=5 candidates per position, K steps deep     │
│    → tree of ~K×5 draft tokens                              │
│    → tree_mask (谁能 attend 谁) + positions + retrieve_idx  │
└────────────────────────┬────────────────────────────────────┘
                         │ draft_tokens + tree metadata
                         v
┌─────────────────────────────────────────────────────────────┐
│ Target model (single forward pass)                          │
│  • ForwardMode.TARGET_VERIFY                                │
│  • EagleVerifyInput.custom_mask = tree_mask                 │
│  • compute logits for ALL tree leaves in 1 fwd              │
│  • sample top-1 per leaf                                    │
└────────────────────────┬────────────────────────────────────┘
                         │ verified_tokens
                         v
┌─────────────────────────────────────────────────────────────┐
│ Accept prefix (longest path where draft == verify)          │
│  • rollback KV cache to divergence point                    │
│  • on_verify_complete_cpu() feed adaptive controller        │
│    (adaptive_spec_params.py adjusts topk/depth)             │
│  • emit accepted tokens (1~K+1 per step)                    │
└─────────────────────────────────────────────────────────────┘
```

## P/D 分离请求流

```
Client request
   │
   v
┌──────────────────────────────────────────┐
│ Prefill instance (full SGLang scheduler) │
│  • PrefillBootstrapQueue: handshake +    │
│    KV slot prealloc                      │
│  • Run forward (prefill only)            │
│  • release_req_to_metadata_buffer()      │
│  • Queue KVSender (begin transfer)       │
└──────────────────┬───────────────────────┘
                   │
                   v
┌──────────────────────────────────────────┐
│ KV transfer backend (one of):            │
│  • Mooncake (Moonshot KV store, ~80KB)   │
│  • NIXL (NVIDIA GPUDirect RDMA)          │
│  • Mori (ByteDance KV protocol, ~58KB)   │
│  • Ascend (Huawei NPU native)            │
│  • Fake (testing)                        │
│  poll_and_all_reduce() sync across ranks │
└──────────────────┬───────────────────────┘
                   │
                   v
┌──────────────────────────────────────────┐
│ Decode instance (full SGLang scheduler)  │
│  • DecodePreallocQueue: reserve KV       │
│  • Wait for KV transfer completion       │
│  • DecodeTransferQueue → WaitingQueue    │
│    → RunningBatch                        │
│  • Skip prefill, populate forward meta   │
│  • Run decode loop, stream tokens        │
└──────────────────┬───────────────────────┘
                   │
                   v
                Client
```

## 设计决策与哲学

- **4 进程异步流水线**：CPU 分词 / GPU 推理 / CPU 反分词彻底进程化隔离，[[zmq]] pyobj 串联 + Scheduler 内部 `event_loop_overlap` 进一步重叠上轮 GPU 与本轮 CPU 准备 —— 任何 stage 阻塞不卡其他 stage
- **[[radix-attention]] 取代 [[paged-attention]]**：vLLM 16-token block 粒度浪费太多复用机会，LLM workload 里 system prompt / few-shot / agent template 是高度共享的前缀，SGLang 用 token-level radix 树 + flat KV pool 把"任意 token 边界共享"做到极致 —— 论文里 RadixAttention 在 tree-of-thought / few-shot 场景 throughput 1.6-6.4× over vLLM
- **两级 KV pool**：`ReqToTokenPool`（req → token 索引列表）+ `TokenToKVPool`（token 索引 → 物理 KV 槽位）的双跳让 radix 树叶直接指向 KV pool 位置，attention kernel 用 device-resident `req_to_token` 张量做一次 gather —— 既保留 token 级粒度，又能让 kernel 高效访存
- **Scheduler 用 Mixin 拼装**：4000+ 行的 `scheduler.py` 通过 10+ 个 Mixin 把横切关注点解耦 —— open-closed 友好，新加 disagg 后端 / PP 形态不改主类。代价是新人定位某个 hook 实现要跨 8-10 个 mixin 文件
- **7 套投机解码共生**：`BaseSpecWorker` + `spec_registry` 注册表让 EAGLE-2 / EAGLE-v2 / 多层 EAGLE / NGRAM / FrozenKV-MTP / DFLASH / Standalone 共存 —— 不同 workload 选最优。NGRAM 零模型成本适合 retrieval-heavy；MTP 适合 DeepSeek-V3 原生 multi-token-predict 头；EAGLE-2 适合通用模型
- **[[prefill-decode-disaggregation]] + 4 transfer backend**：prefill（compute-bound）和 decode（memory-bound）独立扩容，KV 通过 RDMA / [[mooncake]] / NIXL / Mori / Ascend 跨节点传输。`kv_events.py` 用 ZMQ 发布 KV 事件给 router / observability
- **10+ Attention 后端**：`AttentionBackend` ABC + `attention_registry.py` 注册表 —— FlashInfer 默认 / FA3-4 / Triton / FlashMLA / NSA / DSV4 / FlexAttention / TorchNative / Wave / AITER / Intel-AMX，按硬件 / 模型 / 性能曲线选
- **CUDA Graph 只给 DECODE**：DECODE 形状固定（batch_size × 1 token），适合预捕获 graph replay 消除 CPU launch overhead；EXTEND/MIXED 形状变化走原生 kernel。这是 SGLang 把 decode latency 压到接近 kernel-only 的关键
- **统一三大协议入口**：单 backend 支持 OpenAI / Anthropic / Ollama + gRPC + 原生 Engine SDK，下游 client 无缝切换

## 关键组件深入：RadixCache（核心创新）

**TreeNode** (`mem_cache/radix_cache.py:206`)：`key: RadixKey`（变长 token 序列，支持 bigram 模式给 EAGLE 用）+ `value: torch.Tensor`（指向 `TokenToKVPool` 的 KV 索引张量）+ `children: dict[int, TreeNode]` + `lock_ref: int`（引用计数 >0 时禁止 evict）+ `evicted: bool`（已 evict 的占位，支持增量恢复）。

**match_prefix** (line 360)：从 root walk，每层比 `input_ids[i:]` 和子节点 `key`；部分匹配时 split 节点（原节点截到匹配长度，剩余 token 移到新子节点）；返回 `(device_indices, last_node)` —— 前者是已命中 KV 索引张量（直接喂 attention kernel），后者给后续 insert 用。

**insert** (line 420)：请求完成时在 `req.last_node` 下挂新节点，`key = req.fill_ids[len(prefix):]`，`value = req.out_cache_loc`（本次 forward 新写入的 KV 槽位）；父节点 `lock_ref` 递减，允许 evict。

**Eviction** (line 560)：LRU / LFU / FIFO / SLRU / Priority 4 策略，pop `evictable_leaves` 堆顶，free 该节点 `value` 指向的 KV 槽位，递归向上 unlock。

**vs vLLM 关键差异**：vLLM BlockManager 固定 16 token block + block table，无法在 token 7 处分叉；SGLang radix 树天然支持任意 token 边界 split，`value` 是连续区间索引而非 block 列表。

## 与同类对比

| 维度 | SGLang | [[vllm]] | TensorRT-LLM | TGI |
|------|--------|------|--------------|-----|
| **KV 复用粒度** | token 级（[[radix-attention]]） | 16-token block（[[paged-attention]]） | block | block |
| **前缀共享** | 任意分叉点自动 | 同 block 才共享 | prefix cache | prefix cache |
| **投机解码** | 7 算法 | EAGLE / Medusa | EAGLE / Medusa / ReDrafter | speculative-decoding |
| **P/D 分离** | 5 后端 | 实验 | ✅ | 实验 |
| **Attention 后端** | 10+ | FlashAttn / xFormers / TorchSDPA | TRT 内核 | FlashAttn |
| **结构化输出** | 4 backend | outlines | 有限 | outlines |
| **多协议入口** | OpenAI / Anthropic / Ollama / gRPC / Engine | OpenAI | TensorRT 原生 | TGI 原生 |
| **国产硬件** | Ascend NPU / Wave / AITER 一等公民 | 实验 | — | — |
| **前端 DSL** | SGLang DSL（fork/gen/select） | — | — | — |
| **典型适用** | agent / tool-use / RAG / 结构化生成 / 多模态 | 通用 LLM serving | 极致延迟 | HF 生态 |

## 相关页面

- 项目本体：[[sglang]]
- 核心算法：[[radix-attention]]（RadixCache 树）、[[paged-attention]]（vLLM 的对照系统）、[[speculative-decoding]]（EAGLE / NGRAM / MTP）、[[prefill-decode-disaggregation]]
- 同类系统：[[vllm]]（最直接对标）
- 依赖：[[flash-attention]]（FlashInfer / FA3 / FlashMLA）、[[mooncake]]（KV transfer 后端）、[[zmq]]（4 进程 IPC）
