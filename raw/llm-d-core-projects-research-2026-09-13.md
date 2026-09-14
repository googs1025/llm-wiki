# llm-d 核心项目群架构再调研

> 调研日期：2026-09-13
> 
> 上游仓库：
> - https://github.com/llm-d/llm-d @ `965a5080b354187c9f466fbabe4777954348b3f7`
> - https://github.com/llm-d/llm-d-router @ `38cb83316ea49840e10d3d180e67b08beca1d1ca`
> - https://github.com/llm-d/llm-d-kv-cache @ `8cf43067afb7fc9fefafc1b64de063c769f2c90f`
> - https://github.com/llm-d/llm-d-autoscaling @ `0a926fab08ee74942f961cd5e7835ec2ab651ad4`
> - https://github.com/llm-d/llm-d-batch-gateway @ `aaeeca80551027141d4cb61e7d0d5bd7dc134892`
> - https://github.com/llm-d/llm-d-benchmark @ `2abdb608c4e64fccbabfe171298a88471e2cadc4`
> - https://github.com/llm-d/llm-d-inference-sim @ `1d2b5207a19fef6ac48699a915489aef24d92b6c`
> - https://github.com/llm-d-incubation/llm-d-planner @ `89edc1007c4edf2054c59c776ad6b438332ed02c`

## 一句话定位

`llm-d` 不是推理引擎，而是位于 vLLM/SGLang/TensorRT-LLM 之上的 Kubernetes-native 分布式推理控制与优化栈。它把 LLM 请求路由、KV cache locality、Prefill/Decode 解耦、SLO-aware autoscaling、Batch 任务和可复现实验组合成一条 serving platform；`llm-d-planner` 则把业务需求、GPU 选择和部署配置连接到这条平台链路的上游。

## 总体架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                             Client / Workload                                │
│ OpenAI / vLLM / Anthropic-compatible requests · online · batch · agentic     │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │ HTTPRoute / API / queue
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway / Proxy                                                             │
│ Envoy · Istio · AgentGateway · Envoy AI Gateway · cloud Gateway API          │
└────────────────────────────────────┬─────────────────────────────────────────┘
                                     │ ext-proc / Endpoint Picker Protocol
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ llm-d Router / EPP                                                         │
│ request parser → flow control → Filter → Score → Pick                       │
│ load · queue · KV locality · latency prediction · priority · LoRA           │
└───────────────┬──────────────────────┬──────────────────────┬────────────────┘
                │                      │                      │
                ▼                      ▼                      ▼
       InferencePool             KV indexer              WVA / HPA / KEDA
       Pod discovery              ZMQ KV events            desired replicas
                │                      │                      │
                └──────────────┬───────┴──────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Model Server Variants                                                        │
│ vLLM · SGLang · TensorRT-LLM · aggregated · Prefill · Decode · batch         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ OpenAI API / metrics / KV events
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Accelerator + Runtime                                                        │
│ GPU / TPU / HPU / NPU · TP / DP / EP · KV HBM → CPU → SSD/shared storage    │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Batch Gateway        │───▶│ Async Processor      │───▶│ Router / Model Pool  │
│ files/jobs/status    │    │ queue + flow gate    │    │ online serving path  │
└──────────────────────┘    └──────────────────────┘    └─────────────────────┘

┌──────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Benchmark             │───▶│ Inference Simulator  │───▶│ Prism / reports     │
│ render/deploy/run     │    │ no GPU, vLLM-like    │    │ compare experiments │
└──────────────────────┘    └──────────────────────┘    └─────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│ llm-d Planner: intent → traffic/SLO → capacity → recommendation → YAML       │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 项目一：llm-d 主仓库

### 作用与业务问题

主仓库是文档、部署 recipe、API 约定和架构组合层。它解决的不是“如何写一个模型 server”，而是生产环境中模型 server 之间的系统问题：请求不能只按 round-robin 分发，长上下文会放大 KV 重算，P/D 阶段互相干扰，异构 GPU 和多种 serving variant 很难扩缩，batch 任务也不应挤占在线流量。

### 方法与核心抽象

