---
title: NVIDIA Dynamo 架构与业务问题（文档重构版）
tags: [architecture, ai-infra, llm-inference, distributed-serving, kv-cache, kubernetes, autoscaling]
date: 2026-09-13
sources: [dynamo-architecture-analysis.md]
related: [[dynamo]], [[llm-inference]], [[inference-routing]], [[disaggregated-serving]], [[kv-cache-offload]], [[model-serving-operator]], [[ai-gateway]], [[sglang]], [[vllm]]
---

# NVIDIA Dynamo 架构与业务问题（文档重构版）

> 原文：`raw/dynamo-architecture-analysis.md` · 仓库：https://github.com/ai-dynamo/dynamo · 分析版本 HEAD `ed64b7d`
> 本页按当前 README 与官方文档重构；“文档明确”与“架构推导”已尽量区分。

## 一句话定位

[[dynamo]] 是位于 [[sglang|SGLang]]、[[vllm|vLLM]]、TensorRT-LLM 之上的数据中心级 [[llm-inference|LLM 推理编排层]]。它解决跨节点、P/D 分离、KV 局部性、SLA 扩缩和故障迁移问题，而不是替代推理引擎本身。

## 它想解决的业务问题

- 长 prompt 的 prefill 会阻塞 decode：用独立 prefill/decode 池和 NIXL KV transfer 做资源隔离。
- 传统负载均衡不知道缓存：用 KV overlap + 活动负载做成本路由，减少重复 prefill。
- GPU 容量靠人工试错：用 DGDR 描述意图，Profiler/AIConfigurator 生成 DGD，Planner 在线调整副本。
- worker 故障直接暴露给用户：用 migration、worker inhibition、canary 和 graceful shutdown 保持服务连续性。
- 平台入口各有标准：可选 Dynamo Frontend-native 路由，或 Gateway API + GAIE EPP，把入口治理和 serving selection 解耦。

## 核心架构图

```
                              ┌───────────────────────────────┐
                              │        在线业务 / Agent        │
                              │ OpenAI API · Responses · Tools │
                              └───────────────┬───────────────┘
                                              │ HTTP / SSE / gRPC
                       ┌──────────────────────▼──────────────────────┐
                       │             入口与请求编排层                 │
                       │ Frontend / Gateway EPP / Standalone Router  │
                       │ auth · protocol · tokenize · session hints  │
                       └───────────────┬──────────────────┬───────────┘
                                       │                  │
                              route decision       request dispatch
                                       │                  │
                       ┌──────────────▼──────────────────▼───────────┐
                       │                 Dynamo Runtime                │
                       │ Namespace → Component → Endpoint             │
                       │ discovery · request plane · event plane       │
                       └───────┬───────────────────┬──────────────────┘
                               │                   │
                KV overlap + load          endpoint registration / health
                               │                   │
              ┌────────────────▼───────┐   ┌─────▼────────────────────┐
              │     KV-aware Router     │   │ Discovery / Control       │
              │ prefix index + scoring  │   │ etcd / Kubernetes / file  │
              │ filters + worker choice │   │ EndpointSlice / metadata  │
              └───────────┬─────────────┘   └──────────┬────────────────┘
                          │                            │
             ┌────────────▼────────────┐  ┌───────────▼───────────────┐
             │      Serving graph       │  │    Capacity control       │
             │  Prefill pool ↔ Decode   │  │ Profiler → Planner        │
             │  pool; aggregated mode   │  │ Prometheus → scale target  │
             └───────┬──────────┬───────┘  └───────────┬───────────────┘
                     │          │                     │
              KV via NIXL   engine API          DGD / DGDR reconcile
                     │          │                     │
        ┌────────────▼───┐ ┌────▼─────────────┐ ┌─────▼─────────────────┐
        │ Prefill Worker  │ │ Decode Worker    │ │ Kubernetes Platform    │
        │ prompt → KV     │ │ KV → tokens      │ │ Operator · DGD · DCD   │
        │ SGLang/vLLM/TRT │ │ SGLang/vLLM/TRT  │ │ Grove / Gateway API     │
        └────────┬────────┘ └──────┬──────────┘ └──────────┬────────────┘
                 │                 │                       │
                 └────────┬────────┴──────────────┬────────┘
                          │                       │
                ┌─────────▼─────────┐   ┌────────▼────────────────────┐
                │ KV state & events │   │ Observability               │
                │ GPU/CPU/NVMe/Blob │   │ Prometheus · OTLP · Grafana  │
                │ KV events/index   │   │ traces · logs · FPM          │
                └───────────────────┘   └─────────────────────────────┘
```

