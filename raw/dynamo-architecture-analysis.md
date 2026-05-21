# NVIDIA Dynamo 架构与设计思路分析

> 仓库：https://github.com/ai-dynamo/dynamo · 分析日期：2026-05-15 · 版本：1.2.0（commit 7997117）

## 一句话定位

NVIDIA Dynamo 是一个**数据中心级 LLM 推理编排层**：用 Rust 运行时 + Python 组件 + Go K8s Operator，把 SGLang/vLLM/TensorRT-LLM 工作节点拼成具备分离式 prefill/decode、KV 感知路由、四级 KV 缓存（KVBM）和 SLA 自动扩缩容的协调集群。Dynamo 不替代推理引擎，而是让一组 GPU/Node 变成"一个协调的推理系统"。

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

| 层 / 模块 | 主要 crate / 目录 | 职责 |
|----------|-------------------|------|
| HTTP 前端 | `lib/llm/src/http/` (Rust axum) + `components/src/dynamo/frontend/` (Python) | OpenAI 兼容入口、SSE 流式、聚合、validation |
| 预处理流水线 | `lib/llm/src/preprocessor/` | Tokenize（fastokens）、prompt template、多模态 decode、采样归一化 |
| 迁移层 | `lib/llm/src/migration.rs` | 失败 worker 在飞请求自动迁移到新 worker（`RetryManager`） |
| KV-aware Router | `lib/kv-router/` + `lib/kv-hashing/` + `lib/llm/src/kv_router/` | XXH3 hash → radix tree → cost-based softmax 选 worker；多副本经 NATS JetStream 同步 |
| 分布式运行时 | `lib/runtime/` | `Runtime`/`DistributedRuntime`/`Endpoint`/`Discovery` 抽象；TCP+NATS 双平面；HealthCheckManager |
| KVBM (KV Block Manager) | `lib/kvbm-{common,config,engine,kernels,physical,logical,consolidator}/` + `lib/llm/src/block_manager/` | G1-G4 四级 KV 缓存、NIXL 零拷贝传输、TinyLFU 升降级、SequenceHash 去重 |
| Backend wrapper（Python） | `components/src/dynamo/{sglang,vllm,trtllm,frontend,planner,router}/` | Python 进程 + 引擎实例 + 通过 PyO3 注册到 Rust 运行时 |
| Python ↔ Rust 绑定 | `lib/bindings/python/` | maturin/PyO3 把 `DistributedRuntime`、`Endpoint`、`Client`、`RouterMode` 暴露给 Python |
| Planner（SLA 自动扩缩） | `components/src/dynamo/planner/core/` | Prometheus scrape + state machine + 推 K8s operator |
| K8s 控制面 | `deploy/operator/` (Go) + Grove（外部 repo）+ `deploy/inference-gateway/` | CRD: DGDR→DGD→DCD；Grove 做拓扑感知 gang scheduling |

**关键约束：**

- 性能敏感路径（HTTP、tokenize、路由、KVBM）**全部在 Rust**；backend 适配薄到只剩"engine.generate + publish KV events"。
- Python 进程里只有一个 tokio runtime（`pyo3_async_runtimes::tokio::init_with_runtime`），Python `await` 直通 Rust async stream。
- K8s operator 不做 placement，**把拓扑感知外包给 Grove**（external scheduler）。
- 控制平面（discovery）和事件平面（KV events）**默认分离**：file/mem 用 ZMQ 事件，etcd/K8s 用 NATS 事件。

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

**容错路径：** worker 在 [8]–[11] 任意阶段挂掉 → frontend 的 `RetryManager::new_stream()`（migration.rs:212）检测到 `is_migratable()` 错误（CannotConnect / Disconnected / ConnectionTimeout / EngineShutdown）→ 用同一个 PreprocessedRequest 重发到新 worker。已生成 token 的续接由 worker 协议层处理；guided decoding 和 n>1 sampling 因状态不可复制而禁用迁移。

**Planner 自动扩缩容循环（components/src/dynamo/planner/core/state_machine.py:189）：**

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

## 设计决策与哲学

- **三平面架构解耦**：请求平面（低延迟 token gen，TCP/NATS Core）、控制平面（desired-state 扩缩，etcd/K8s/file）、存储+事件平面（KV 可见性，NATS JetStream + Object Store）三者独立演进。事件平面用 JetStream 持久化，router 副本重启后可 replay 历史事件重建 radix tree。参见 `lib/runtime/src/distributed.rs:46`（DistributedRuntime 同时持有 discovery_client / tcp_server / nats_client）。

