---
title: NVIDIA Dynamo 架构与设计思路分析
tags: [architecture, ai-infra, llm-inference, distributed-serving, kv-cache, kubernetes]
date: 2026-05-15
sources: [dynamo-architecture-analysis.md]
related: [[dynamo]], [[vllm]], [[sglang]], [[paged-attention]], [[radix-attention]], [[disaggregated-serving]], [[kv-cache-offload]]
---

# NVIDIA Dynamo 架构与设计思路分析

> 原文：`raw/dynamo-architecture-analysis.md` · 仓库：https://github.com/ai-dynamo/dynamo · 分析版本 1.2.0（commit 7997117，2026-05-15）

## 一句话定位

[[dynamo]] 是 NVIDIA 开源的**数据中心级 [[llm-inference|LLM 推理]]编排层**：用 Rust 运行时 + Python 组件 + Go K8s Operator，把 [[sglang|SGLang]] / [[vllm|vLLM]] / TensorRT-LLM 等推理引擎拼成具备[[disaggregated-serving|分离式 prefill/decode]]、[[radix-attention|KV 感知路由]]、四级 KV 缓存（KVBM）和 SLA 自动扩缩容的协调集群。它不替代推理引擎，而是让一群 GPU/Node 变成"一个协调的推理系统"。

## 核心架构图

```
                    ┌─────────────────────────────────────────────┐
                    │              Client (OpenAI API)            │
                    └────────────────────┬────────────────────────┘
                                         │ HTTP / SSE
┌────────────────────────────────────────▼─────────────────────────────────────┐
│ FRONTEND (Rust axum + Python wrapper)     lib/llm/src/http  +  components/  │
│   /v1/chat/completions  ─► validate ─► preprocess ─► migration ─► route     │
└────────────────────────────────────────┬─────────────────────────────────────┘
                                         │
            ┌────────────────────────────┼────────────────────────────┐
            │     REQUEST PLANE          │      CONTROL PLANE         │
            │   (TCP / NATS Core)        │   (etcd / K8s / file)      │
            │                            │                            │
            ▼                            ▼                            ▼
┌──────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
│ KV-Aware Router      │  │ DistributedRuntime     │  │ Planner (Python)       │
│ lib/kv-router        │  │ lib/runtime            │  │ components/.../planner │
│ - Radix tree of      │  │ - Discovery trait      │  │ - Prometheus scrape    │
│   block hashes/wkr   │  │ - Component registry   │  │ - Throughput + Load    │
│ - Cost function:     │  │ - HealthCheckManager   │  │   scaling laws         │
│   prefill_load +     │  │ - Pipeline framework   │  │ - Emits ScalingDecision│
│   decode_cost -      │  │                        │  │   to K8s Operator      │
│   overlap credits    │  └─────────┬──────────────┘  └──────────┬─────────────┘
└──────────┬───────────┘            │                            │
           │                        │ register / watch           │ patch DGD
           ▼                        ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ WORKER POOL (Python wrappers around backends via PyO3)                      │
│                                                                             │
│   Prefill Worker        ────KV transfer (NIXL/GDS)────►   Decode Worker    │
│   ┌──────────────┐                                        ┌──────────────┐ │
│   │ SGLang/vLLM/ │      ◄────KV-events (NATS JetStream)─► │ SGLang/vLLM/ │ │
│   │ TRT-LLM      │                                        │ TRT-LLM      │ │
│   │ + KVBM hooks │                                        │ + KVBM hooks │ │
│   └──────┬───────┘                                        └──────┬───────┘ │
└──────────┼───────────────────────────────────────────────────────┼─────────┘
           │                                                       │
┌──────────▼───────────────────────────────────────────────────────▼─────────┐
│ STORAGE / EVENTS PLANE                                                      │
│                                                                             │
│   KVBM Tier Hierarchy (lib/kvbm-*)            NATS JetStream + Object Store │
│   G1: GPU device memory   ──LRU──┐            - kv-events subject           │
│   G2: CPU pinned          ──LFU──┤            - Radix tree snapshots        │
│   G3: NVMe/SSD (NIXL)            │                                          │
│   G4: S3/Azure/Object (NIXL)     │                                          │
│                                  │                                          │
│   Consolidator dedupes by         │                                          │
│   SequenceHash (128-bit PLH)      │                                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                         ▲
                                         │ topology-aware gang sched
┌────────────────────────────────────────┴─────────────────────────────────────┐
│ K8s Operator (Go, deploy/operator/)                                          │
│   DGDR (request)  ─►  DGD (graph)  ─►  DCD (per-component pods)             │
│   AIConfigurator profiles ─► Planner picks ─► Grove places (NVL72 aware)    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| HTTP 前端（Rust axum + Python wrapper） | OpenAI 兼容入口、SSE 流式、聚合、validation |
| 预处理流水线 | Tokenize、prompt template、多模态 decode、采样归一化 |
| 迁移层（`migration.rs`） | 失败 worker 在飞请求自动迁移到新 worker（RetryManager） |
| [[radix-attention\|KV-aware Router]] | XXH3 hash → radix tree → cost-based softmax 选 worker；多副本经 NATS JetStream 同步 |
| 分布式运行时（`lib/runtime`） | Runtime/Endpoint/Discovery/Transport 抽象；TCP+NATS 双平面 |
| KVBM（KV Block Manager） | G1-G4 四级 KV 缓存、NIXL 零拷贝、TinyLFU 升降级、SequenceHash 去重 |
| Backend wrapper（Python） | [[sglang]]/[[vllm]]/TRT-LLM 适配；通过 PyO3 接入 Rust 运行时 |
| Planner（SLA 自动扩缩） | Prometheus scrape + state machine + 推 K8s operator |
| K8s 控制面（Go + Grove + Gateway plugin） | CRD: DGDR→DGD→DCD；拓扑感知 gang scheduling |

**关键约束：**

- 性能敏感路径（HTTP、tokenize、路由、KVBM）**全部在 Rust**；backend 适配薄到只剩 "engine.generate + publish KV events"。
- K8s operator 不做 placement，**把拓扑感知外包给 Grove**。
- 控制平面（discovery）和事件平面（KV events）**默认分离**：file/mem 用 ZMQ，etcd/K8s 用 NATS。

## 关键数据流

**端到端请求路径（HTTP arrival → token streaming）：**

```
[1] HTTP POST /v1/chat/completions
        │
        ▼
