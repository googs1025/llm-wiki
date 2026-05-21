# SGLang 架构与设计思路分析

> 仓库：https://github.com/sgl-project/sglang · 分析日期：2026-05-15 · HEAD：`50f4058` (main, active development) · 分析范围：`python/sglang/`（推理引擎核心，跳过 `rust/` 和 `sgl-kernel/`）

## 一句话定位

**SGLang 是面向大规模 LLM 推理的高性能引擎**：4 进程异步流水线（HTTP server / TokenizerManager / Scheduler / DetokenizerManager）把 CPU 分词、GPU 推理、CPU 反分词彻底解耦；**RadixCache** 把 KV 缓存复用从 vLLM 的 16-token block 粒度做到 token 级（论文里的 "RadixAttention"），叠加 **7 套可插拔投机解码**（EAGLE / EAGLE-v2 / 多层 EAGLE / MTP / NGRAM / DFLASH / Standalone）+ **prefill/decode 分离** + **10+ attention 后端**，是 vLLM 之外的主流开源推理栈。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| **HTTP / RPC 入口** | `srt/entrypoints/http_server.py`、`grpc_server.py`、`engine.py` | FastAPI/uvicorn + gRPC + 离线 Engine API；`launch_subprocesses()` 启动 4 进程 |
| **协议适配** | `entrypoints/openai/serving_*.py`、`entrypoints/anthropic/`、`entrypoints/ollama/` | OpenAI / Anthropic / Ollama 三套协议 → 统一 `GenerateReqInput` |
| **TokenizerManager** | `managers/tokenizer_manager.py`、`detokenizer_manager.py` | 主进程负责分词 + ZMQ 出/入；DetokenizerManager 在独立进程做反分词；ZMQ 三段管道 |
| **Scheduler（GPU 主进程）** | `managers/scheduler.py`、`schedule_batch.py`、`schedule_policy.py` | 事件循环、请求准入、batch 组装、调用 ModelRunner；用 8+ Mixin 拼装 disagg/PP/DPAttn/Dllm 等横切特性 |
| **Memory 子系统** | `mem_cache/radix_cache.py`、`memory_pool.py`、`allocator.py` | 4 套 RadixCache 变体（vanilla / hi / mamba / swa / cpp）+ 两级 pool（Req→Token, Token→KV）；4 种 evict 策略 |
| **ModelRunner** | `model_executor/model_runner.py`、`forward_batch_info.py`、`cuda_graph_runner.py` | ForwardMode 调度（EXTEND/DECODE/MIXED/TARGET_VERIFY/DRAFT_EXTEND）；CUDA Graph 预捕获 decode 路径 |
| **Attention 后端** | `srt/layers/attention/` | 10+ 可插拔后端：FlashInfer / FA3-4 / Triton / FlashMLA / NSA / DSV4 / FlexAttention / TorchNative / Wave / AITER / Intel-AMX |
| **投机解码** | `srt/speculative/` | 7 算法走 `BaseSpecWorker` + `spec_registry`：EAGLE-2 / EAGLE-v2 / 多层 EAGLE / NGRAM / FrozenKV-MTP / DFLASH / Standalone |
| **P/D 分离** | `srt/disaggregation/` | prefill.py + decode.py + kv_events.py + 5 transfer backend：Mooncake / NIXL / Mori / Ascend / Fake |
| **结构化输出** | `srt/constrained/` | xgrammar / outlines / llguidance / reasoner backend；在 sampling 前 apply vocab mask |
| **模型库** | `srt/models/` | 100+ 模型实现（LLaMA / Qwen / DeepSeek / Mixtral / Gemma / GPT-OSS / 多模态…） |
| **多模态** | `srt/multimodal/`、`srt/multimodal_gen/` | image / audio / video 预处理 + KV 缓存；audio 走 Whisper / Qwen-ASR adapter |
| **分布式** | `srt/distributed/`、`srt/elastic_ep/`、`srt/eplb/` | TP / PP / DP / EP；专家并行 + load balancing |
| **前端 DSL** | `python/sglang/lang/` | SGLang DSL（fork / gen / select）—— 论文里的 "Structured Generation Language"，编译到 RadixCache 友好的执行计划 |

