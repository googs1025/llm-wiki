---
title: NVIDIA Dynamo 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D
tags: [analysis, dynamo, llm-serving, vllm, sglang, kv-aware-routing, nixl]
date: 2026-10-11
sources: [dynamo-architecture-analysis.md]
related: ["[[dynamo]]", "[[llm-inference-request-lifecycle]]", "[[vllm-gpu-execution-path]]", "[[sglang-gpu-execution-path]]", "[[llm-gpu-kernel-execution-path]]", "[[inference-routing]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]"]
---

# NVIDIA Dynamo 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D

本页追踪 Dynamo Frontend 收到 OpenAI-compatible 请求后，如何通过 Distributed Runtime、KV-aware routing 与 backend workers 进入 vLLM 或 SGLang，并区分 aggregated 与 Prefill/Decode 分离路径。它还将 request、event、discovery 三个 plane 分开，避免把 KV event 当作 KV tensor transfer。

Dynamo 的统一层在 engine 之上：Frontend/preprocessor、router、runtime endpoint 和 worker handler 负责跨进程/跨节点协调；进入 vLLM `AsyncLLM` 或 SGLang `TokenizerManager/Scheduler` 后，batch、KV allocation 与 GPU kernels 仍由 engine 负责。

## 当前源码快照与结论范围

核验日期：2026-10-11。

