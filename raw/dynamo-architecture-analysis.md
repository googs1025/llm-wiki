# NVIDIA Dynamo 架构与设计思路分析

> 仓库：https://github.com/ai-dynamo/dynamo · 分析日期：2026-09-13 · 版本：HEAD ed64b7d85b71c08f884fc424c205e956eb89c88e
> 分析范围：以 README.md 与 docs/fern/pages 下的官方架构、组件、部署和运维文档为主；没有把未核验的源码细节当作结论。

## 一句话定位

NVIDIA Dynamo 是位于 SGLang、TensorRT-LLM、vLLM 等推理引擎之上的数据中心级推理编排层。它要解决的不是“如何在一张 GPU 上完成一次生成”，而是“如何把跨 GPU、跨节点、跨推理阶段的一组引擎变成一个满足延迟目标、成本可控、能持续扩缩和故障自愈的在线推理服务”。

核心手段是：Frontend 承接兼容 API，KV-aware Router 把缓存局部性和实时负载放进同一个选择决策，Prefill/Decode 分离隔离两类计算，NIXL 传输 KV，Planner 根据 SLA 和流量调整容量，再由 Kubernetes Operator / DGD / DGDR 把意图物化为可运行工作负载。

## 业务问题：它想解决什么

### 问题一：单体推理引擎无法同时优化 prefill 与 decode

Prefill 是计算密集的上下文处理，Decode 是内存和并发敏感的逐 token 生成。长 prompt 的 prefill 会阻塞正在生成的请求；两者混在同一池里时，扩容只能按一个折中配置做。Dynamo 用 xPyD（x 个 prefill、y 个 decode）把两种资源池拆开，使它们可以独立扩缩、使用不同并行度或硬件。

### 问题二：传统负载均衡看不到 KV cache

Round-robin 或只看队列长度的路由，会把一个已经缓存了长前缀的请求送到冷 worker，导致重复 prefill；反过来只追求 cache hit，又可能把所有流量压到同一台机器。Dynamo 的路由把“可复用 KV”转换成成本折扣，同时把活动 prefill、decode 和请求数加入成本，目标是最低预测代价而非最大命中率。

### 问题三：GPU 集群容量配置依赖人工试错

模型、GPU、并行策略、输入输出长度、KV 命中率和 SLA 共同决定最优配置。DGDR 允许用户只描述部署意图，Profiler / AIConfigurator 先生成候选 DGD；部署后的 Planner 再根据实时流量和性能模型调节 prefill/decode 副本，减少拍脑袋配机器和长期过配。

### 问题四：推理服务故障不应直接变成用户失败

GPU worker 可能在请求中途退出、升级或被驱逐。Dynamo 的请求迁移能力让 Frontend 缓存必要的请求状态，在允许的迁移次数内把请求重新发给健康 worker；worker inhibition 和 canary health check 用于减少把请求继续发往已知异常端点。

### 问题五：平台需要标准入口，但推理路径又需要专门决策

有些平台希望 Dynamo Frontend 端到端拥有入口，有些平台要求 Kubernetes Gateway API 负责认证、限流和可观测性。Dynamo 同时支持 Frontend-native 路由和 Gateway API + GAIE EPP 路由；两者复用 KV-aware selection，而不是复制两套路由算法。

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

这是逻辑架构而非单一进程图：Frontend、Router、Planner、worker 和 Operator 可以在本地进程、Kubernetes Pod 或 sidecar 组合中部署。Dynamo 不替换 backend engine，而是通过 runtime、路由、传输和控制面把 engine 连接起来。

## 模块分层