**分层约束**：
- **TokenizerManager 不持有 GPU**：所有 GPU 状态都在 Scheduler subprocess，TokenizerManager 不可直接调 PyTorch
- **Mixin 只能横向扩展 Scheduler**：禁止 mixin 之间互相依赖（实际上 disagg 的 prefill/decode mixin 是互斥的）
- **RadixCache 4 变体不可混用**：必须根据 attention 类型（MHA/MLA/Mamba/SWA）启动时绑死
- **Speculative + chunked prefill + disagg 三选二**：组合限制写在 `server_args.py` 启动校验里

## 关键数据流

### 端到端请求生命周期（标准 HTTP 模式）

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

**关键 IPC 通道**：

| 方向 | 类型 | IPC name | 消息 |
|------|------|----------|------|
| HTTP → TokenizerManager | 进程内 async call | — | `GenerateReqInput` |
| TokenizerManager → Scheduler | ZMQ PUSH/PULL | `scheduler_input_ipc_name` | `TokenizedGenerateReqInput` / `BatchTokenizedGenerateReqInput` |
| Scheduler → DetokenizerManager | ZMQ PUSH/PULL | `detokenizer_ipc_name` | `BatchTokenIDOutput` |
| DetokenizerManager → TokenizerManager | ZMQ PUSH/PULL | `tokenizer_ipc_name` | `BatchStrOutput` |

**流水线 overlap**：`event_loop_overlap`（scheduler.py:1564）让 GPU 算 batch N 的同时 CPU 准备 batch N+1，TokenizerManager 同时分词 batch N+2，DetokenizerManager 反分词 batch N−1 —— 4 个进程同时活跃。

### RadixCache 复用 + KV pool 联动

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

请求完成时 `tree_cache.insert()` 把 `out_cache_loc` 区段挂到 `last_node` 下，新节点继承复用资格；evict 时 LRU/LFU/FIFO/Priority 选叶子，`lock_ref` 防止 in-flight 请求的节点被收。

### 投机解码（EAGLE-2 默认）

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

### P/D 分离请求流

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

- **4 进程异步流水线**：把 CPU 分词（变长延迟） / GPU 推理（批量化） / CPU 反分词（流式输出）拆到不同 OS 进程，用 ZMQ pyobj 串联。`event_loop_overlap` 进一步在 Scheduler 内部把"上轮 GPU 算完出 token"和"本轮 CPU 准备 next batch"重叠 —— 任何一个 stage 阻塞都不会卡住其他 stage。代价是 ZMQ 序列化 overhead 和多进程内存复制
- **RadixCache 取代 PagedAttention**：vLLM 的 16-token block 粒度浪费太多复用机会。LLM workload 里 system prompt / few-shot / agent tool template 是高度共享的前缀，SGLang 用 token-level radix 树 + flat KV pool 把"任意 token 边界共享"做到极致 —— 论文里 RadixAttention 在 LLaMA-7B 上 throughput 提升 1.6-6.4×。`mem_cache/radix_cache.py:206`（TreeNode）+ `:360`（match_prefix）+ `:420`（insert）
- **两级 KV pool**：`ReqToTokenPool`（req → 该 req 的 token 索引列表）+ `TokenToKVPool`（token 索引 → 物理 KV 槽位）的双跳设计让 RadixCache 树叶可以直接指向 KV pool 位置，attention kernel 用 device-resident `req_to_token` 张量做一次 gather —— 既保留 token 级粒度，又能让 kernel 高效访存
- **Scheduler 用 Mixin 拼装**：4000+ 行的 `scheduler.py` 通过 8+ 个 Mixin（`SchedulerDisaggregationPrefillMixin / SchedulerDisaggregationDecodeMixin / SchedulerPPMixin / SchedulerDPAttnMixin / SchedulerDllmMixin / SchedulerProfilerMixin / SchedulerUpdateWeightsMixin / SchedulerRecvSkipperMixin / SchedulerRuntimeCheckerMixin / SchedulerOutputProcessorMixin`）把横切关注点解耦 —— open-closed 友好，新加 disagg 后端、PP 形态都不改主类。代价是新人定位某个 hook 实现要跨 8-10 个 mixin 文件
- **可插拔投机解码（7 算法共生）**：`BaseSpecWorker` + `spec_registry` 让 EAGLE-2 / EAGLE-v2 / 多层 EAGLE / NGRAM / FrozenKV-MTP / DFLASH / Standalone 共存 —— 不同 workload 选最优。`server_args.speculative_algorithm` 切换；NGRAM 适合 retrieval-heavy（零模型成本），MTP 适合 DeepSeek-V3 原生 multi-token-predict 头，EAGLE-2 适合通用模型
- **P/D 分离 + 4 transfer backend**：把 prefill（compute-bound）和 decode（memory-bound）放到不同实例集群独立扩容，KV 通过 RDMA / Mooncake / NIXL / Mori / Ascend 跨节点传输。`kv_events.py` 用 ZMQ 发布 KV 转移事件给 router / observability，与 [[mooncake]] 这样的"KV store as a service"形成生态
- **10+ Attention 后端**：`base_attn_backend.py:AttentionBackend` ABC + `attention_registry.py` 注册表 —— FlashInfer（默认）/ FA3-4 / Triton / FlashMLA / NSA（稀疏）/ DSV4（DeepSeek 定制）/ FlexAttention / TorchNative / Wave / AITER / Intel-AMX，按硬件 / 模型 / 性能曲线选择
- **CUDA Graph 只给 DECODE 路径**：DECODE 形状固定（batch_size × 1 token），适合预捕获 graph 然后 replay 消除 CPU launch overhead；EXTEND/MIXED 形状变化（extend_input_len 不定），走原生 kernel。这是 SGLang 把 decode latency 压到接近 kernel-only 的关键
- **统一 OpenAI / Anthropic / Ollama 协议**：单一 backend 支持 3 大主流协议 + gRPC + 原生 Engine SDK，下游可以无缝切换 client。代价是 entrypoints 目录膨胀（10+ 文件）