- **Rust 内核 + Python 适配 + Go 控制器**三语言协作：性能敏感路径全在 Rust（1000 个 `.rs` 文件）；backend 适配做到薄薄一层 Python（896 个 `.py`）；K8s CRD 控制循环用 Go（258 个 `.go`）。各司其职，不重复造轮子。

- **请求迁移是默认能力**：`RetryManager` 把 worker 死亡变成对客户端透明的事件。`migration.rs:189` 的 `is_migratable()` 用错误枚举枚举可恢复错误；guided decoding 和 n>1 因 FSM/状态机不可复制而被显式排除。这是 Dynamo 区别于纯推理引擎的根本特征——它把"集群"当作一等公民。

- **KV 块的全局身份 = SequenceHash**：128-bit PositionalLineageHash（XXH3, seed=1337, 把 LoRA adapter id 混入 seed）让一个 KV 块在 GPU/CPU/SSD/远端 + 多 worker 之间有同一个名字。Consolidator 用它去重（跨 ZMQ for vLLM/TRT-LLM 和 in-process for KVBM），router 用它前缀匹配，KVBM 用它升降级。参见 `lib/kvbm-common/src/lib.rs:SequenceHash`。

- **KVBM 四级层次（G1-G4）与 NIXL 统一传输**：G1=GPU device、G2=CPU pinned、G3=NVMe/SSD、G4=S3/Azure/Object。LRU 管 G1→G2（`lib/kvbm-logical/src/pools/inactive/backends/lru_backend.rs:68`），TinyLFU + presence filter 管 G2→G3（`lib/kvbm-engine/src/offload/policy.rs:20`）。所有层都包装成 NIXL MemType，使得不同 tier 间的代码路径几乎同形。Weak reference 持有避免悬空。

- **KV-aware 路由 ≠ 最大化命中率**：成本函数同时惩罚 prefix overlap 不足和当前 worker 负载（`lib/kv-router/src/scheduling/selector.rs:161`）。多 router 副本通过 NATS JetStream 同步 `AddRequest`/`MarkPrefillCompleted`/`Free` 事件，避免单点。softmax(−cost) 采样而非 argmin，留出概率分散负载（temperature=0 时退化成贪心）。

- **AIConfigurator → Planner → Operator 三段式 SLA 闭环**：AIConfigurator 离线扫 10K+ TP/EP/DEP 配置 → 选出满足 TTFT/ITL 的 Pareto 前沿 → Planner 在线决策扩缩 → Operator 物化 K8s 资源。这是 1.0 "zero-config DGDR" 的实现基础。`DynamoGraphDeploymentRequest` (`deploy/operator/api/v1beta1/dynamographdeploymentrequest_types.go:29`) 状态机：Pending → Profiling → Ready → Deploying → Deployed。

- **拓扑感知外包给 Grove**：Operator 不做 NVL72/rack/host placement，把 component group 翻译成 `PodCliqueSet` 和 `PodCliqueScalingGroup` 交给 Grove（external scheduler，github.com/ai-dynamo/grove），operator 只读 Grove 的 condition 反传给 DGD status（`deploy/operator/internal/controller/dynamographdeployment_controller.go:444-453`）。

- **Discovery backend 是 trait，不是硬编码**：`Discovery` trait（`lib/runtime/src/discovery/mod.rs:773`）三种实现：`KVStoreDiscovery`（etcd/file/memory）、`KubeDiscoveryClient`（EndpointSlice）、`MockDiscovery`。模型注册有身份冲突检测——不同模型注册到同一 endpoint 会被拒绝（除非两者都是 LoRA adapter）。

- **canary 健康检查 + 自愈再注册**：`HealthCheckManager` (`lib/runtime/src/health_check.rs:55`) 为每个 endpoint 启动独立 task，5s canary_wait_time 后发送 `health_check_payload`，超时则标记 `NotReady` 并触发 re-register。这样 K8s 拉起一个新 pod 后能立即恢复路由。

## 关键组件深入解读

### KV-Aware Router（lib/kv-router）

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

工作流：
1. 请求到达，prompt 用 XXH3（seed=1337，混入 LoRA id）切成定长 PLH 块（典型 128 tokens）。
2. 在 `ConcurrentRadixTree` 里查每个 worker 的最长公共前缀长度，按 device/host/disk 加权得到 overlap 信用。
3. `worker_logit()` (`lib/kv-router/src/scheduling/selector.rs:161-194`) 算每个 worker 的成本。
4. `LocalScheduler` 用 softmax(−logit) + 温度采样选 worker；`SchedulerQueue` 在排队时还会基于最新事件重新评估。
5. KV 事件从所有 worker → NATS JetStream `kv-events` subject → indexer → radix tree（`lib/llm/src/kv_router/indexer/jetstream.rs:1-50`）。
6. 多 router 副本：每个副本订阅 JetStream 作为 durable consumer，互相同步 `AddRequest`/`MarkPrefillCompleted`/`Free` 事件，确保活跃块视图一致。