| 层 / 模块 | 文档对应能力 | 主要职责 | 不负责什么 |
|---|---|---|---|
| 业务入口层 | Frontend、Gateway API/GAIE EPP、Standalone Router | OpenAI-compatible API、协议转换、入口策略、tokenize、请求生命周期 | 不实现 Transformer kernel |
| 请求决策层 | KV-aware Router、PrefillRouter | 过滤不合格 worker，按 KV overlap、prefill/decode 负载和活动请求选择目标 | 不拥有 GPU 执行状态 |
| 分布式运行时层 | DistributedRuntime、Namespace、Component、Endpoint | 服务发现、endpoint 注册、请求 RPC、事件发布、生命周期和局部失败抑制 | 不替代 Kubernetes desired-state 控制器 |
| 推理执行层 | Prefill / Decode / Aggregated Worker | 调用 SGLang、vLLM、TRT-LLM 完成推理、KV 管理和 token 生成 | 不决定全局副本数量 |
| KV 与高速传输层 | NIXL、KV event/index、KVBM/相关 offload | P/D 间 KV transfer，必要时把 KV 从 GPU 延伸到 CPU、NVMe、对象存储 | 不把所有 cache 当成强一致数据库 |
| 容量与部署控制层 | DGDR、Profiler、AIConfigurator、Planner、DGD/DCD、Operator、Grove | 预部署配置搜索、在线扩缩、拓扑感知放置、资源和 CRD 生命周期 | 不参与每个 token 的热路径 |
| 观测与可靠性横切层 | Prometheus、OTLP、canary、migration、request rejection | 观测 TTFT/ITL/FPM、分布式 trace、主动健康检查、迁移和优雅下线 | 不保证事件持久化等同于业务数据库 |

三个必须分开的边界：请求平面 ≠ 发现平面 ≠ 事件平面；Profiler ≠ Planner；Operator ≠ Router。前者分别追求低延迟、最终一致和异步广播，后两者分别区分部署前配置搜索/部署后控制，以及 Kubernetes reconcile/在线请求选择。

## 关键数据流

### 数据流一：Frontend-native 在线请求（聚合模式）

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

### 数据流二：分离式 Prefill/Decode 请求

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

P/D 分离不是免费的：它增加了一次 worker 选择和 KV 网络传输。低并发时聚合模式可能更划算；长 prompt 与 decode 竞争严重、或需要独立扩缩时，分离模式的延迟隔离价值更大。

### 数据流三：KV-aware 路由反馈环

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

抽象成本可以写成：

```text
adjusted_prefill = max(raw_prefill - overlap_credit, 0)
projected_cost   = prefill_weight * adjusted_prefill
                 + projected_decode_blocks
                 + active_request_penalty
```

具体权重和支持的 cache 层由配置与 backend 能力决定；不要把这个公式理解成跨版本稳定的公共 API。

### 数据流四：DGDR 到运行中的 DGD

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

### 数据流五：Planner 在线扩缩控制回路

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

Planner 有两个时间尺度：throughput loop 用较长窗口预测持续需求并提供容量下界；load loop 更快地纠正当前 SLA 压力。共享状态包括 worker inventory、性能模型、throughput lower bound、KV hit rate、speculative accept length 和 GPU budget。

### 数据流六：Gateway API 路由拓扑

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

另一种拓扑是 `Client → Dynamo Frontend → Router → workers`。两种入口共享 backend、P/D、KV-aware routing 能力；差异在于入口治理由谁负责。

### 数据流七：故障迁移与优雅下线

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

迁移默认关闭（`migration-limit=0`）；是否能迁移取决于请求状态和 backend 语义。优雅关闭则先停止接收新流量、排空活动请求，再从 discovery 注销。

### 数据流八：可观测性信号

```
Dynamo processes
  ├─ pull /metrics ─────────────► Prometheus ───────► Grafana
  ├─ OTLP traces/logs ──────────► OTel Collector ───► Tempo / Loki
  ├─ FPM event publication ─────► event plane
  │                                └─ bounded trace queue → JSONL(.gz)
  └─ request trace rows ─────────► JSONL / NATS / OTLP / stderr sinks
```

观测路径是旁路的：有界队列背压时可以丢弃 FPM trace，不能阻塞推理请求或事件发布。这说明 FPM 文件更像分析材料而不是强一致审计日志。