- `Router / EPP`：以 LLM 状态为信号做 endpoint picking。
- `InferencePool`：用 label selector 组织同一模型的 model-server Pods，是 LLM 优化版 Service。
- `Variant`：用 Pod labels 表达同一模型的硬件、TP、角色、成本或性能差异。
- `Model Server`：实际运行 vLLM、SGLang 或 TensorRT-LLM 的执行层。
- Well-lit paths：把 prefix-aware routing、P/D、wide-EP、KV offload、autoscaling、batch 等能力组合成可部署 recipe。

### 业务集成

Gateway API 的 `HTTPRoute → InferencePool` 进入 Proxy，Proxy 通过 `ext-proc` 调 EPP；EPP 根据 Kubernetes endpoint、模型 server metrics、KV 事件和配置 profile 选出 Pod。模型 server 通过 OpenAI API 提供推理，通过 Prometheus 提供 queue/running/KV 指标，通过 KV events 提供精确缓存状态。

### 关键数据流

```
HTTPRoute → Gateway/Proxy
          → ext-proc 请求
          → EPP 解析 request
          → Flow Control admission / priority / fairness
          → Filter 候选端点
          → Score load / KV / latency / LoRA
          → Pick endpoint
          → Proxy 转发到 Model Server
          → vLLM/SGLang 执行 prefill + decode
          → metrics / KV events 反哺 EPP
```

## 项目二：llm-d-router

### 作用与业务问题

`llm-d-router` 是智能入口层。它把网络代理的数据面和 LLM 专用决策面拆开，避免重新实现 TLS、连接管理和通用 L7 proxy，同时解决模型 server endpoint 选择、排队、公平性、优先级和 P/D 编排问题。

### 架构图

```
Client
  │
  ▼
┌──────────────┐  ext-proc   ┌────────────────────────────────────────┐
│ Envoy /      │────────────▶│ EPP                                    │
│ Gateway API  │◀────────────│ parser → flow control → scheduler      │
└──────┬───────┘ endpoint     │ Filter → Score → Pick                  │
       │                       └───────────────┬────────────────────────┘
       │                                       │ consult
       ▼                                       ▼
┌──────────────┐                     ┌───────────────────────────────────┐
│ InferencePool│◀── discovery ───────│ Data Layer                         │
│ model Pods   │                     │ K8s Pods + metrics + KV + sidecars │
└──────┬───────┘                     └───────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ vLLM / SGLang / TensorRT-LLM · aggregated / P-D / E-P-D variants          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 核心方法

- `Filter → Score → Pick` 插件流水线：先排除不可用端点，再计算 load/KV/latency 等分数，最后按策略选择。
- EPP Flow Control：按 priority band 排队，支持 admission、saturation detector、fairness policy 和 ordering policy，避免 noisy neighbor。
- `InferenceObjective`：表达请求级调度目标、优先级和性能要求。
- `InferenceModelRewrite`：支持模型名重写，服务 A/B、canary 和多模型流量管理。
- Standalone mode：自带 Envoy sidecar 或独立 Service。
- Gateway mode：EPP 作为 InferencePool 后端，复用 Istio、AgentGateway、Envoy AI Gateway 或云 Gateway。
- Disaggregation sidecar：协调 prefill/decode worker 和 KV transfer。

### 解决的问题与集成

它适合需要 endpoint-level LLM routing 的平台，而不是 provider auth/policy 型通用 AI gateway。集成入口是 Envoy `ext-proc`、Gateway API `HTTPRoute/InferencePool`、Prometheus metrics、Kubernetes Pod discovery 和可选 consultant sidecars（KV indexer、latency predictor、tokenizer）。

## 项目三：llm-d-kv-cache

### 作用与业务问题

这是一个 Go library，不是独立的缓存服务。它让 EPP 维护“哪个 model server Pod 拥有哪些 KV blocks”的近实时全局视图，并按请求 prefix 的最长连续命中长度对候选 Pod 打分，解决多轮对话、长上下文、agentic loop 中重复 prefill 的浪费。

### 架构图

```
┌──────────────────────── Model Servers ────────────────────────┐
│ vLLM / SGLang                                                 │
│ BlockStored · BlockRemoved · AllBlocksCleared                 │
└──────────────────────────┬────────────────────────────────────┘
                           │ msgpack over ZMQ
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ kvevents.Pool                                                  │
│ shard by pod → preserve per-pod order → EngineAdapter          │
└──────────────────────────┬─────────────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────────────┐
│ kvblock.Index                                                   │
│ requestKey → pod entries · engineKey → requestKey · LRU/Redis  │
└──────────────────────────┬─────────────────────────────────────┘
                           ▲
                           │ lookup / score