[2] axum Router (lib/llm/src/http/service/openai.rs:2012)
    └─► handler_chat_completions
        │
        ▼
[3] Validate (openai.rs:1233-1254)
    + Apply model/temperature/token defaults
        │
        ▼
[4] Preprocessor pipeline (lib/llm/src/preprocessor/)
    TokenizeOperator → PromptFormattingOperator → SamplingOperator
    NvCreateChatCompletionRequest ──► PreprocessedRequest
        │
        ▼
[5] Migration layer (lib/llm/src/migration.rs:115)
    RetryManager wraps the call; on CannotConnect/Disconnected/
    EngineShutdown (line 189) replays with Context::with_id(...)
        │
        ▼
[6] KV-aware route decision
    ├─ Hash prompt → PLH blocks (XXH3, block_size=128, LoRA-aware)
    ├─ Query ConcurrentRadixTree per worker for prefix overlap
    └─ Selector logit (lib/kv-router/src/scheduling/selector.rs:161):
       cost = prefill_load_scale × adjusted_prefill_blocks + decode_cost_blocks
       softmax(−cost) sample
        │
        ▼
[7] Dispatch via Request Plane
    └─ TCP (pooled) or NATS Core → worker generate endpoint
        │
        ▼
[8] Worker (Python) calls backend engine
    ├─ SGLang: sgl.Engine.async_generate(...)
    ├─ vLLM:   AsyncLLMEngine.generate(...)
    └─ TRT-LLM: trtllm executor
        │
        ▼ [if disaggregated]