## 关键组件深入解读

### RadixCache（`mem_cache/radix_cache.py`）

**TreeNode**（line 206）：
- `key: RadixKey` —— 变长 token 序列（支持 bigram 模式，给 EAGLE 用）
- `value: torch.Tensor` —— 指向 `TokenToKVPool` 的 KV 索引张量
- `children: dict[int, TreeNode]` —— 首 token 到子节点的映射
- `lock_ref: int` —— 引用计数，>0 时禁止 evict（保护 in-flight 请求）
- `evicted: bool` —— 已被 evict 的占位（用于增量恢复）

**match_prefix(input_ids)**（line 360）：
1. 从 root 开始 walk，每层比较 `input_ids[i:]` 和子节点 `key`
2. 部分匹配时 split 节点：原节点截断到匹配长度，剩余 token 移到新子节点
3. 返回 `(device_indices, last_node)`：前者是已命中的 KV 索引张量（直接喂 attention kernel），后者是匹配链尾节点（给后续 insert 用）

**insert(req)**（line 420）：
1. 在 `req.last_node` 下挂新节点，`key = req.fill_ids[len(prefix):]`
2. `value` 取 `req.out_cache_loc`（这次 forward 新写入的 KV 槽位）
3. 父节点的 `lock_ref` 递减 —— 完成后可以被 evict

**Eviction（line 560）**：4 种策略 LRU / LFU / FIFO / SLRU / Priority，evict 时 pop `evictable_leaves` 堆顶，free 该节点 `value` 指向的 KV 槽位，递归向上 unlock

**vs vLLM 关键差异**：vLLM 的 BlockManager 用固定 16 token block + block table，无法做"在 token 7 处分叉"；SGLang 用 radix 树天然支持任意 token 边界 split，并且 `value` 是连续区间索引而非 block 列表

### Scheduler 主循环（`managers/scheduler.py`）

`event_loop_normal()` @ L1537 单次迭代：

```python
# 简化伪代码
while True:
    recv_reqs = self.recv_requests()                    # L1656 ZMQ NOBLOCK
    self.process_input_requests(recv_reqs)              # L1842 → waiting_queue

    batch = self.get_next_batch_to_run()                # L2485
    if batch is None: continue

    result = self.run_batch(batch)                      # L2996 ModelRunner.forward
    self.process_batch_result(batch, result)            # L3170
```

