---
title: llm-d 核心项目群架构再调研
tags: [architecture, llm-serving, kubernetes, inference-routing, kv-cache, autoscaling, batch-inference]
date: 2026-09-13
sources: [llm-d-core-projects-research-2026-09-13.md]
related: [[llm-d]], [[llm-d-router]], [[llm-d-kv-cache]], [[llm-d-workload-variant-autoscaler]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-inference-sim]], [[llm-d-planner]], [[gateway-api-inference-extension]], [[vllm]], [[sglang]], [[disaggregated-serving]], [[model-serving-operator]]
---

# llm-d 核心项目群架构再调研

> 原文：`raw/llm-d-core-projects-research-2026-09-13.md` · 调研日期：2026-09-13

## 一句话定位

[[llm-d]] 是位于 [[vllm]] / [[sglang]] 之上的 Kubernetes-native 分布式推理控制与优化栈；核心项目围绕路由、KV cache、P/D、扩缩容、Batch、实验验证和部署规划形成完整链路。

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

## 核心项目职责

| 项目 | 作用 | 解决的业务问题 | 主要集成 |
|---|---|---|---|
| [[llm-d]] | 主架构、部署 recipe、API 和 well-lit paths | 把模型 server 组合成生产 serving stack | Kubernetes、Gateway API、vLLM、SGLang、Prometheus |
| [[llm-d-router]] | Proxy + EPP 智能入口 | endpoint picking、排队、公平性、P/D 编排 | Envoy ext-proc、InferencePool、InferenceObjective |
| [[llm-d-kv-cache]] | KV event index/scorer library | 重复 prefix 重算、缓存局部性丢失 | vLLM/SGLang KV events、ZMQ、Router EPP |
| [[llm-d-workload-variant-autoscaler]] | variant 全局扩缩 | 异构 GPU、P/D、成本与 SLO 的联合分配 | Prometheus、HPA/KEDA、InferencePool |
| [[llm-d-batch-gateway]] | OpenAI-compatible Batch API | 大量离线请求的持久化、重试和限流 | PostgreSQL、Redis/Valkey、object store、Router |
| [[llm-d-benchmark]] | 实验生命周期编排 | 多环境、多配置实验不可复现 | Jinja2、Kustomize/Helm、GuideLLM、inference-perf |
| [[llm-d-inference-sim]] | vLLM 行为模拟器 | 无 GPU 验证 routing/autoscaling/CI | OpenAI API、vLLM gRPC、ZMQ、Prometheus |
| [[llm-d-planner]] | 需求到部署规划 | 不懂 GPU/模型/SLO 的团队难以落地 | FastAPI、SQLite、LLM provider、KServe/vLLM YAML |

## Router / EPP 请求路径

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

[[llm-d-router]] 的方法是插件化 `Filter → Score → Pick`，而不是把某个 routing heuristic 固化在 Proxy 中。EPP 还能通过 Flow Control 处理 priority band、saturation、fairness 和 ordering；Proxy 继续承担连接、TLS 和转发。

## KV Cache 路径

### Router 架构图

~~~
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
~~~

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

[[llm-d-kv-cache]] 的关键不是“把 KV 存到哪里”，而是把 engine 的 KV state 转成 Router 可查询的 locality signal。它支持 vLLM/SGLang event adapter、最长连续 prefix、tier 权重、multimodal/LoRA extra keys 和 speculative indexing；tokenization 正在从库内 pool 迁移到外部 host/sidecar。

## Autoscaling、Batch 与实验闭环

### Autoscaling

WVA 读取 queue、running、KV、latency、pending Pod 和 accelerator inventory，计算 `desired replicas`，再让 HPA/KEDA 执行。单一同构 Deployment 适合 KEDA + EPP metrics；多 variant、P/D、异构硬件和强 SLO 才需要 WVA。

### Batch

Batch Gateway 负责 job/file/output 的 durable lifecycle；Async Processor 负责从 Redis 或 Pub/Sub 取单请求、结合系统信号做 flow control，再调用 Router。它和在线 Router 的区别是：前者优化 job 可恢复性和吞吐，后者优化单请求延迟与端点选择。

### Benchmark 与 Simulator

Benchmark 用 declarative scenario、Jinja render、Kubernetes lifecycle、harness 和 workspace 实现可复现实验；Inference Sim 用 OpenAI/vLLM API、延迟公式、KV blocks、metrics 和 failure injection 让这些实验可以在无 GPU 环境做控制面 smoke test。Simulator 不是生产性能基线。

## Planner 的上游入口

[[llm-d-planner]] 把自然语言或结构化业务意图转换成 traffic profile、TTFT/ITL/E2E SLO、quality/cost/latency 权重，再用 benchmark、capacity planner 和 GPU recommender 生成部署建议，最后渲染 KServe/vLLM/HPA/ServiceMonitor YAML。它是 adoption/planning 层，不在 Router 的在线请求路径内。

## 设计判断与边界

- [[llm-d]] 负责组合和标准化，不替代推理 engine。
- [[llm-d-router]] 负责 endpoint-level intelligence，不是通用 provider gateway。
- [[llm-d-kv-cache]] 负责 locality index/scoring，不等同于 KV offload 或 KV transfer。
- WVA 通过 HPA/KEDA 执行扩缩，不直接取代 Kubernetes autoscaler。
- Batch Gateway 解决异步 job，不应把 batch 请求直接当 interactive request。
- Benchmark 与 Simulator 负责验证和实验，不能把模拟延迟当真实 GPU 指标。
- Planner 解决部署规划，当前仍要区分生产愿景和 POC 实现。

## 各项目架构图补充

### 核心请求数据流

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

### WVA

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

### Batch Gateway

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

### Benchmark

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

### Inference Sim

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

### Planner

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

## 相关页面

- [[inference-routing]]
- [[kv-cache-offload]]
- [[disaggregated-serving]]
- [[model-serving-operator]]
- [[gateway-api-inference-extension]]
- [[vllm]]
- [[sglang]]