## 模块分层与边界

| 层 | 功能 | 边界 |
|---|---|---|
| 入口 | Frontend、Gateway EPP、Standalone Router | 协议、tokenize、入口治理；不实现 GPU kernel |
| 决策 | KV-aware Router、PrefillRouter | 选择 worker；不拥有全局 Kubernetes 状态 |
| Runtime | Namespace、Component、Endpoint、discovery/request/event planes | 连接与生命周期；不替代 Operator |
| 执行 | Prefill/Decode/Aggregated Workers + backend engine | batching、sampling、KV、token generation |
| KV/传输 | NIXL、KV index/events、KVBM/offload | KV transfer 与分层存储；不等价于强一致数据库 |
| 控制 | DGDR、Profiler、AIConfigurator、Planner、DGD/DCD、Operator、Grove | 配置搜索、扩缩、放置；不进入 token 热路径 |
| 横切 | Prometheus、OTLP、canary、migration | 观测与可靠性；不能阻塞推理热路径 |

## 请求与控制流

### 聚合请求

```
Client
  │ 1. OpenAI-compatible request
  ▼
Frontend
  │ 2. validate → chat template → tokenize → normalize sampling
  ▼
Router
  │ 3. filter ready workers
  │ 4. score KV overlap + active prefill + active decode + request count
  ▼
Selected aggregated worker
  │ 5. continuous/inflight batching inside backend engine
  │ 6. prefill + decode on the same worker pool
  ▼
Token stream
  │ 7. detokenize / aggregate if non-streaming
  ▼
Frontend ───────────────────────────────────────────────► Client
```

### P/D 分离请求

```
Client → Frontend → PrefillRouter
                         │
                         ├─① 选择 prefill worker
                         │       │
                         │       ├─计算 prompt
                         │       ├─生成 KV blocks
                         │       └─返回 disaggregated_params
                         │
                         ├─② 选择 decode worker
                         │       │
                         │       ├─注入 transfer metadata
                         │       ├─通过 NIXL 协调 GPU↔GPU KV transfer
                         │       └─使用 KV 开始逐 token decode
                         │
                         └─③ stream tokens → Frontend → Client
```

### KV-aware 路由反馈环

```
              ┌──────────────────────────────────────────┐
              │              Request arrives              │
              └────────────────────┬─────────────────────┘
                                   ▼
                         tokenize / normalize
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        KV prefix index                         active-load snapshot
        cached block overlap                    prefill/decode/request
                 └─────────────────┬─────────────────┘
                                   ▼
                       worker filters + cost score
                                   │
                                   ▼
                              worker choice
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
           request dispatch                    KV lifecycle events
                                                     │
                                                     └──► index refresh
```

路由本质是把 cache locality 转成成本折扣，同时惩罚已分配的 prefill/decode 工作：`adjusted_prefill = max(raw_prefill - overlap_credit, 0)`，再与 projected decode blocks、active request penalty 合并。它不是“永远选择 cache 命中最多的 worker”。详见 [[inference-routing]] 与 [[radix-attention]]。

### DGDR → DGD → Serving

```
用户意图
  │ model + backend + hardware + workload + SLA + optional planner
  ▼
DGDR
  │ discover GPU type / memory / node capacity
  ▼
Profiler
  │ rapid: performance estimates
  │ thorough: deploy candidates and benchmark on real GPUs
  ▼
AIConfigurator
  │ enumerate → evaluate → rank candidate topology / parallelism / replicas
  ▼
Generated DGD
  │ autoApply=true  ───────────────┐
  │ autoApply=false → user review   │
  ▼                                ▼
Operator reconcile                 DGD applied
  │ create worker graph / DCD / services / optional planner
  ▼
Serving deployment
```

