---
title: llm-d 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D
tags: [analysis, llm-d, llm-serving, gateway-api, inferencepool, vllm, sglang, disaggregated-serving]
date: 2026-10-11
sources: [llm-d-architecture-analysis.md, llm-d-router-architecture-analysis.md]
related: ["[[llm-d]]", "[[llm-d-router]]", "[[llm-inference-request-lifecycle]]", "[[vllm-gpu-execution-path]]", "[[sglang-gpu-execution-path]]", "[[llm-gpu-kernel-execution-path]]", "[[gateway-api-inference-extension]]", "[[inference-routing]]", "[[disaggregated-serving]]"]
---

# llm-d 推理请求全链路：vLLM/SGLang 与 Aggregated/P-D

本页追踪 llm-d 的当前入口：Client 请求先到符合 Gateway API Inference Extension 的 Proxy，Proxy 通过 Envoy `ext_proc` 咨询 Endpoint Picker（EPP）；EPP 在 `InferencePool` candidates 上执行 request handling、admission 与 Filter→Score→Pick，并把选中的 endpoint 交回 Proxy。Aggregated 请求直接进入 vLLM/SGLang；P/D 请求由 Routing Proxy Sidecar / coordinator 编排 Prefill、Decode 与 KV handoff。

llm-d 是组件化 Kubernetes serving stack，不是新的 GPU engine。EPP 的 endpoint decision、KV index 与 K8s workload control 都在 engine 之外；KV tensors、continuous batching 和 CUDA kernels仍由 [[vllm-gpu-execution-path]] 或 [[sglang-gpu-execution-path]] 负责。

## 当前源码快照与结论范围

核验日期：2026-10-11。