┌──────────────────────────┴─────────────────────────────────────┐
│ EPP host process                                                │
│ external tokenizer → TokenProcessor → longest-prefix Scorer    │
│ GPU/CPU tier weights · speculative entries · multimodal/LoRA    │
└──────────────────────────┬─────────────────────────────────────┘
                           │ normalized KV locality score
                           ▼
                    Filter → Score → Pick
```

### 核心方法

事件适配器把 vLLM/SGLang wire format 统一成 domain events；TokenProcessor 重建与 engine 一致的 chained block keys；Scorer 只计最长连续 prefix，避免把孤立的后续 block 当成可复用缓存；GPU/CPU tier 可使用不同权重；speculative indexing 用短 TTL 填补“已经路由但 BlockStored 尚未到达”的窗口。

### 集成边界

新集成应在 host 或 sidecar 外部 tokenize 后调用 `ScoreTokens`；库内 tokenizer pool 已是兼容路径。索引可使用 in-memory、Redis/Valkey 等后端。它解决“路由看见缓存在哪里”，不负责模型执行，也不等同于 vLLM KV offloading 或跨节点 KV transfer。

## 项目四：llm-d-autoscaling

### 作用与业务问题

WVA 是面向分布式 inference workload 的 variant optimization autoscaler。它解决单一 HPA 只能看单 Deployment 指标的问题：同一模型可能同时存在不同 GPU、TP、batch、P/D 角色和成本档位，需要在有限 accelerator inventory 下做全局 replica allocation。

### 架构图

```
                 Prometheus / EPP metrics
          queue · running · KV · latency · pending Pods
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│ WVA Controller                                                │
│ workload/variant discovery → capacity model → optimizer       │
│ supply constraints · energy/cost · latency/throughput SLO      │
└──────────────────────────────┬───────────────────────────────┘
                               │ wva_desired_replicas
                               ▼
┌──────────────┐      metrics      ┌──────────────┐      scale subresource
│ Prometheus   │─────────────────▶│ HPA / KEDA   │───────────────────────▶│
└──────────────┘                  └──────────────┘                         │
                                                                          ▼
                         Model-server Deployments / variants
```

### 核心方法与集成

WVA 不直接替代 HPA/KEDA，而是计算 desired replica 指标，由 HPA/KEDA 执行 scale subresource。它消费 Prometheus、EPP queue/KV 指标、GPU inventory 和 InferencePool/variant 信息；可以处理 heterogeneous hardware、P/D role 和 pending Pods。简单同构服务可用 KEDA + EPP metrics；多 variant、资源受限或强 SLO 场景再用 WVA。

当前仓库的 V2 saturation analyzer 已成为默认，采用 token/capacity 信号而不是旧的 percentage/spare-capacity 规则；升级时要重新检查阈值、dashboard 和告警。

## 项目五：llm-d-batch-gateway

### 作用与业务问题

Batch Gateway 是 backend-agnostic 的 OpenAI-compatible Batch API 和处理引擎。它把大量低优先级、可延迟的 JSONL 推理从在线请求中分离出来，提供 file/job lifecycle、进度、取消、重试、归档和可恢复执行。

### 架构图

```
Client
  │ POST /v1/files + POST /v1/batches
  ▼
┌──────────────────────┐      PostgreSQL metadata
│ Batch API Server     │──────────────────────────┐
│ validation / status  │                          │
└──────────┬───────────┘                          ▼
           │ enqueue                       ┌──────────────┐
           ▼                              │ Redis/Valkey  │
