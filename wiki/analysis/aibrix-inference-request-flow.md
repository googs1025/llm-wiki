---
title: AIBrix 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D
tags: [analysis, aibrix, llm-serving, inference-routing, vllm, sglang, disaggregated-serving]
date: 2026-10-11
sources: [aibrix-architecture-analysis.md]
related: ["[[aibrix]]", "[[llm-inference-request-lifecycle]]", "[[vllm-gpu-execution-path]]", "[[sglang-gpu-execution-path]]", "[[llm-gpu-kernel-execution-path]]", "[[inference-routing]]", "[[disaggregated-serving]]"]
---

# AIBrix 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D

本页从 AIBrix Gateway 的 Envoy `ext_proc` 入口开始，分别追踪 vLLM/SGLang 的标准 aggregated 请求与 Prefill/Decode 分离请求，再在 engine handoff 处连接 [[vllm-gpu-execution-path]] 或 [[sglang-gpu-execution-path]]。

AIBrix 的关键边界是：Envoy 承载客户端主 HTTP/SSE 数据流，Gateway plugin 在 `ext_proc` stream 上解析/修改请求并选择 pod；P/D router 还会主动发起 Prefill leg，但 KV payload 由 engine/transfer backend 在 worker 之间移动，Gateway 不搬运 KV tensors。

## 当前源码快照与结论范围

核验日期：2026-10-11。