- 文档/recipes 仓库：[llm-d/llm-d@`a9cf07a77a3016db21ae87134e5745b3a2d45ba6`](https://github.com/llm-d/llm-d/tree/a9cf07a77a3016db21ae87134e5745b3a2d45ba6)。
- Router/EPP/coordinator canonical 仓库：[llm-d/llm-d-router@`d870bcd132fc118b1433940a7842140275cc6cc9`](https://github.com/llm-d/llm-d-router/tree/d870bcd132fc118b1433940a7842140275cc6cc9)。GitHub 对历史名称请求会 redirect 到该 canonical repository。
- 本地 `/Users/zhenyu.jiang/llm-d` 与 `/Users/zhenyu.jiang/llm-d-router` 都早于固定 upstream，只用于定位。
- 当前架构已把 autoscaling 主线写成 EPP metrics → Prometheus/KEDA → HPA；[[llm-d-workload-variant-autoscaler]] 保持 deprecated 历史材料，不进入本页当前主链。

## Proxy / EPP / InferencePool 所有权

```text
[Client]
   │ OpenAI-compatible HTTP/SSE
   ▼
[Proxy: Envoy / Istio / agentgateway / Envoy AI Gateway / standalone proxy]
   │ ext_proc ProcessingRequest stream
   ▼
[EPP]
   Parser → FlowControl → DataProducers → Admitter → Scheduler
   Filter → Score → Pick over InferencePool endpoints
   │ selected endpoint address / dynamic metadata / header mutation
   ▼
[Proxy]
   │ upstream request
   ▼
[Model Server Pod]
   vLLM or SGLang → GPU
   │ response/SSE
   ▼
[Proxy] ── response chunks through EPP hooks when configured ──► Client

[Kubernetes control]
InferencePool/HTTPRoute/controllers ··► endpoint candidates/config, not token execution
```

职责边界：

- Proxy 建立客户端和 model server 的真实 upstream connection，并流式搬运 response。
- EPP 解析/调度/准入，返回 endpoint；它“扩展 proxy”，不重新实现完整 L7 proxy。
- `InferencePool` 声明 endpoint 集合、selector、target ports 与 EPP attachment。
- Model server 拥有 engine queue、KV memory 和 GPU state。

Standalone mode 将 Proxy 与 EPP 放在同一 pod，通过 localhost ext-proc；Gateway mode 使用 Gateway/HTTPRoute/InferencePool。两种模式的 request decision path 相同。

## 支持矩阵

| Engine | Serving 形态 | 状态 | 当前证据 |
|---|---|---|---|
| vLLM | Aggregated | documented | optimized-baseline guide、vLLM model-server architecture、InferencePool/EPP recipes |
| vLLM | P/D | documented | P/D architecture/operations、NixlConnector、Routing Proxy Sidecar/coordinator、CI workflows |
| SGLang | Aggregated | documented | SGLang model-server architecture、optimized-baseline SGLang workflow/guide |
| SGLang | P/D | documented | SGLang P/D architecture/operations、bootstrap coordinator、NIXL/Mooncake、CI workflow |

“documented”只覆盖基础请求链。特定硬件、TP ratio、connector、multimodal、LoRA 或 conditional disaggregation仍须按对应 guide/CI status 核验。

## vLLM × Aggregated

`llm-d.ai/role: prefill-decode` 或等价普通 model-server pods同时执行两阶段。EPP 使用 vLLM `/metrics`、request-local producers 和可选 KV index选择 pod，Proxy把请求直接转发到选中 endpoint。

```text
Client
 ──► Proxy
      ├─ext_proc──► EPP StreamingServer.Process
      │             ├── openai parser / request state
      │             ├── candidate endpoints from InferencePool
      │             ├── Filter→Score→Pick
      │             └── selected vLLM endpoint
      ◄──────────────┘
      ──► vLLM OpenAI endpoint
             ├── AsyncLLM / EngineCore
             ├── Scheduler / KVCacheManager
             ├── prefill + decode on same pool
             └── GPUModelRunner → token stream
Client ◄──── Proxy response/SSE ◄──────────────────────────
```

EPP 的 vLLM signals 包括 waiting/running requests、KV utilization 与可选 block-size/num-blocks。它们用于选点和 flow control，不修改 vLLM 的本轮 token budget。Engine 下钻见 [[vllm-gpu-execution-path]]。

## vLLM × P/D

Routing Proxy Sidecar/coordinator 接收请求并按 pipeline steps 调用 Gateway/EPP 的 Prefill profile 与 Decode profile。vLLM 路径是 context-first：先得到 Prefill response 中的 KV transfer parameters，再构造 Decode request。

```text
Client       Coordinator       Gateway/Proxy+EPP      Prefill vLLM       Decode vLLM
  │ request       │                    │                    │                  │
  ├──────────────►│ handleInference    │                    │                  │
  │               ├─Prefill step──────►│ profile=prefill    │                  │
  │               │                    ├─pick P endpoint───►│                  │
  │               │                    │                    ├─prefill GPU      │
  │               │◄─transfer params───┴────────────────────┤                  │
  │               ├─nixlKV.PrepareDecodeKVParams                               │
  │               ├─Decode reverse proxy───────────────────────────────────────►│
  │               │                    │ profile=decode/pick D                  ├─reserve/load
  │               │                    │                    │◄══ NIXL pull ═══►│
  │               │                    │                    │                  ├─decode GPU
  │◄──────────────┴──────────────────────────── streaming response ─────────────┤
```

vLLM Decode pod还可以在 conditional-disaggregation decision允许时本地 prefill；request 未携带 remote-prefill intent时，Decode worker按 aggregated path运行。若 connector policy 支持，在 remote KV load失败时可选择 recompute；这不是所有 connector 的统一保证。

## SGLang × Aggregated

SGLang pod必须标 `llm-d.ai/engine-type: sglang`，否则 EPP 会错误地按默认 vLLM metric names理解 telemetry。Aggregated 请求路径与 vLLM 相同，但 engine 内使用 RadixCache/ScheduleBatch。

```text
Client ──► Proxy ──ext_proc──► EPP
                  candidates from SGLang InferencePool
                  metrics: queue/running/token usage/page info
                  Filter→Score→Pick
             ◄── selected SGLang endpoint
       ──► SGLang HTTP server
             ├── TokenizerManager
             ├── Scheduler / RadixCache
             ├── ScheduleBatch extend + decode
             └── ModelRunner → Detokenizer → SSE
Client ◄── Proxy ◄────────────────────────────────────
```

Engine 细节见 [[sglang-gpu-execution-path]]。EPP 可利用 approximate/precise prefix producers，但 RadixCache 的 lock/refcount 与 KV slot ownership仍在 SGLang 进程。

## SGLang × P/D

SGLang Decode mode要求每个请求都有 bootstrap rendezvous fields，不能像 vLLM conditional path那样自行 fallback local prefill。因此 EPP 使用 always-disagg P/D decider；Routing Proxy Sidecar为两腿注入 `bootstrap_host`、`bootstrap_port`、`bootstrap_room`。

```text
Client       Coordinator sidecar       Gateway/EPP       Prefill SGLang     Decode SGLang
  │ request          │                      │                   │                  │
  ├─────────────────►│ generate room/fields │                   │                  │
  │                  ├─async Prefill request───────────────────►│                  │
  │                  │  context.WithoutCancel│ pick P           │                  │
  │                  ├─sync Decode request────────────────────────────────────────►│
  │                  │                      │ pick D             │ allocate KV pages│
  │                  │                      │                   ├══ push KV ══════►│
  │                  │                      │                   │ bootstrap/ready  │
  │                  │                      │                                      ├─decode GPU
  │◄─────────────────┴──────────────────────── streaming response ─────────────────┤
```

Prefill leg异步启动，Decode request立即进入并等待 bootstrap/KV；两者通过 engine out-of-band transfer协调。Connector可以是 NIXL 或 Mooncake；llm-d 当前架构重点是 NIXL。`sglangKV.PreparePrefillKVParams` 与 `PrepareDecodeKVParams` 负责 request fields，真正 KV movement 仍在 SGLang backend。

## EPP Filter → Score → Pick

`StreamingServer.Process` 收到 body后调用 parser，再交给 `Director.HandleRequest`。Director执行 model rewrite、request-header processors、candidate snapshot、data producers、screeners/admission，最后调用 `Scheduler.Schedule`。

```text
Incoming body/headers
  │ Parser → InferenceRequestBody
  ▼
Director.HandleRequest
  ├── resolve InferenceObjective / target model
  ├── candidate endpoints snapshot
  ├── RequestHeaderProcessors
  ├── DataProducers
  │     tokenizer · prefix matches · in-flight load · predicted latency
  ├── Screeners / FlowControl / Admitters
  └── Scheduler.Schedule
        ├── ProfileHandler.Pick profiles
        ├── each profile: Filters → Scorers → Picker
        └── ProfileHandler.ProcessResults
                    │
                    ▼
             SchedulingResult
             selected endpoint + score/context
```

Filters移除不 eligible endpoints；Scorers产生相对 preference；Picker做最终选择。Flow control/admission可能在没有安全容量/SLO headroom时先拒绝请求，不必等 engine queue爆满。

### Response hooks

```text
request selected ──► PreRequest hooks increment in-flight state
backend headers  ──► ResponseHeaderProcessor
SSE body chunks  ──► ResponseBodyProcessor / usage/latency
end/cancel/error  ──► release request state and metrics
```

是否能提取 output usage取决于 Proxy的 response-body processing mode 与 backend是否发送 usage。EPP在 response path观察/统计，不取代 Proxy的 socket streaming。

## InferencePool

`InferencePool` 是“哪些 endpoints属于这个 model-serving pool、端口是什么、哪个 EPP负责选择”的声明式边界，不是请求队列或 GPU memory pool。

```text
InferencePool spec
  selector: llm-d.ai/model = X
  targetPorts: serving / metrics / optional connector
  endpointPickerRef: EPP Service
          │ controller/watch
          ▼
matching Pods / EndpointSlice / endpoint metadata
  ├── pod A: role=prefill-decode, engine=vllm
  ├── pod B: role=prefill, engine=vllm
  ├── pod C: role=decode, engine=vllm
  └── pod D: role=prefill-decode, engine=sglang
          │
          ▼
EPP candidate snapshot per request/profile
```

`InferencePoolReconciler.Reconcile` 管理相关 Gateway/endpoint attachment状态；EPP data layer同时读取 Kubernetes endpoint metadata和server telemetry。候选出现不代表 model已加载完成，仍需 readiness与健康信号。

## P/D Coordinator

Coordinator 是明确的 HTTP/pipeline owner，而 EPP仍负责每个 phase的endpoint selection。

```text
Server.handleInference
  ├── parse/copy original request body + headers into RequestContext
  ├── pipeline steps
  │    ├── render/encode (when configured)
  │    ├── prefill
  │    │    ├── connector.PreparePrefillKVParams
  │    │    └── call gateway with phase/profile headers
  │    ├── conditional decode decision
  │    └── decode
  │         ├── connector.PrepareDecodeKVParams
  │         └── streaming ReverseProxy to gateway/decode endpoint
  └── write status/stream/error to client
```

`Server.handleInference` 不是 GPU coordinator：它协调 HTTP legs和metadata。`serveDecode` 用 streaming reverse proxy保持客户端 response；transport error在 headers前后具有不同可恢复性。

## KV Index 与 KV Payload

```text
KV INDEX / ROUTING SIGNAL
vLLM block events OR SGLang radix events
  ··► ZMQ/event ingestion ··► KV indexer
  ··► precise prefix producer/scorer ··► EPP endpoint choice
  contains: hashes/block identity/worker ownership, not tensor bytes

KV PAYLOAD
Prefill engine reserved KV VRAM
  ══ NIXL/Mooncake/connector transport ══► Decode reserved KV VRAM
  contains: per-layer K,V data in backend-specific layout

REQUEST METADATA
Coordinator ──► do_remote_{prefill,decode}, connector params, bootstrap fields
```

Precise index可以减少重复 prefill，但eventual consistency意味着selected endpoint必须由 engine校验。Pod restart后旧 agent/metadata可能失效；当前 vLLM NixlConnector operations guide明确列出 stale agent cache等限制。

## 流式返回

```text
ModelRunner.sample
  ──► engine token/text chunks
  ──► Model Server HTTP response
  ──► Proxy upstream stream
       ├─ext_proc response headers/body hooks ──► EPP metrics/state
       └─for P/D: Coordinator decode ReverseProxy
  ──► Client SSE/final JSON
```

Aggregated mode通常由shared Proxy直接返回；coordinator P/D path由Decode reverse proxy把chunks写给client。EPP response hook若启用body processing可统计TTFT/ITL/usage，但必须保持streaming，不能buffer整段输出后才交付。

## 失败与取消

| 故障点 | 当前边界 | 处理含义 |
|---|---|---|
| Parser/DataProducer失败 | EPP尚未选endpoint | immediate reject；无engine state |
| FlowControl/Admitter拒绝 | Proxy收到429/相应错误 | proactive overload，不进入GPU queue |
| 选中endpoint在转发前失效 | Proxy upstream连接失败 | 后续request会基于新EndpointSlice；当前request是否retry取决于proxy policy |
| Prefill leg失败 | coordinator pipeline停止或fallback policy执行 | Decode不能读取不存在的KV |
| KV index stale | EPP可能高估hit | engine connector校验；recompute/fail按backend policy |
| NIXL transfer失败 | vLLM可配置部分recompute policy；SGLang/其他路径分别核验 | 不能把所有backend写成透明fallback |
| SGLang client cancel | async Prefill使用独立context避免过早中断transfer | 必须另外清理Prefill/Decode lifecycle |
| Decode在headers前失败 | coordinator/proxy可返回error status | 尚未暴露stream prefix |
| Decode在headers/token后失败 | truncated/reset stream | 不可无痕换pod继续sampling |

```text
ext_proc stream / client context canceled
        │
        ├··► EPP termination hooks release in-flight/accounting
        ├──► Proxy closes upstream
        └──► Coordinator/backend-specific abort
                    │
                    └── engine frees request/KV only at safe lifecycle point
```

取消不是一个跨所有组件的transaction。特别是P/D有两个HTTP legs和一个out-of-band KV transfer；每个owner都必须有终止/超时/清理路径。

## KEDA / HPA / DisaggregatedSet 旁路

```text
REQUEST HOT PATH
Client ──► Proxy/EPP ──► Coordinator(optional) ──► engine pods ──► tokens
                  │ metrics: queue/saturation/token backlog
                  ·
                  ▼
Prometheus ◄·· EPP/model-server metrics
    │
    ▼
KEDA Prometheus scaler ──► HPA desired replicas
    │                                  │ scale subresource
    │                                  ▼
    │                       Deployment/LWS/DisaggregatedSet
    │                                  │ create/drain role pods/slices
    └·· feedback after readiness ·····► InferencePool endpoints / EPP
```

- KEDA/HPA根据metrics改变replicas，不选择单次request endpoint。
- `DisaggregatedSet` 管理prefill/decode等multi-role versioned slices；`LeaderWorkerSet` 管理多节点pod group。
- 新pod必须加载模型、注册connector并ready后才能进入candidate set。
- Scale-down必须考虑active streams、KV ownership和transfer state。
- Deprecated WVA不应作为新部署当前主线。

## vLLM 与 SGLang 的关键差异

| 维度 | vLLM P/D | SGLang P/D |
|---|---|---|
| Coordinator时序 | context-first，Prefill response提供Decode params | Prefill async + Decode immediate，bootstrap room rendezvous |
| Decode fallback | conditional path可在部分配置本地prefill | decode mode要求bootstrap fields，采用always-disagg decider |
| KV逻辑 | Paged blocks / NixlConnector | Radix/page pools + bootstrap transfer |
| EPP metrics默认 | vLLM metric names；无label时默认 | 必须标 `engine-type: sglang` 映射SGLang metrics |
| Engine下钻 | [[vllm-gpu-execution-path]] | [[sglang-gpu-execution-path]] |

## 源码入口

| 层 | 固定 commit symbol | 阅读重点 |
|---|---|---|
| ext_proc stream | [`StreamingServer.Process`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/epp/handlers/server.go#L311) | request/response phases、eviction/cancel/cleanup |
| request lifecycle | [`Director.HandleRequest`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/epp/requestcontrol/director.go#L199) | candidates、producers、admission、scheduler、prepare request |
| scheduling | [`Scheduler.Schedule`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/epp/scheduling/scheduler.go#L62) | profile selection、Filter/Score/Pick results |
| pool reconcile | [`InferencePoolReconciler.Reconcile`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/epp/controller/inferencepool_reconciler.go#L45) | InferencePool/Gateway attachment control loop |
| coordinator HTTP | [`Server.handleInference`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/coordinator/server/handlers.go#L49) | request context、pipeline、stream/error response |
| decode proxy | [`serveDecode`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/coordinator/steps/decode_proxy.go#L160) | streaming reverse proxy 与 headers后错误边界 |
| SGLang fields | [`sglangKV.PreparePrefillKVParams`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/coordinator/connectors/kv/sglang.go#L87) | bootstrap/P-D control fields |
| vLLM/NIXL fields | [`nixlKV.PrepareDecodeKVParams`](https://github.com/llm-d/llm-d-router/blob/d870bcd132fc118b1433940a7842140275cc6cc9/pkg/coordinator/connectors/kv/nixl.go#L50) | Prefill response → Decode connector params |

## 学习结论

1. Proxy承载HTTP/SSE；EPP只做解析、准入与endpoint decision，不能把二者画成同一个进程职责。
2. InferencePool是Kubernetes endpoint集合，不是engine queue或KV pool。
3. Aggregated路径在EPP选点后直接进入engine；P/D路径增加coordinator的两腿HTTP编排和KV connector metadata。
4. vLLM与SGLang P/D时序不同：context-first response merge对比async bootstrap rendezvous。
5. KV index通过events影响EPP score，KV payload通过NIXL/Mooncake在engine内存间移动。
6. KEDA/HPA/DisaggregatedSet是异步capacity loop，不在每个token热路径上。