[9] PrefillRouter picks prefill worker → runs prefill
    └─ disaggregated_params returned
        │
        ▼
[10] PrefillRouter picks decode worker
     └─ KV blocks transferred via NIXL/GPUDirect-RDMA
        │
        ▼
[11] Decode generates tokens
     ├─ Each new block: KVBM.OffloadManager computes SequenceHash
     └─ publish to NATS "kv-events" subject
        │
        ▼
[12] Tokens stream back through SSE
     └─ ChatCompletionAggregator collapses if stream=false
        │
        ▼
[13] Response to client (status 200, JSON or SSE)
```

**容错路径：** worker 在 [8]–[11] 任意阶段挂掉 → `RetryManager` 检测 `is_migratable()` 错误 → 用同一个 `PreprocessedRequest` 重发到新 worker。guided decoding 和 n>1 sampling 因状态机不可复制而禁用迁移。

**Planner 自动扩缩容循环：**

```
            ┌──────────────────────────────────────────────────────┐
            │  Tick scheduler (load ~10s, throughput ~60s, "agg")  │
            └────────────────────────┬─────────────────────────────┘
                                     │
                ┌────────────────────▼────────────────────┐
                │  _gather_tick_input()                   │
                │  - Prometheus: TTFT, ITL, ISL, OSL, QPS │
                │  - FPM subscriber (ForwardPassMetrics)  │
                │  - per-worker queue depth               │
                └────────────────────┬────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            ▼
┌──────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│ Throughput branch│   │  Load branch         │   │ Correction factors:  │
│ predict next-win │   │  estimate latency    │   │ prefill_correction = │
│ traffic × safety │   │  from queue + FPM    │   │   actual_ttft /      │
│ → replicas LB    │   │  vs SLA threshold    │   │   expected_ttft      │
└────────┬─────────┘   └──────────┬───────────┘   │ decode_correction =  │
         │                        │               │   actual_itl /       │
         └──── load > throughput ─┤               │   expected_itl       │
                                  │               └──────────────────────┘
                                  ▼
                   ScalingDecision(num_prefill, num_decode) | None
                                  │
                                  ▼
                    _apply_effects() ──► K8s operator
                                       ──► patches DGD replicas
                                  │
                                  ▼
                   Prometheus counters + JSON diagnostics