### KVBM（lib/kvbm-* + lib/llm/src/block_manager）

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

块生命周期（8 阶段，源自 `lib/llm/src/block_manager.md` 状态机）：
1. **Allocate** — 空块从 inactive pool 预留（lib/kvbm-logical/src/pools）
2. **Fill** — Partial → 填满 token 后转 ReadyForScheduling
3. **Schedule** — ReadyForScheduling → Inflight（设计文档状态机）
4. **Compute** — kernel 执行（kvbm-kernels 做 block copy/hashing）
5. **Hash** — 计算 128-bit SequenceHash（dynamo_tokens::PositionalLineageHash）
6. **Register** — Complete → Registered（不可变）→ 进入 OffloadManager
7. **Consolidate** — 跨事件源（ZMQ for vLLM/TRT-LLM、in-process for KVBM）按 SequenceHash 去重；u64 投影后传给 kv-router
8. **Evict/Restore** — weak ref demotion 把块从高层挤下；如 upgrade 失败则记录 evicted（`lib/kvbm-engine/src/offload/pipeline.rs:1185` 日志 "Weak block evicted before transfer"）

NIXL 集成：`lib/llm/src/block_manager/layout/nixl.rs:4-80` 的 `NixlLayout` trait 把 block layouts 注册到 NIXL agent 启用 GPUDirect RDMA；ObjectStorage 用 `nixl_sys::MemType::Object` 把 S3 包装成 NIXL OBJ 后端，G3↔G4 用同一套调度。

### 分布式运行时（lib/runtime）

发布与发现流程：

```
COMPONENT ANNOUNCES:
  1. endpoint.register_endpoint_instance()
       → discovery.register(DiscoverySpec::Endpoint)
       → KVStoreDiscovery::register_internal()
       → kv.put("v1/instances/{ns}/{comp}/{ep}/{id:x}", Instance)

  2. SystemHealth::register_health_check_target()
       → stores (Instance, payload) + notifier channel
       → HealthCheckManager spawns per-endpoint task

CLIENT DISCOVERS:
  1. discovery.list_and_watch(ComponentEndpoints{ns, comp})
       → kv.watch_prefix("v1/instances/{ns}/{comp}/")
       → stream: DiscoveryEvent::Added(DiscoveryInstance)

  2. Client builds router from instance_id → TransportType mapping
       → TCP: endpoint.ip:port
       → NATS: endpoint.subject_prefix

HEALTH CHECK LOOP (canary):
  HealthCheckManager::spawn_endpoint_health_check_task()
  → wait canary_wait_time (5s default)
  → send health_check_payload via request plane
  → on success: SystemHealth::set_endpoint_health_status(Ready)
  → on timeout: mark NotReady, re-register via discovery
```

请求平面：TCP 客户端（`lib/runtime/src/pipeline/network/egress/tcp_client.rs:11`，无锁 LRU 连接池）做高吞吐 RPC；NATS Core（`nats_client.rs:20`）做 pub/sub subject 路由。事件平面：file/mem 默认 ZMQ + MessagePack，etcd/K8s 默认 NATS + JSON。

### K8s Operator（deploy/operator/，Go）

CRD 层次：

```
DynamoGraphDeploymentRequest (DGDR)
    Pending → Profiling → Ready → Deploying → Deployed
    (AIConfigurator sweeps TP/EP/DEP, picks cost-efficient configs meeting SLA)
        │
        ▼
DynamoGraphDeployment (DGD)
    Declarative spec: components (prefill/decode/frontend),
    scheduling constraints, restart policies
        │
        ▼
DynamoComponentDeployment (DCD)
    Pod template, backend framework (sglang/vllm/trtllm),
    sub-component type (prefill/decode/frontend/epp),
    scaling group info, env/resources/probes
```

Reconciler 职责（`deploy/operator/internal/controller/dynamographdeployment_controller.go:79`）：
1. CRD finalizer 生命周期管理（lines 178-186）
2. 多节点部署翻译为 Grove `PodCliqueSet` + `PodCliqueScalingGroup`（lines 429-431）
3. 订阅 Grove PCS topology conditions 反传 DGD status
4. 滚动更新：单节点用 worker-hash drain，多节点委托 Grove
5. EndpointSlice + 发现代理同步
6. RBAC ServiceAccount/ClusterRole 自动创建

## 与同类对比