### Planner 扩缩闭环

```
┌─────────┐   ┌─────────┐   ┌───────────┐   ┌──────────────┐
│ OBSERVE │ → │ PREDICT │ → │ PROPOSE   │ → │ RECONCILE    │
│ metrics │   │ req/ISL │   │ replicas  │   │ constraints  │
└─────────┘   └─────────┘   └───────────┘   └──────┬───────┘
                                                   ▼
                                           ┌──────────────┐
                                           │ CONSTRAIN    │
                                           │ min/GPU/SLA  │
                                           └──────┬───────┘
                                                  ▼
                                           ┌──────────────┐
                                           │ EXECUTE      │
                                           │ scale_to     │
                                           └──────┬───────┘
                                                  ▼
                                  Operator / connector changes replicas
                                                  │
                                                  └──── feedback ────► OBSERVE
```

throughput loop 预测持续需求并提供下界，load loop 快速纠正 SLA 压力。它们共享 worker inventory、性能模型、KV hit rate、speculative accept length 与 GPU budget；因此 Planner 不是普通 CPU utilization HPA。

### Gateway API 路由

```
Client
  │
  ▼
Kubernetes Gateway / HTTPRoute
  │ 入口策略、认证、限流、边缘观测
  ▼
GAIE Endpoint Picker Plugin (EPP)
  │ 复用 Dynamo KV-aware selection
  ▼
Selected worker Frontend sidecar
  │ router-mode=direct
  ▼
Worker / engine
```

### 故障迁移

```
request in flight
      │
      ▼
worker error / timeout / disconnect
      │
      ├─不可迁移错误 → reject / return error
      │
      └─可迁移错误
            │ cache token/request state
            │ inhibit failed worker locally
            ▼
      choose healthy endpoint
            │ migration_limit not exceeded
            ├───────────────┐
            ▼               │
      replay request        │ limit reached
            │               ▼
            └──────► stream response or final failure
```

### 可观测性

```
Dynamo processes
  ├─ pull /metrics ─────────────► Prometheus ───────► Grafana
  ├─ OTLP traces/logs ──────────► OTel Collector ───► Tempo / Loki
  ├─ FPM event publication ─────► event plane
  │                                └─ bounded trace queue → JSONL(.gz)
  └─ request trace rows ─────────► JSONL / NATS / OTLP / stderr sinks
```

## 关键设计判断

- **Engine 与 orchestration 分离**：复用 backend 的 kernel、batching、sampling 专业能力。
- **KV 是集群级资源**：既影响路由，也影响 P/D transfer 和分层存储。
- **三平面解耦**：request、discovery、event 具有不同延迟与一致性目标。
- **Profiler 与 Planner 分工**：部署前找配置，部署后调容量。
- **Operator 与 Router 分工**：最终一致地物化资源，毫秒级做在线选择。
- **入口可替换**：Frontend-native 与 Gateway API/EPP 共用 serving selection。
- **旁路可观测**：观测落后时丢 trace，不阻塞推理热路径。

## 选型与限制

适合长上下文、多 GPU/多节点、P/D 分离、需要 KV-aware routing、SLA autoscaling 或快速扩容的生产推理。单模型、单 GPU、没有跨节点协调需求时，直接使用 [[vllm]] 或 [[sglang]] 更简单。

P/D 分离会增加 KV transfer；Planner 依赖指标与性能模型；migration 需要请求幂等；远端 KV 需要额外的数据驻留和租户隔离治理。README 中的 2x TTFT、7x 启动等数字是特定 benchmark，不应视为通用保证；本次没有运行 GPU benchmark。

## 相关页面

- [[dynamo]]
- [[llm-inference]]
- [[inference-routing]]
- [[disaggregated-serving]]
- [[kv-cache-offload]]
- [[model-serving-operator]]
- [[ai-gateway]]