## 设计决策与哲学

- **把推理引擎当作可替换执行器**：Dynamo 提供 orchestration，而 SGLang/vLLM/TRT-LLM 保留 scheduler、kernel、sampling 和 GPU execution 的专业实现。
- **把 KV 从执行内部状态提升为调度信号**：prefix overlap 进入 worker selection，KV transfer 进入 P/D 协议，KV offload 进入容量设计；缓存局部性成为集群级资源。
- **把在线控制拆成预测环与反应环**：throughput loop 防止持续需求到来时扩容太晚，load loop 处理突发和模型误差；两者通过 lower bound 与约束合并。
- **把配置搜索前置为声明式意图**：DGDR 不要求用户提前知道每个 worker 的并行配置；Profiler 生成可审查的 DGD，保留 `autoApply=false` 作为治理闸门。
- **把低延迟和最终一致放在不同平面**：请求选择不依赖 Operator 每次 reconcile；worker discovery 和事件传播可以异步更新，局部 inhibition 用于缩短故障收敛窗口。
- **把入口治理与 serving selection 解耦**：Dynamo Frontend 和 GAIE EPP 都能承载相同的 KV-aware selection。
- **用 sidecar 隔离 backend 依赖**：Dynamo sidecar 负责注册、健康和事件转发，engine 负责原生 gRPC、batching、sampling、KV 和 GPU 执行。
- **观测不能反向拖慢热路径**：metrics 采用 pull，trace/log 采用 push，FPM persistence 采用 bounded nonblocking queue。

## 关键组件深入解读

### Frontend / Router：把请求转换成可执行的 worker 选择

Frontend 是 API gateway，不只是反向代理：它负责协议兼容、请求预处理、流式响应和请求生命周期。预处理后的请求交给 Router；Router 的核心输入不是单一队列长度，而是 prompt token 对现有 KV 的重叠程度、worker 当前的 prefill/decode 活动量以及请求数量。选择完成后，普通模式直接 dispatch；P/D 模式则先选 prefill，再根据返回的 `disaggregated_params` 选择 decode 并协调 KV transfer。

文档把“路由发生在哪里”和“路由算法是什么”分开：Frontend-native、GAIE EPP、Standalone Router 都可以作为 selection host。这样平台入口可以变化，KV-aware cost model 不必变化。

### Planner：把性能模型变成容量动作

Planner 先从 frontend/router 与 worker 获取 request count、ISL、OSL、KV hit rate、speculative accept length、queue 和 FPM 等观察值；throughput 分支预测下一窗口的请求形状，load 分支根据实时 SLA 压力做快速修正；提案再经过 reconcile/constraint，最后通过 connector 输出 prefill/decode 副本目标。

这套设计把“流量预测错误”“KV 命中率变化”“scale action 尚未完成”等现实因素放进控制器状态，而不是假设一个静态的每副本 QPS。代价是控制逻辑更复杂，需要 Prometheus、性能模型和 Kubernetes 执行器共同可靠。

### Operator / DGDR / DGD：把想要什么变成怎么跑

DGDR 表达 model、hardware、workload、latency target 和可选功能；Profiler 负责部署前的候选配置评估，生成完整 DGD；DGD 再由 Operator 物化成各组件工作负载。DGD 是最终可审查、可手工修改的部署描述，DGDR 是帮助生成它的意图 API。这个双层模型既支持 zero-config，也不剥夺高级用户对拓扑和 Kubernetes 配置的控制。

### KVBM / KV state：容量层与路由层的连接

KV cache 是跨 GPU、CPU、NVMe 和对象存储的资源问题；KVBM/相关 offload 能力负责存放与迁移，KV index/event 能力负责让 Router 知道哪些 worker 或层级可能复用。P/D transfer 是把 KV 送到另一个 GPU，offload 是把 KV 放到更便宜的层，二者都依赖高效传输，但不应混淆为同一个控制器。