```

**KV-aware Router cost function：**

```text
adjusted_prefill_blocks = max(
    prefill_blocks
    - overlap_score_credit * device_overlap_blocks
    - host_cache_hit_weight * host_overlap_blocks
    - disk_cache_hit_weight * disk_overlap_blocks
    - shared_cache_multiplier * shared_beyond_blocks,
    0,
)
cost = prefill_load_scale * adjusted_prefill_blocks + decode_blocks
```

## 设计决策与哲学

- **三平面架构解耦**：请求平面（低延迟，TCP/NATS Core）、控制平面（desired-state，etcd/K8s/file）、存储+事件平面（[[radix-attention|KV 可见性]]，NATS JetStream + Object Store）三者独立演进。事件平面持久化保证 router 副本重启后能 replay。

- **Rust 内核 + Python 适配 + Go 控制器**三语言协作：性能敏感路径全在 Rust（1000 个 .rs 文件）；backend 适配做到薄薄一层 Python（896 个 .py）；K8s CRD 控制循环用 Go（258 个 .go）。

- **请求迁移是默认能力**：`RetryManager` 把 worker 死亡变成对客户端透明的事件。这是 Dynamo 区别于纯推理引擎（[[vllm]]、[[sglang]]）的根本特征——它把"集群"当作一等公民。

- **KV 块的全局身份 = SequenceHash**：128-bit PositionalLineageHash（XXH3, seed=1337，混入 LoRA id）让一个 KV 块在 GPU/CPU/SSD/远端 + 多 worker 之间有同一个名字。Consolidator 去重、router 前缀匹配、KVBM 升降级都用它。

- **KVBM 四级层次（G1-G4）与 NIXL 统一传输**：G1=GPU device、G2=CPU pinned、G3=NVMe/SSD、G4=S3/Azure。LRU 管 G1→G2，TinyLFU + presence filter 管 G2→G3。所有层都包装成 NIXL MemType，使得不同 tier 间的代码路径几乎同形。参见 [[kv-cache-offload]]。

- **KV-aware 路由 ≠ 最大化命中率**：成本函数同时惩罚 prefix overlap 不足和当前 worker 负载。多 router 副本通过 NATS JetStream 同步活跃块视图。softmax(−cost) 采样而非 argmin，留出概率分散负载。

- **AIConfigurator → Planner → Operator 三段式 SLA 闭环**：AIConfigurator 离线扫 10K+ TP/EP/DEP 配置选 Pareto 前沿 → Planner 在线决策扩缩 → Operator 物化 K8s 资源。这是 1.0 "zero-config DGDR" 的实现基础。

- **拓扑感知外包给 Grove**：Operator 不做 NVL72/rack/host placement，把 component group 翻译成 Grove `PodCliqueSet` + `PodCliqueScalingGroup` 交给外部 scheduler，只读 Grove condition 反传 DGD status。

- **Discovery backend 是 trait，不是硬编码**：`KVStoreDiscovery`（etcd/file/memory）/`KubeDiscoveryClient`（EndpointSlice）/`MockDiscovery` 三种实现可热切。模型注册有身份冲突检测——不同模型注册同一 endpoint 会被拒绝（LoRA adapter 除外）。

- **canary 健康检查 + 自愈再注册**：每个 endpoint 独立 health check task，超时则标 `NotReady` 并触发 re-register，K8s 拉起新 pod 后立即恢复路由。

## KVBM 四级层次（核心组件深入）

```
┌─────────────────────────────────────────────────────┐
│ GPU Memory (G1)                    lib/kvbm-engine │
│ - Fastest, smallest capacity                        │
│ - Active compute blocks                             │
└──────────────┬──────────────────────────────────────┘
               │ Offload G1→G2 (LRU pop_lru)
               ↓
┌─────────────────────────────────────────────────────┐
│ CPU/Host Memory (G2)     lib/kvbm-logical (pools)  │
│ - Pinned DRAM staging                               │
│ - µs-latency RDMA ready  lib/kvbm-physical         │
└──────────────┬──────────────────────────────────────┘
               │ Offload G2→G3 (TinyLFU + presence filter)
               ↓
┌─────────────────────────────────────────────────────┐
│ NVMe/SSD (G3)           lib/kvbm-physical/storage  │
│ - Persistent warm cache                             │
│ - ms-latency disk ops                               │
└──────────────┬──────────────────────────────────────┘
               │ Offload G3→G4 (NIXL OBJ backend)
               ↓
┌─────────────────────────────────────────────────────┐
│ Object Storage (G4)      lib/llm/block_manager/    │
│ - S3/MinIO/Azure Blob    storage/object.rs         │
│ - Unlimited capacity, seconds+ latency              │
└─────────────────────────────────────────────────────┘
```

块生命周期 8 阶段：Allocate → Fill → Schedule → Compute → Hash（128-bit SequenceHash）→ Register → Consolidate（按 SequenceHash 去重）→ Evict/Restore（weak ref demotion）。

NIXL 把 GPUDirect RDMA、NVMe-oF、对象存储都包装成统一 MemType，G1↔G2↔G3↔G4 的传输代码路径同形。详见 raw 中的"关键组件深入解读 / KVBM" 节。

## 相关页面

- [[dynamo]] — 项目主页
- [[vllm]] — 支持的推理 backend 之一
- [[sglang]] — 支持的推理 backend 之一
- [[paged-attention]] — KV cache 分块管理基础理念
- [[radix-attention]] — KV-aware 路由的算法基础
- [[disaggregated-serving]] — 分离式 prefill/decode 概念
- [[kv-cache-offload]] — KV 多级缓存方法论