- 官方仓库：[ai-dynamo/dynamo@`b208989fbe1cfbfde64d11334d8af4ff04fe1a99`](https://github.com/ai-dynamo/dynamo/tree/b208989fbe1cfbfde64d11334d8af4ff04fe1a99)。
- 本地 `/Users/zhenyu.jiang/dynamo` 指向个人 fork 且停在 `4d28ee2d93b4`，本页不使用它定义 current truth。
- 当前官方架构页明确描述 Frontend → PrefillRouter → Prefill → metadata → Decode → NIXL KV transfer → token stream，并分别提供 vLLM/SGLang aggregated 与 disaggregated launch 文档。
- 既有 [[src-dynamo-architecture]] 保存较早 raw-backed 分析；本页的 symbol 与能力状态固定到上述 commit。

## Frontend 与 Runtime 所有权

```text
[Client]
   │ OpenAI-compatible HTTP/SSE
   ▼
[Dynamo Frontend]
   validate · chat template · tokenize · request extensions · postprocess
   │ preprocessed request / token sequence / routing hints
   ▼
[Router / PrefillRouter]
   KV overlap · active prefill/decode load · policy/admission
   │ runtime endpoint request
   ▼
[Distributed Runtime]
   Namespace → Component → Endpoint → endpoint instance
   │ request plane: direct TCP or NATS
   ├─────────────────────────────────────────┐
   ▼                                         ▼
[Aggregated worker]                 [Prefill + Decode workers]
   │ engine handler                           │ NIXL/engine handoff
   ▼                                          ▼
vLLM or SGLang → GPU                vLLM or SGLang → GPU
   │                                          │
   └────────────────── token stream ──────────┘
                         │ Frontend postprocess/detokenize
                         ▼
                       Client
```

### Runtime 的四级对象

| 对象 | 所有权 | 请求路径作用 |
|---|---|---|
| `DistributedRuntime` | 进程级连接、background tasks、cancellation | 承载 discovery/request/event clients |
| `Namespace` | 一个 deployment/model group 的逻辑隔离 | 防止 endpoint 名称跨部署碰撞 |
| `Component` | 同角色 workers，如 frontend/prefill/decode | 建立 membership 与 endpoint group |
| `Endpoint` | `generate`、`clear_kv_blocks`、metrics 等服务 | typed/streaming RPC 目标 |

Runtime 解决 endpoint 发现和消息 transport，不替代 engine scheduler。一个 Runtime request 可以流式返回很多 token chunks，但 GPU iteration 仍由 backend engine 决定。

## 支持矩阵

| Engine | Serving 形态 | 状态 | 固定 commit 证据 |
|---|---|---|---|
| vLLM | Aggregated | documented | vLLM backend overview 与 `examples/backends/vllm/launch/agg.sh` |
| vLLM | P/D | documented | disaggregated architecture、vLLM Prefill/Decode handlers、NIXL connector tests/recipes |
| SGLang | Aggregated | documented | SGLang backend overview 与 `examples/backends/sglang/launch/agg.sh` |
| SGLang | P/D | documented | SGLang disaggregation guide、Prefill/Decode handlers 与 `launch/disagg.sh` |

“documented”只表示基础组合有官方路径；feature pair 的成熟度仍不同。例如固定 commit 的 SGLang 文档把 disaggregated remote-prefill cancellation、LoRA+P/D 等部分组合标成 limited/未做完整端到端验证。

## vLLM × Aggregated

Aggregated worker 本地完成 prefill 与 decode。Frontend 可用 KV-aware router 在多个 aggregated workers 中选一个；被选 worker 的 Dynamo handler 将请求适配给 vLLM native generate API，并把 engine output 转成 Dynamo/OpenAI stream。

```text
Client
  ──► Frontend preprocess/tokenize
  ──► KV router or load-balancer selects aggregated vLLM endpoint
  ──► Runtime request plane → vLLM DecodeWorkerHandler(aggregated mode)
         ├── request → vLLM GenerateRequest/SamplingParams
         ├── engine_client.generate / AsyncLLM.generate
         ├── EngineCore → Scheduler → GPUModelRunner
         ├── prefill and decode share local worker/KV
         └── async ModelRunner outputs
  ◄── Runtime response stream
  ◄── Frontend postprocess/detokenize/SSE
```

固定 commit 的 `dynamo.vllm.handlers.DecodeWorkerHandler.generate` 同时承载 aggregated 与 decode-side path；是否要求 remote prefill 由 worker mode/request annotations 决定。进入 vLLM 后见 [[vllm-gpu-execution-path]]。

## vLLM × P/D

vLLM P/D 是同步 prefill-first 契约：Prefill 完成后返回 `kv_transfer_params`（block IDs、remote worker/connector 信息等 backend metadata），router 将其注入 Decode request。

```text
Client       Frontend/PrefillRouter      Prefill vLLM handler       Decode vLLM handler
  │ request            │                          │                         │
  ├───────────────────►│ preprocess/tokenize      │                         │
  │                    ├─KV/load select prefill──►│                         │
  │                    │                          ├─AsyncLLM prefill        │
  │                    │                          ├─write/export KV         │
  │                    │◄─disaggregated_params────┤                         │
  │                    ├─select decode + inject kv_transfer_params─────────►│
  │                    │                          │◄══ NIXL KV transfer ═══►│
  │                    │                          │                         ├─load/wait
  │                    │                          │                         ├─decode GPU
  │                    │◄──────────────────────── token stream ─────────────┤
  │◄─Frontend SSE──────┤
```

Dynamo `dynamo.vllm.handlers.PrefillWorkerHandler.generate` 负责 prefill worker endpoint；`DecodeWorkerHandler.generate` 负责 decode/aggregated endpoint。Worker handler 包装 vLLM，但 block allocation、connector pre/finish hooks 和 invalid-block recovery属于 [[vllm-gpu-execution-path#P/D Connector 边界|vLLM engine connector]]。

## SGLang × Aggregated

SGLang aggregated worker 使用原生 tokenizer manager/async generation，Dynamo handler 做 request translation、runtime streaming 与错误/cancellation 适配。

```text
Client
  ──► Dynamo Frontend
       ├── SGLang-compatible preprocessing/chat template
       └── route to aggregated SGLang generate endpoint
  ──► dynamo.sglang.request_handlers.llm.DecodeWorkerHandler.generate
       ├── build native GenerateReqInput/payload
       ├── TokenizerManager.generate_request or engine.async_generate
       ├── Scheduler + RadixCache + ModelRunner
       ├── local extend/prefill + decode
       └── token/text chunks
  ◄── Runtime stream ──► Frontend postprocess ──► Client
```

固定 commit 的 `components/src/dynamo/sglang/engine_generate.py` 封装 native request construction/stream；engine 内部完整链见 [[sglang-gpu-execution-path]]。

## SGLang × P/D

SGLang 路径与通用“先 Prefill 后 Decode”图不同：官方 backend guide 明确说明 Dynamo 先路由 Decode worker，再选择 Prefill worker并向两端发送请求，用 SGLang bootstrap server 配合 NIXL/Mooncake 进行 transfer。

```text
Client       Frontend/Router       Decode SGLang handler       Prefill SGLang handler
  │ request       │                         │                            │
  ├──────────────►│ preprocess              │                            │
  │               ├─select decode──────────►│ create/bootstrap context   │
  │               ├─KV-aware select prefill────────────────────────────►│
  │               │                         ├── bootstrap/request ──────►│
  │               │                         │ allocate KV receive pages  │
  │               │                         │◄─ room/transfer metadata ──┤
  │               │                         │                            ├─prefill GPU
  │               │                         │◄══ RDMA/NIXL KV write ═════┤
  │               │                         ├─poll/confirm readiness      │
  │               │                         ├─SGLang decode GPU           │
  │               │◄────── token stream ────┤                            │
  │◄─SSE──────────┤
```

`dynamo.sglang.request_handlers.llm.PrefillWorkerHandler.generate` 生成/返回 bootstrap info并运行 prefill；`dynamo.sglang.request_handlers.llm.DecodeWorkerHandler.generate` 支持 aggregated/disaggregated 两种模式，构造 native request、校验 bootstrap info并处理 token/text stream。SGLang 内部 bootstrap 与 KV mapping 见 [[sglang-gpu-execution-path#P/D Bootstrap 边界|SGLang engine P/D]]。

## KV-aware Routing

Router 的目标不是“命中最多就选谁”，而是估算选择某 worker 后的增量成本。固定 commit 的 Rust `lib/kv-router` 将 KV index、active sequences/load、policy/admission 和 selection/reservation 分离。

```text
preprocessed token sequence / block hashes
              │
              ├───────────────► KvIndexer
              │                  find match details per worker
              │                  cached blocks / overlap confidence
              │
              ├───────────────► Active load tracker
              │                  active prefill tokens
              │                  projected decode blocks / requests
              │
              ▼
SelectionCore.select / select_and_reserve
  ├── filter eligible/healthy/model-compatible workers
  ├── convert overlap to effective prefill discount
  ├── add projected load / policy penalties
  ├── admission or capacity decision
  └── choose endpoint + optional reservation
              │
              ▼
Runtime endpoint request
```

`KvIndexer.find_match_details` 查询路由视图；它不读取 worker 的 K/V tensors。Worker 通过 KV lifecycle events 更新 index，event 丢失或延迟会造成路由视图陈旧；engine 最终仍须验证 local/received KV。

### 反馈闭环

```text
request routed ──► worker executes ──► KV block stored/removed events
      ▲                                      │
      │                                      ··► event plane
      │                                           │
      └──── next selection ◄·· KvIndexer update ──┘

active request reservation ──► projected load ──► completion/cancel releases
```

Prefix locality 与队列负载存在冲突：缓存丰富的 worker 可能已经很忙，空闲 worker 可能需要重新 prefill。Dynamo policy 把二者纳入同一 selection，而不是固定偏向其中一个。

## Request / Event / Discovery Planes

```text
DISCOVERY PLANE
worker register Endpoint instance
  ··► etcd leases OR Kubernetes DynamoWorkerMetadata/EndpointSlice
  ··► Frontend/Router watch membership

REQUEST PLANE
Frontend/Router ──► namespace.component.endpoint
  ──► direct pooled TCP (default) OR brokered NATS
  ──► msgpack/json codec advertised per endpoint
  ◄── streaming responses / errors / cancellation

EVENT PLANE
workers ··► KV lifecycle / telemetry events ··► router/index/planner consumers
  ZMQ (default) OR NATS subjects

KV DATA PLANE
Prefill GPU ══ NIXL/NVLink/PCIe/RDMA ══► Decode GPU
  separate from all three metadata/control planes above
```

Planes 可以选择不同 transport。Discovery stale 时 Runtime 可暂时 inhibit 一个刚失败的 local worker，等待权威 membership 收敛；这不是永久删除 endpoint，也不保证 in-flight request 自动恢复。

## NIXL KV Transfer

```text
[Prefill engine]
logical KV blocks/pages
   │ register/export memory regions + backend metadata
   ▼
disaggregated_params
   ──► Router/Decode: block IDs · addresses/handles · rank/layout identity

[Decode engine]
allocate/reserve destination KV slots
   │ build NIXL transfer descriptors
   ▼
[NIXL]
source GPU memory ══ chosen transport ══► destination GPU memory
   NVLink / PCIe / InfiniBand-UCX / backend-specific path
   │ completion/event
   ▼
Decode engine maps received blocks → request KV view → attention
```

NIXL 是 data movement layer，不决定 endpoint，也不执行 attention。Router只转发 metadata；engine connector 知道具体 KV layout、TP ranks、layer/block mapping与何时可安全读取。Transfer 可以 non-blocking，但 Decode attention 仍需等待相关 bytes 完成。

## Token 返回

```text
[Engine GPU]
logits → sample token ID
   │ engine async generator
   ▼
[Dynamo worker handler]
translate backend chunk / usage / finish / extension fields
   │ Runtime streaming response
   ▼
[Frontend]
postprocess / detokenize when frontend owns decoding
tool/reasoning formatting / OpenAI SSE encoding
   │
   ▼
[Client]
```

Detokenization 位置依 frontend/backend configuration 而变：Frontend 可 tokenize/postprocess，也存在 engine-native text/token stream。页面只要求 ownership 可追踪，不假设所有 backend 都返回同形态 chunk。

### 一次 aggregated request 的共同段

```text
HTTP request
 ──► Frontend preprocess
 ──► KV/load selection
 ──► Runtime generate endpoint
 ──► backend DecodeWorkerHandler(aggregated)
 ──► vLLM AsyncLLM OR SGLang TokenizerManager/async_generate
 ──► engine scheduler/batch/KV
 ──► CUDA kernels
 ──► engine token chunks
 ──► Runtime stream
 ──► Frontend response
```

## 失败、取消与迁移

| 边界 | 当前行为重点 | 不能假设 |
|---|---|---|
| Frontend validation | 在 dispatch 前拒绝非法 protocol/model/params | worker 一定看到 request |
| Runtime endpoint failure | inhibit 本地失败 instance，discovery 决定后续 membership | 已执行的请求必然无副作用 |
| P/D Prefill 失败 | 没有可用 transfer metadata 时 Decode 不应消费 KV | 任意 Decode 都能重新接管 |
| KV transfer 失败 | connector/engine 报错、recompute 或 fail 取决于 backend | index 命中能证明 payload 正确 |
| Client cancellation | Runtime propagation + backend handler/engine abort | 任意阶段都能立即释放 GPU/KV |
| SGLang remote prefill cancellation | 固定 commit backend matrix标为有限；decode-side cancellation能力更完整 | P/D 两腿都有完全相同语义 |
| Worker graceful shutdown | unregister、drain grace、停止接新请求 | Pod 删除自动迁移 sampling state |
| Request migration | 需要 Dynamo/backend 支持并恢复必要 state | 单靠 retry 可保证 token 流一致 |

```text
before first token
  worker fails ──► route retry/migration may be possible if request/KV/state recoverable

after token chunks
  worker fails ──► Frontend has already exposed irreversible stream prefix
                    │
                    ├── resume only with explicit migration contract
                    └── otherwise surface truncated/error stream
```

迁移必须处理 generated tokens、KV、sampling/RNG/grammar/tool state 和 client stream position。Dynamo 的 request migration capability不能推广为每个 backend/feature pairing的透明 exactly-once。

## Planner / Operator 旁路

```text
REQUEST HOT PATH
Client ──► Frontend ──► Router/Runtime ──► Workers ──► token stream
                 ▲                           │
                 │                           │ metrics/load/capacity
                 │                           ·
                 │                           ▼
CONTROL LOOP   Profiler / Planner / AIConfigurator
                 │ desired prefill/decode replicas / config
                 ▼
              DGD / DCD / Operator / Kubernetes
                 │ reconcile deployments/endpoints
                 └··► discovery membership ··► Router/Runtime
```

Planner 根据 workload、SLO、capacity signals 提议副本变化；Operator 实际 reconcile workers。扩缩会经过 model load、endpoint register 和 readiness delay，因此 admission/backpressure 仍需在热路径处理当前负载。

## 控制、请求与数据状态表

| 状态 | 典型 owner | 更新路径 | 是否在每个 token 热路径 |
|---|---|---|---|
| endpoint membership | Discovery/Runtime | lease/EndpointSlice/register | 否，watch/cache 反馈 |
| KV locality index | KV router | worker KV events | 路由时读取；不传 payload |
| active projected load | Router/reservation | dispatch/completion/cancel | 路由时读取 |
| request queue/batch | vLLM/SGLang scheduler | 每 engine iteration | 是 |
| KV tensor bytes | engine GPU memory | attention write / NIXL transfer | 是 |
| replica desired state | Planner/Operator | metrics/reconcile | 否 |

## 源码入口

| 组件 | 固定 commit symbol | 阅读重点 |
|---|---|---|
| Frontend 组装 | [`frontend.async_main`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/frontend/main.py#L361) | Runtime、router、pre/post processor 与 HTTP frontend 初始化 |
| KV selection | [`SelectionCore.select`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/lib/kv-router/src/services/selection/core/run.rs#L67) | selection/admission/reservation 与 endpoint response |
| KV index lookup | [`KvIndexer.find_match_details`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/lib/kv-router/src/indexer/kv_indexer.rs#L727) | per-worker prefix match details |
| vLLM Decode/Aggregated | [`dynamo.vllm.handlers.DecodeWorkerHandler.generate`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/vllm/handlers.py#L3695) | request translation、engine stream、decode connector/cancel |
| vLLM Prefill | [`dynamo.vllm.handlers.PrefillWorkerHandler.generate`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/vllm/handlers.py#L4283) | prefill execution与 transfer metadata |
| SGLang Decode/Aggregated | [`dynamo.sglang.request_handlers.llm.DecodeWorkerHandler.generate`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py#L615) | native/async generation、bootstrap、token/text stream |
| SGLang Prefill | [`dynamo.sglang.request_handlers.llm.PrefillWorkerHandler.generate`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py#L90) | bootstrap info、prefill stream、cache-hit reporting |
| SGLang native bridge | [`native_generate_stream`](https://github.com/ai-dynamo/dynamo/blob/b208989fbe1cfbfde64d11334d8af4ff04fe1a99/components/src/dynamo/sglang/engine_generate.py#L123) | 调用 SGLang `TokenizerManager.generate_request` |

## 学习结论

1. Dynamo 的共同主干是 Frontend → routing → Runtime endpoint → backend handler；engine 内部执行仍需分别学习 vLLM/SGLang。
2. vLLM P/D 使用 prefill-first metadata injection；SGLang P/D 使用 decode-first bootstrap并发协调，不能用同一时序替代。
3. Request/event/discovery planes 处理消息和状态，NIXL 单独移动 KV payload。
4. KV-aware routing把 locality 当作成本折扣，同时纳入 projected load；KV index 不是 KV cache storage。
5. Planner/Operator 改变未来 capacity，不参与每个 token iteration，也不能消除扩缩启动延迟。