┌──────────────────────┐                   │ queue/status │
│ Processor workers    │◀──────────────────└──────────────┘
│ fetch JSONL → invoke │
│ backend → write output│
└──────────┬───────────┘
           │ OpenAI-compatible requests
           ▼
┌──────────────────────┐      object storage / FS
│ Router or backend     │──────────────────────────▶ output JSONL
└──────────────────────┘
           ▲
           └──────────── GC / retry / reconciliation
```

### 方法与集成

API server、processor、PostgreSQL、Redis/Valkey 和 file/object store 解耦；processor 可直接调用下游 serving backend，也可以和 Async Processor 组合获得 metric-based flow control。核心边界是 batch job lifecycle，不是在线 endpoint picking。适合离线评测、数据生成、批量摘要和 embedding；不适合低延迟 interactive path。

## 项目六：llm-d-benchmark

### 作用与业务问题

Benchmark 是 Kubernetes 实验生命周期编排器，不是单一压测器。它解决“同一套 serving stack 如何在不同集群、硬件、路由 profile 和 workload 下可复现比较”的问题。

### 架构图

```
Scenario YAML + cluster config + CLI overrides
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────┐
│ Plan phase                                                       │
│ Pydantic validation → config merge → Jinja render → workspace    │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌─────────────┐
│ standup      │ → │ smoketest    │ → │ run/experiment│ →│ teardown    │
│ infra+stack  │   │ health/API   │   │ harness+DoE  │   │ cleanup     │
└──────────────┘   └──────────────┘   └───────────────┘   └─────────────┘
                               │
                               ▼
                 workspace: manifests · logs · metrics · reports
```

### 方法与集成

`llmdbenchmark` CLI 将 plan、standup、run、experiment、teardown 串成阶段；Jinja2 生成 Kustomize/Helm/Kubernetes manifests；支持 inference-perf、GuideLLM、vLLM benchmark 等 harness；DoE 可对 infrastructure 与 workload 参数做 sweep；workspace 保存输入、渲染结果、日志和报告，保证结果可追溯。它可以和 Inference Sim 做 GPU-free smoke test，也可以在 GKE、CoreWeave、OpenShift 等环境跑真实实验。

## 项目七：llm-d-inference-sim

### 作用与业务问题

Inference Sim 是轻量、可配置、实时的 vLLM 行为模拟器。它不跑真实模型，而是模拟 API、队列、延迟、KV cache、metrics、失败和 LoRA，从而让 Router、Autoscaling、Benchmark 和 CI 在没有 GPU 的环境先验证控制面行为。

### 架构图

```
OpenAI / vLLM client
          │ HTTP + HTTP/2
          ▼
┌─────────────────────────────────────────────────────────────────┐
│ llm-d-inference-sim                                             │
│ HTTP/OpenAI + vLLM gRPC + render/tokenize + admin/config        │
├───────────────────┬──────────────────┬──────────────────────────┤
│ Request/API        │ Simulator        │ Engine-compatible signals│
│ parsing/response   │ queue/worker      │ metrics + KV events      │
├───────────────────┼──────────────────┼──────────────────────────┤
│ latency calculator │ prefix KV cache  │ ZMQ BlockStored/Removed  │
│ constant/per-token│ block eviction   │ Prometheus vLLM metrics   │
└───────────────────┴──────────────────┴──────────────────────────┘
          │
          ├── OpenAI-compatible responses
          ├── Prometheus metrics
          └── ZMQ events → llm-d-kv-cache / EPP