| 维度 | NVIDIA Dynamo | vLLM 单引擎 | SGLang Router | Ray Serve / KServe |
|------|---------------|-------------|---------------|---------------------|
| 主要场景 | 多 GPU/多节点协调 | 单节点 LLM serving | 单节点请求路由 + cache | 通用模型服务编排 |
| 分离 prefill/decode | ✅ 默认支持 | ❌ | ❌ | 需自己拼 |
| KV-aware 路由 | ✅ radix tree + NATS sync | ❌ | ✅（单进程） | ❌ |
| KV cache 多级 offload | ✅ G1-G4 + NIXL | 部分（CPU offload） | ❌ | ❌ |
| 在飞请求迁移 | ✅ RetryManager | ❌ | ❌ | ❌ |
| SLA 自动扩缩 | ✅ Planner + AIConfigurator | ❌ | ❌ | K8s HPA（指标驱动，无 SLA 反演） |
| K8s 原生 | ✅ CRD + Grove + Gateway plugin | 需自己包 | 需自己包 | ✅（设计目标） |
| backend 支持 | SGLang / vLLM / TRT-LLM | 自己就是 backend | SGLang | 任意（通用） |
| 语言 | Rust + Python + Go | Python（含 C++ kernels） | Python + Rust | Python + Go |

定位差异：Dynamo 不是另一个推理引擎，而是**让多个推理引擎组成集群**的编排层。vLLM/SGLang/TRT-LLM 解决"一个 GPU 怎么跑得快"，Dynamo 解决"一群 GPU 怎么跑得协调"。

## 性能 / 资源开销

**官方宣称（README "Key Results"）：**
- 7× per-GPU throughput（DeepSeek R1，GB200 NVL72 + Dynamo vs B200 baseline，来源 InferenceX）
- 7× faster cold-start（ModelExpress 权重流式，DeepSeek-V3 on H200）
- 2× faster TTFT（KV-aware 路由，Qwen3-Coder 480B，Baseten 基准）
- 80% 更少 SLA 违约 + 5% lower TCO（Planner autoscaling，Alibaba APSARA 2025）
- 750× throughput（DeepSeek-R1 on GB300 NVL72，InferenceXv2）

**架构开销定性：**
- 前端引入额外一跳（HTTP → frontend → worker），但 axum + Rust 路径开销 ≪ tokenize 本身
- KV-aware 路由需 NATS（如果启用），单事件 ~1KB，每块 1 个事件
- KVBM 跨层 offload 在 hot path 上不阻塞（异步 pipeline + weak ref）
- Planner 决策周期默认 load=10s / throughput=60s，对 worker 无侵入

未独立测试，引用官方/第三方基准。

## 安全模型

**信任边界：**

```
[Client] ─TLS?─► [Frontend Ingress]  ◄── 外部边界
                          │
                          ▼
[Frontend] ────TCP/NATS────► [Worker pods]
                          │
                          ▼
                  [etcd / NATS / K8s API]   ◄── 控制平面
                          │
                          ▼
                  [Object Storage (G4)]     ◄── 数据平面
```

- **外部 → frontend**：标准 K8s ingress + TLS（不在 Dynamo 自身代码中）。
- **frontend → worker**：默认明文 TCP / NATS。生产部署假设集群内网，TLS 配置在 NATS/K8s 层做。
- **discovery**：etcd-client 支持 TLS（Cargo.toml 启用 `tls` feature），K8s 用 ServiceAccount + RBAC。
- **KV blocks → object storage**：S3/Azure 凭证来自 K8s secret，NIXL OBJ 后端透传。
- **PyO3 边界**：Python 进程内 Rust 类型暴露通过 `pyo3_async_runtimes::tokio::init_with_runtime` 唯一 runtime，无 GIL 死锁风险但 panic 会跨边界传播。

**已知风险点：**
- 多 router 副本通过 NATS 同步活跃块映射，NATS 中断 → 临时不一致（设计上可接受，过期会被 KV events 修正）。
- LoRA adapter id 混入 hash seed → 不同 adapter 不会被错误命中，但同名不同版本 adapter 需要外部约定。
- 请求迁移在 guided decoding / n>1 模式被禁用——这两类请求在 worker 死亡时返回错误，不会"看起来成功但结果错"。

## Git 洞察

最近 10 commits（截至 2026-05-15，commit 7997117）方向：
- parser 修复（DeepSeek v4、gemma4、glm47）—— 与新模型生态对齐
- DGDR autoscaling 修复 + planner load 优化目标 —— 巩固 1.0 SLA 闭环
- vLLM MooncakeConnector 支持 P/D 解耦 —— 扩展 backend 集成
- SGLang Gemma4/Llama 测试覆盖 —— 稳定性
- 工具调用 parity 测试 —— 确保跨 backend 行为一致

项目重心：**1.0 稳定性 + 模型生态对齐**（DeepSeek-V4 Day-0 recipes 已合入 main）。