`get_next_batch_to_run()` 核心逻辑：
1. 先看 `running_batch`（已在 DECODE 的请求）—— 若 KV 池快满，触发 preempt 把低优先级 req 放回 waiting
2. 调用 `PrefillAdder.add_prefill_reqs()`（schedule_policy.py:407）按预算入新 prefill
3. 决定 `forward_mode`：纯 prefill → EXTEND；纯 decode → DECODE；混合 → MIXED（chunked prefill）

`event_loop_overlap()` @ L1564 —— 引入 `result_queue: deque[Future]`，GPU 算 batch N 时 CPU 已经在 build batch N+1，下一轮 wait 上一 future。`is_disable_overlap_for_batch()` @ L1618 在连续 prefill 时禁用 overlap，保 TTFT

## 与同类对比

| 维度 | SGLang | vLLM | TensorRT-LLM | TGI |
|------|--------|------|--------------|-----|
| **KV 复用粒度** | token 级（RadixCache 树） | 16-token block（PagedAttention） | block | block |
| **前缀共享** | 任意分叉点自动 | 同 block 才共享 | prefix cache（block） | prefix cache |
| **投机解码** | 7 算法（EAGLE / NGRAM / MTP / DFLASH / Standalone / 多层 EAGLE / v2）| EAGLE / Medusa | EAGLE / Medusa / ReDrafter | speculative-decoding |
| **P/D 分离** | 5 后端（Mooncake / NIXL / Mori / Ascend / Fake）| 实验 | ✅ | 实验 |
| **Attention 后端** | 10+ (FlashInfer / FA3-4 / Triton / FlashMLA / NSA / DSV4 / Flex / TorchNative / Wave / AITER / Intel-AMX) | FlashAttn / xFormers / TorchSDPA | TRT 内核 | FlashAttn |
| **结构化输出** | xgrammar / outlines / llguidance / reasoner | outlines | 有限 | outlines |
| **多协议入口** | OpenAI / Anthropic / Ollama / gRPC / Engine | OpenAI | TensorRT 原生 | TGI 原生 |
| **国产硬件** | Ascend NPU / Wave / AITER 一等公民 | 实验 | — | — |
| **前端 DSL** | SGLang DSL（fork/gen/select 结构化生成） | — | — | — |
| **典型适用** | agent / tool-use / RAG / 结构化生成 / 多模态 | 通用 LLM serving | 极致延迟 | HuggingFace 生态 |

## 性能 / 资源开销

| 指标 | 实际表现 |
|------|---------|
| **prefix 缓存命中收益** | RadixAttention 论文：LLaMA-7B 在 tree-of-thought / few-shot 场景 throughput 1.6-6.4× over vLLM |
| **decode latency** | CUDA graph replay → 单步 decode latency ≈ kernel 自身时间（CPU overhead 接近 0） |
| **流水线 overlap** | 4 进程异步 + Scheduler 内 overlap → 单 GPU 占用率持续 95%+（不被 CPU prep / detokenize 卡住） |
| **投机解码加速** | EAGLE-2 默认 topk=5、step=5：典型 1.5-2.5× decode 加速（视模型 / 数据接受率而定） |
| **P/D 分离收益** | 长 prefill / 长 decode workload：吞吐 1.3-2× over collocated（compute-bound 和 memory-bound 独立扩容） |
| **冷启动** | CUDA graph 捕获 + warmup → ~30-90s（与 model 大小相关） |
| **稳态显存** | 模型权重 + KV pool（默认占用剩余 80-90% GPU mem）+ buffers |

## 安全模型

- **信任边界**：HTTP / gRPC 入口是公网可达；TokenizerManager 和 Scheduler 都假设输入是已认证的（无内置 auth，要靠前置 gateway）
- **进程隔离**：Scheduler subprocess 持有 GPU 状态，崩了主进程会 propagate；TokenizerManager 不持有 GPU 防 OOM 雪崩
- **权重更新通道**：`UpdateWeights*` 系列 RPC 走 ZMQ + 显式 secret token（避免恶意权重热替换）
- **结构化输出 mask**：通过 grammar 强制输出格式，可以缓解（不能完全杜绝）prompt-injection 让模型输出非法 JSON
- **多模态输入**：image / audio 走独立 receiver，不在主进程解码（防 codec 漏洞）
- **未自带审计 / 限流 / RBAC**：需要外接 gateway（如 [[agentgateway]]）做 token 计量、rate limit、prompt 审计