## 与同类对比

| 维度 | Dynamo | vLLM / SGLang | llm-d / Gateway API serving | KServe / OME 类 Operator |
|---|---|---|---|---|
| 核心边界 | engine 之上的数据中心推理编排 | 单机/多 GPU 推理 engine | K8s inference endpoint、router、pool 生态 | 声明式模型服务生命周期 |
| P/D 分离 | 一等能力，PrefillRouter + NIXL | backend 能力或单独部署 | 通过 serving stack 与 KV/router 组合 | 通常依赖 runtime/扩展集成 |
| 路由信号 | KV overlap + prefill/decode load | 主要是 engine 内部调度 | endpoint、KV、健康、策略信号 | Service/endpoint 与模型状态 |
| 自动配置 | DGDR → Profiler → DGD | 用户或 recipe 配置 | 依赖平台和组件组合 | CRD/operator 生成和 reconcile |
| 在线扩缩 | Planner 双时间尺度 SLA 控制 | 通常不负责集群级扩缩 | autoscaling 组件或 K8s 控制器 | HPA/KEDA/operator 体系 |
| 容错重点 | 请求迁移、worker inhibition、canary | engine 进程级恢复 | endpoint failover / gateway policy | Pod/Deployment 生命周期 |
| 适用场景 | 长上下文、多节点、P/D、强 SLA、GPU 成本优化 | 单模型单机或 engine 调优 | K8s 平台统一路由与多模型入口 | 标准模型服务 API 与生命周期 |

## 性能 / 资源开销

- README 给出若干项目方引用的结果：KV-aware routing 在特定 benchmark 中声称可带来 2x TTFT 改善，Planner 场景声称减少 SLA breach；这是上下文相关的 benchmark，不是所有模型和硬件的保证。
- P/D 分离增加 KV transfer 和跨 worker 协调；收益取决于 prompt 长度、并发度、互联带宽、backend 实现和 decode KV 容量。
- `rapid` auto deployment 依赖估算、成本低；`thorough` 使用真实 GPU 候选部署和 benchmark，文档给出的典型耗时为 2–4 小时。
- 观测 persistence 使用有界队列，系统宁愿丢弃滞后的 trace，也不让推理热路径等待磁盘或远端 sink。
- 具体副本数、GPU 利用率、TTFT/ITL 和缓存命中收益必须通过目标模型、输入输出分布和硬件互联实测；本次未运行 GPU benchmark。

## 安全模型与运维边界

- Gateway API 拓扑适合把认证、限流和边缘治理放在平台入口；Frontend-native 拓扑则把入口和 serving 逻辑集中在 Dynamo。
- discovery 中的 endpoint 状态不是业务授权模型；生产环境仍需独立处理身份认证、命名空间隔离、网络策略和 secret 注入。
- worker health check 分为被动 HTTP 状态与主动 canary；主动 canary 会实际走 inference endpoint，应评估 payload、成本和数据敏感性。
- 请求迁移会重放请求状态，必须明确哪些请求可迁移、迁移次数、token 状态缓存和重复副作用边界；工具调用/外部副作用型请求尤其需要业务幂等设计。
- KVBM 的远端对象存储会扩大数据驻留边界；KV 内容可能包含用户 prompt 的派生状态，应配置访问控制、加密、生命周期和租户隔离。

## 文档证据与局限

主要证据来自当前仓库的 `README.md`、system-architecture、disaggregated-serving、kv-aware-routing、router-design、planner-design、auto-deployment、gateway-api、sidecar-backends、observability-architecture 与 request-migration 文档。

本页是文档驱动架构解释，不是逐符号源码审计。代码目录会快速演进，尤其是 backend support、KVBM offload、Gateway EPP 和 Planner 配置；采用 Dynamo 时应再核对目标 release 的 feature matrix、backend 文档、CRD reference 和部署 recipe。