```

### 方法与集成

延迟模型区分 prefill 与 decode：`prefill + decode`，支持 constant 或 per-token calculator；P/D 时用 KV transfer latency 替代 prefill。KV cache 将 prompt token 切成 blocks，模拟 hit、eviction、ZMQ event 和 `cached_tokens`；支持 `/v1/chat/completions`、`/v1/completions`、`/v1/responses`、`/v1/embeddings`、render/tokenize、gRPC Generate/GetModelInfo、failure injection 和运行时 admin config。它可被当作 vLLM-like backend 放进 InferencePool。

## 项目八：llm-d-planner（incubation）

### 作用与业务问题

Planner 解决的是 serving adoption 的上游问题：应用团队知道业务需求，但不知道模型、GPU、上下文长度、并发、TTFT/ITL SLO 和成本如何转换成 Kubernetes 部署。它把“自然语言需求 → 可编辑规格 → 多目标推荐 → 可部署 YAML”做成一个 Python/FastAPI/CLI 平台。

### 架构图

```
Business intent / user count / priorities
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────┐
│ FastAPI / UI / CLI                                                │
│ Intent Extraction → Specification Editor                          │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ Knowledge Base                                                     │
│ model catalog · GPU catalog · SLO templates · benchmark DB        │
│ Arena/Artificial Analysis quality · empirical/estimated data       │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ Recommendation                                                    │
│ capacity planner → config finder → quality/cost/latency scorer     │
│ → ranked views / what-if trade-offs                               │
└──────────────────────────────┬───────────────────────────────────┘
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│ Configuration / Deployment                                         │
│ Jinja2 → KServe/vLLM/HPA/ServiceMonitor YAML → Kubernetes          │
└──────────────────────────────────────────────────────────────────┘
```

### 方法与集成

Intent extraction 使用可替换 LLM provider（Ollama、OpenAI、Anthropic 或 OpenAI-compatible endpoint）；Specification 将 use case 映射到 traffic profile、TTFT/ITL/E2E SLO、quality category 和 priority；Recommendation 查询 `(model, GPU, traffic profile)` benchmark，计算 replicas，再按 quality、cost、latency 生成 Best Quality、Lowest Cost、Lowest Latency、Balanced 四种视图。Capacity Planner 估算 weights、KV、activation 和 GPU 数；GPU Recommender 在无真实 benchmark 时估算性能。Configuration Service 生成 KServe/vLLM/HPA/ServiceMonitor YAML，并提供 simulator 模式做 GPU-free 本地验证。

Planner 当前更像部署规划和推荐入口，不是 llm-d Router 的运行时组件；它未来计划补充 P/D、llm-d stack 参数搜索和更强安全验证。

## 统一业务问题与方法映射

| 业务问题 | 主要项目 | 方法 |
|---|---|---|
| 请求打到哪个 Pod 才快 | Router | EPP、Filter-Score-Pick、load/KV/latency-aware routing |
| 重复长上下文导致 prefill 浪费 | KV Cache + Router | KV events、block-key index、longest-prefix scoring |
| 长 prefills 阻塞 decode | Router + P/D | prefill/decode worker selection、NIXL KV transfer |
| 异构 GPU 和多 variant 扩缩 | Autoscaling | capacity model、cost/SLO optimization、HPA/KEDA actuator |
| 离线请求挤占在线流量 | Batch Gateway + Async | OpenAI Batch API、持久化 job、queue、flow control |
| 实验无法复现 | Benchmark | declarative scenario、rendered workspace、DoE |
| 没有 GPU 无法验证控制面 | Inference Sim | vLLM-like API、latency/KV/metrics/failure simulation |
| 从业务需求到部署配置成本高 | Planner | intent extraction、SLO planning、multi-criteria ranking、YAML generation |

## 关键设计判断

- **控制面与执行面分离**：llm-d 不替代 vLLM/SGLang，而是在 Kubernetes/Gateway/EPP 层做系统优化。
- **标准协议优先**：Gateway API、Envoy ext-proc、Prometheus、OpenAI API、vLLM-compatible API 和 ZMQ KV events 让组件可替换。
- **插件化调度**：Filter、Score、Pick 和 Profile Handler 允许把新的 KV、latency、LoRA、P/D 策略接入，而不重写 Proxy。
- **在线与离线分流**：Router 处理 request-level latency；Batch Gateway 处理 job-level durability；两者可通过 Async Processor 连接。
- **真实执行与实验替身分离**：Inference Sim 提供控制面信号，不应被当作生产性能基线；Benchmark 才负责真实环境的可复现实验。
- **成熟度有边界**：WVA 的部分 SLO 能力仍标为 experimental；KV hybrid-attention、DP rank 等能力仍在演进；Planner 的生产愿景与当前 POC 仍需区分。