- 官方仓库：[vllm-project/aibrix@`1d6472b83d2b70ce873dbd953add835e1ccc6a71`](https://github.com/vllm-project/aibrix/tree/1d6472b83d2b70ce873dbd953add835e1ccc6a71)。
- 当前 README 的最新正式 release 为 v0.7.0，同时 quick-start 指向 v0.8.0-rc.1；本页固定到 default-branch commit，不把它称作稳定 release。
- 官方 [`pd-disaggregation.rst`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/docs/source/features/pd-disaggregation.rst) 明确列出 vLLM、SGLang 与 TensorRT-LLM，并同时描述 standard inference pods 与 P/D pods。
- 既有 [[src-aibrix-architecture]] 是历史 raw-backed 摘要；本页的 current observations 独立标注 commit，不反向改写历史来源。

## 支持矩阵

状态含义沿用 [[llm-inference-request-lifecycle]]：`documented` 是官方当前文档明确描述；`tested` 表示仓库存在实现/测试或镜像入口，但缺少同等清晰的端到端 standard deployment 文档。

| Engine | Serving 形态 | 状态 | 当前证据与限制 |
|---|---|---|---|
| vLLM | Aggregated | documented | PD 文档将 standard inference pod 定义为单进程完整 lifecycle；默认 engine 是 vLLM，并给出 combined pod 配置 |
| vLLM | P/D | documented | PD 文档、`samples/disaggregation/vllm/`、`VLLMHandler` 与 connector transfer agent |
| SGLang | Aggregated | tested | Gateway 普通 OpenAI forwarding 不依赖 engine-specific P/D handler；仓库含 SGLang image/endpoints tests，但固定 commit 未找到与 vLLM combined pod 同等完整的 standard SGLang gateway recipe |
| SGLang | P/D | documented | PD 文档、`samples/disaggregation/sglang/`、`SGLangHandler` bootstrap、watchdog 与测试 |

SGLang aggregated 的 `tested` 不等于不支持：主数据面是普通 OpenAI-compatible upstream，代码存在 SGLang runtime/endpoint 测试；状态较低只表示“当前固定 commit 的正式文档证据不如 SGLang P/D 完整”。

## 平台所有权总图

```text
[Client]
   │ HTTP / SSE
   ▼
[Envoy Gateway data plane]
   │ ext_proc bidirectional ProcessingRequest/Response
   ▼
[AIBrix Gateway plugin]
   RequestHeaders → RequestBody → route/pick → response accounting
   │                         │
   │ selected target headers │ P/D only: Prefill HTTP leg
   ▼                         ▼
[Envoy upstream routing]   [Prefill pod]
   │                         └══ KV via engine transfer backend ══╗
   ▼                                                            ║
[Aggregated pod OR Decode pod] ◄═════════════════════════════════╝
   │ vLLM/SGLang engine → GPU
   ▼
[Envoy response path] ⇄ [Gateway plugin response headers/body accounting]
   │
   ▼
[Client token stream]

[Control plane]
controllers · model/adapter metadata · autoscaler · runtime · health ··► pod/config/cache
```

Gateway plugin 不是普通 reverse proxy application server。`Server.Process` 处理 Envoy external processing stream；它返回 header/body mutations、route-cache 清理和 immediate response。真正的客户端 upstream connection 仍由 Envoy 管理。P/D prefill 是例外：router 的 PrefillExecutor 从 plugin 发起额外 HTTP leg。

## 请求头、请求体与选点

```text
Envoy ext_proc stream
  │
  ├── RequestHeaders
  │     └── Server.HandleRequestHeaders
  │          auth/user/quota context · path/header capture · route rematch
  │
  ├── RequestBody
  │     └── Server.HandleRequestBody
  │          parse model/messages/stream/prefix text
  │          validate model availability / ready pods
  │          resolve profile + routing-strategy
  │          RouterManager.Validate(strategy)
  │          selectTargetPod → router.Route
  │          set target pod/IP/request-id/body mutation headers
  │          ClearRouteCache so Envoy rematches upstream
  │
  ├── ResponseHeaders
  │     └── diagnostics / first response phase / upstream status
  │
  └── ResponseBody chunks
        └── streaming usage/TTFT accounting, error normalization, TPM
```

`Server.HandleRequestBody` 在当前代码中承担关键分叉：如果 strategy 未设置，可让 Kubernetes HTTPRoute/Service 决定；否则收集 model pods 并调用 selected router。Router 返回的是目标地址和 mutation state，Envoy 再将客户端请求转发到目标 engine pod。

## vLLM × Aggregated

前置条件：选择普通 routing strategy，或 PD strategy 通过 prompt bucket/availability 选择 `combined: true` 的 standard vLLM pod。Prefill 与 Decode 都由同一个 vLLM instance 完成，不发生跨 pod KV transfer。

```text
Client
  ──► Envoy Gateway
        ├─ext_proc──► AIBrix Server.Process
        │             ├── headers/body parse
        │             ├── model/profile/strategy
        │             └── choose combined vLLM pod
        │                       │ target pod IP/header mutations
        ◄───────────────────────┘
        │ route rematch
        ──► vLLM OpenAI endpoint
              ──► AsyncLLM / EngineCore / Scheduler
              ──► KVCacheManager / GPUModelRunner
              ──► prefill + repeated decode on same worker/pool
              ──► sampled token/SSE
        ◄─────────────────────────────────────────────
  ◄── SSE via Envoy; response chunks observed by ext_proc accounting
```

Engine handoff 之后的完整源码链见 [[vllm-gpu-execution-path]]。AIBrix router 看到 pod readiness、load、routing metrics 或 prefix index，但不修改 vLLM 本轮 `SchedulerOutput`、block table 或 CUDA Graph。

### Combined fallback

在 PD routing 加 prompt-length bucketing 时，combined vLLM pod 可作为另一条 documented path：没有匹配 bucket、roleset 缺少一侧，或 load policy 选择 standard capacity 时，`filterPrefillDecodePods` 返回 combined pod；`pdRouter.Route` 不发 prefill HTTP leg，Envoy 直接把原始完整请求送到该 pod。

## vLLM × P/D

vLLM handler 是 context-first 同步 handler（`IsAsync() == false`）。Gateway 先完成 Prefill HTTP leg并解析返回的 transfer parameters，再让 Envoy 把 Decode leg 送到选中的 decode pod。

```text
Client          Envoy/ext_proc       AIBrix pdRouter       Prefill vLLM       Decode vLLM
  │ request           │                     │                    │                  │
  ├──────────────────►│ RequestBody         │                    │                  │
  │                   ├────────────────────►│ Route              │                  │
  │                   │                     ├─select P/D pair    │                  │
  │                   │                     ├─PreparePayload     │                  │
  │                   │                     ├──HTTP prefill─────►│                  │
  │                   │                     │                    ├─prefill GPU      │
  │                   │                     │                    ├─export KV ══════►│
  │                   │                     │◄─transfer params───┤                  │
  │                   │                     ├─VLLMHandler.MergePrefillResponse      │
  │                   │◄─decode target/body─┤                                       │
  │                   ├──────────────────────────────────────────decode request─────►│
  │                   │                                                             ├─wait/load KV
  │                   │                                                             ├─decode GPU
  │◄──────────────────┴──────────────────────────────SSE tokens──────────────────────┤
```

关键源码契约：

- `pdRouter.filterPrefillDecodePods` 将 ready pods 分成 rolesets/roles/combined buckets，按 prompt range、load、prefix/token policies 选择 aligned pair。
- `VLLMHandler.AugmentPrefillRequest` 通过 transfer agent 向 Prefill body 加 connector 控制字段。
- Prefill response 带回 connector/disaggregation metadata；`VLLMHandler.MergePrefillResponse` 写入 routing context/decode request。
- Gateway 只处理 metadata；KV payload 由 SHFS/NIXL/Mooncake 等选定 transfer agent 与 vLLM connector 在 workers 之间移动。
- Decode vLLM 进入 [[vllm-gpu-execution-path#P/D Connector 边界|vLLM connector → scheduler/runner]]，完成 load/readiness 后才 decode。

## SGLang × Aggregated

状态为 `tested`。AIBrix 的普通 gateway route 对 OpenAI-compatible SGLang endpoint 不需要 P/D engine handler；选点后 Envoy 将原始请求送到 standard SGLang server，后者本地完成 extend/prefill 与 decode。

```text
Client ──► Envoy ──ext_proc──► AIBrix Gateway plugin
                   │                 │ parse/model/policy
                   │                 └── choose ready SGLang pod
                   ◄── target IP / route rematch
                   │
                   └──► standard SGLang HTTP server
                           ├── TokenizerManager
                           ├── Scheduler / RadixCache / ScheduleBatch
                           ├── ModelRunner → GPU
                           ├── extend/prefill then decode locally
                           └── Detokenizer → token stream
Client ◄────────────────────────────────────────────── SSE via Envoy
```

证据限制：固定 commit 有 `build/container/Dockerfile.sglang`、development SGLang endpoints tests 与 engine-aware response handling；Gateway 的普通 target forwarding 本身是 engine-neutral。但没有找到与 `samples/disaggregation/sglang/` 同等级的 dedicated aggregated gateway sample，因此不提升为 `documented`。

Engine 内部见 [[sglang-gpu-execution-path]]。

## SGLang × P/D

SGLang 使用 bootstrap handshake。`SGLangHandler.AugmentPrefillRequest` 从 decode pod annotation/identity取得 bootstrap host/port/room，为 decode body 与 prefill body生成共同 request identity；handler 是 async，因此 Prefill leg 与 Envoy→Decode leg 的协调不同于 vLLM context-first。

```text
Client        Envoy/ext_proc       AIBrix pdRouter       Prefill SGLang      Decode SGLang
  │ request         │                    │                     │                  │
  ├────────────────►│                    │                     │                  │
  │                 ├───────────────────►│ select roleset pair │                  │
  │                 │                    ├─SGLangHandler.AugmentPrefillRequest     │
  │                 │                    │  shared rid + bootstrap host/port/room  │
  │                 │                    ├─async prefill HTTP─►│                  │
  │                 │◄─decode body/target┤                     │                  │
  │                 ├──────────────────────────────────────────decode request────►│
  │                 │                    │                     ├══ bootstrap/KV ═►│
  │                 │                    │                     │ prefill returns   │
  │                 │                    │◄─prefill completion─┤ after handoff      │
  │                 │                    │                                        ├─decode/sample
  │◄────────────────┴──────────────────────────────SSE token stream────────────────┤
```

`SGLangHandler.MergePrefillResponse` 是 no-op，因为必要 coordination 已由 bootstrap fields/handshake 完成；这与 vLLM“先解析 Prefill response，再构造 Decode parameters”不同。SGLang engine 内的接收、KV mapping 与 readiness 见 [[sglang-gpu-execution-path#P/D Bootstrap 边界|SGLang P/D Bootstrap 边界]]。

### 为什么需要 Decode watchdog

官方文档说明 SGLang Prefill request 只在 Decode 已接管 KV 后返回。此后如果 Decode scheduler crash/hang，Prefill 已成功却可能没有首 token。Gateway 因此跟踪：

- streaming 首 body chunk timeout；
- streaming chunks 之间的 idle timeout；
- 可选 non-streaming response timeout；
- timeout 时向 Decode `/abort_request` 清理 request。

响应头已发送后不能改成新的 HTTP error body；Gateway 会截断 stream 并记录错误，因此客户端可能看到 `200` 加不完整 body/stream error。

## KV Metadata / KV Payload / Token Stream

三条路径必须分别观察：

```text
CONTROL / METADATA
Gateway ──► select {prefillPod, decodePod, roleset, engine}
Gateway ──► request id / connector or bootstrap fields ──► Prefill + Decode
Prefill ──► readiness/transfer params/completion ──► Gateway or Decode

KV PAYLOAD
Prefill GPU/cache ══ SHFS/NIXL/Mooncake/engine transport ══► Decode GPU/cache
Gateway plugin does not read/copy K,V tensor bytes

TOKEN STREAM
Decode or Combined engine ──► Envoy upstream response ──► Client
                                  │
                                  └── ext_proc observes headers/body chunks
                                      for watchdog/usage/TTFT/accounting
```

Prefix cache index 属于 metadata：它帮助选择 Prefill pod，但命中并不代表 Decode 已拥有相同 KV。Transport success 也不代表 sampling state 可迁移；P/D 通常把 prompt KV 交给一个新的 decode lifecycle。

## 路由打分与并发记账

```text
ready pods
  │ filter model/readiness/role/roleset/prompt bucket
  ▼
prefill candidates                    decode candidates
  ├─ prefix overlap                   ├─ request/load balance
  ├─ least requests                   ├─ throughput/drain rate
  ├─ token load                       ├─ token load
  └─ conductor/hybrid                 └─ policy score
          │                                  │
          └──────── final roleset score ─────┘
                             │
                             ▼
                  atomically select + register
                  PrefillRequestTracker
                  PendingDecodeTracker
                  TokenLoadTracker charges
                             │ completion/failure
                             └··► release charges
```

选择与 register 在共享锁下协调，避免两个并发请求都读取同一旧 load 后同时选中一个 pod。Metrics/prefix index 仍可能比真实 engine queue 滞后；tracker 的 provisional charge 用来缩小这个窗口，不提供跨 gateway 的强一致 transaction。

## 失败与取消

| 故障点 | AIBrix 可观察行为 | Engine/客户端边界 |
|---|---|---|
| 请求/controlled field 非法 | 在选 pod、发 Prefill 前返回 4xx | 没有 GPU/KV 副作用 |
| 没有 ready model pod | routing 5xx/availability error | 可由上游 retry policy 处理，仍需考虑请求幂等性 |
| P/D roleset 不完整 | 有 compatible combined pod 时 fallback，否则失败 | 不会把 Prefill 与错误 Decode roleset 拼接 |
| Prefill HTTP/transfer setup 失败 | fail-fast；清理 trackers/charges | Decode 若已启动需 abort/reset |
| SGLang Decode 首 token/idle 超时 | watchdog abort decode；未发 header 可 504，已发 header 则截断 stream | 已输出 token 后不是透明 retry |
| KV metadata 与实际 payload 不一致 | Decode connector/load 应失败或 recompute，取决于 engine contract | Gateway prefix signal不能证明 device KV 有效 |
| Client disconnect | ext_proc context cancel、finish request bookkeeping、下游取消/abort | 已排入 GPU 的 batch 可能仍短暂完成 |
| Worker 在流中途消失 | Envoy/upstream stream error；metrics finalization | 采样状态/KV 若不可恢复，只能让客户端看到失败 |

```text
request state
  ──► selected
  ──► prefill started (P/D)
  ──► decode/combined upstream started
  ──► headers sent?
  ──► first token sent?
  ──► completed

failure before headers ──► immediate HTTP error may still be possible
failure after headers  ──► reset/truncate stream + abort cleanup
failure after tokens   ──► cannot silently replay without duplicate/divergent text risk
```

## 控制面旁路

```text
HOT REQUEST PATH
Envoy ⇄ Gateway plugin ──► selected pod ──► engine/GPU ──► response
              ▲
              │ reads cached state
              │
CONTROL / FEEDBACK
Kubernetes controllers · Runtime · LoRA controller · RayClusterFleet
Autoscaler · GPU optimizer · accelerator diagnosis
      │ create/update pods, adapters, readiness, policies
      └··► informer/cache/metrics/prefix events ··► Gateway routing state
```

Autoscaler/controller 的 reconcile 不会在每个 decode token 前运行。它们改变 future capacity 与 ready candidates；已经选中的 request 仍依赖 Envoy/upstream connection、engine state 和 connector lifecycle。Scale-down 必须 drain 或容忍请求失败，不能仅凭 Kubernetes Pod deletion 自动迁移生成状态。

## 源码入口

| 组件 | 固定 commit symbol | 阅读重点 |
|---|---|---|
| ext_proc 主循环 | [`Server.Process`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/gateway.go#L380) | stream lifecycle、cancel、watchdog、统一 bookkeeping |
| headers | [`Server.HandleRequestHeaders`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/gateway_req_headers.go#L61) | request context、auth/rate-limit、route rematch |
| body/route | [`Server.HandleRequestBody`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/gateway_req_body.go#L43) | parse、profile/strategy、ready pods、target mutations |
| PD route | [`pdRouter.Route`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/algorithms/pd_disaggregation.go#L504) | validate handler、select pair、prefill dispatch、decode target |
| pair selection | [`pdRouter.filterPrefillDecodePods`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/algorithms/pd_disaggregation.go#L702) | roleset/bucket/load/prefix scoring 与 atomic registration |
| vLLM merge | [`VLLMHandler.MergePrefillResponse`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/algorithms/pd/engine/vllm.go#L72) | Prefill response → Decode transfer metadata |
| SGLang bootstrap | [`SGLangHandler.AugmentPrefillRequest`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/algorithms/pd/engine/sglang.go#L58) | shared rid、bootstrap host/port/room、async handoff |
| Prefill executor | [`PrefillExecutor.Execute`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/algorithms/pd/prefill/executor.go#L39) | sync/async engine handler dispatch 与 tracker cleanup |
| response stream | [`Server.HandleResponseBody`](https://github.com/vllm-project/aibrix/blob/1d6472b83d2b70ce873dbd953add835e1ccc6a71/pkg/plugins/gateway/gateway_rsp_body.go#L252) | SSE usage、TTFT/TPM、upstream errors |

## 学习结论

1. Aggregated 与 P/D 都经过同一个 Envoy/ext_proc 入口，但 P/D 额外产生 Prefill HTTP leg与 KV transfer lifecycle。
2. AIBrix 选择 engine pods、改写/补充 request metadata；engine 自己拥有 scheduler、KV blocks/pages 和 GPU kernels。
3. vLLM P/D 是 context-first response-merge 契约；SGLang P/D 是 async bootstrap/handoff 契约，不能共用一张假想时序图。
4. Gateway 看见 prefix/load 信号，不等于 Gateway 持有 KV；KV payload 不经过 Go router memory。
5. 已发送 response headers/token 后的故障必须按流语义处理，不能包装成无痕 retry。
