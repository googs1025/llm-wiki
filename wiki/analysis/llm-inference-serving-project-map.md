---
title: LLM Inference / Serving 项目地图
tags: [llm-inference, llm-serving, kv-cache, project-map, ai-infra]
date: 2026-09-22
sources: [src-dynamo-architecture, src-sglang-architecture, src-skypilot-architecture, src-k8s-gpu-device-plugins-stars, src-llm-d-architecture, src-llm-d-router-architecture, src-llm-d-kv-cache-architecture, src-llm-d-batch-gateway-architecture, src-llm-d-benchmark-architecture, src-llm-d-workload-variant-autoscaler-architecture, src-llm-d-inference-sim-architecture, src-vllm-architecture, src-aibrix-architecture, src-k8s-serving-stack-comparison]
related: ["[[dynamo]]", "[[vllm]]", "[[sglang]]", "[[llm-d]]", "[[llm-d-router]]", "[[llm-d-kv-cache]]", "[[llm-d-batch-gateway]]", "[[llm-d-benchmark]]", "[[llm-d-workload-variant-autoscaler]]", "[[llm-d-inference-sim]]", "[[batch-inference]]", "[[llm-inference]]", "[[paged-attention]]", "[[radix-attention]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]", "[[kubernetes]]", "[[llm-d-kubernetes-sigs-candidate-map]]", "[[aibrix]]", "[[inference-routing]]", "[[model-serving-operator]]"]
---

# LLM Inference / Serving 项目地图

## 当前上游核验（2026-09-22）

本页把官方仓库/文档的当前观察与既有 raw-backed Source 摘要分开。Source 摘要仍保存其分析时点；下表用于判断本次横向地图是否需要调整。

| 项目 | 核验版本 | 当前稳定职责 | 本次处理 |
|------|----------|--------------|----------|
| [[vllm]] | HEAD [`d50723df04f7`](https://github.com/vllm-project/vllm/commit/d50723df04f7) | engine scheduler、model execution、local KV | 保留内部图，补外部边界 |
| [[sglang]] | HEAD [`04c0913434c4`](https://github.com/sgl-project/sglang/commit/04c0913434c4) | engine/runtime、RadixCache、distributed/P-D integration | 保留内部图，补集成边界 |
| [[dynamo]] | HEAD [`f36d2fab37fd`](https://github.com/ai-dynamo/dynamo/commit/f36d2fab37fd) | distributed request/control/state runtime、routing、KV transfer、planner | 更新平台层关系 |
| [[llm-d]] | HEAD [`1e9a86a3a9da`](https://github.com/llm-d/llm-d/commit/1e9a86a3a9da) | Proxy/EPP、InferencePool、Model Server 与 routing signals | 更新 Gateway/EPP 热路径 |
| [[aibrix]] | HEAD [`96056b47f158`](https://github.com/vllm-project/aibrix/commit/96056b47f158) | K8s routing、autoscaling、adapter/model lifecycle、KV/multi-role orchestration | 纳入核心比较 |

> [!note] 证据边界
> 当前职责来自本次官方仓库与文档核验；内部调用路径仍以对应 Source 页面为准。

官方架构/文档入口：[vLLM](https://docs.vllm.ai/en/latest/design/arch_overview/)、[SGLang](https://docs.sglang.ai/)、[Dynamo](https://docs.nvidia.com/dynamo/dev/knowledge-base/concepts/architecture)、[llm-d](https://llm-d.ai/docs/dev/architecture)、[AIBrix](https://aibrix.readthedocs.io/latest/getting_started/overview.html)。

这页是 M4 的 L1 职责地图，用 D1–D5 连接入口、选点、推理引擎、KV 状态和部署控制。项目内部的完整调用图见各 Source；组合选型见 [[llm-serving-engine-selection-map]]。实线箭头只表示同步请求或数据传输，带标签的虚线箭头 `- - signal / control - ->` 表示异步观察或控制；控制器不串入逐请求执行链。D5 单独采用故障场景的因果记法，见该节说明。

## D1 · 模块边界图

```text
Application / Agent / Batch Client
                  │ OpenAI-compatible API
                  ▼
┌──────────────── Gateway / Traffic ────────────────┐
│ Gateway API / HTTPRoute / Proxy / auth / policy    │
└───────────────────────┬───────────────────────────┘
                        │ endpoint decision
                        ▼
┌──────────────── Routing / Serving Platform ───────┐
│ EPP / Router / InferencePool / discovery           │
│ Dynamo / llm-d / AIBrix runtime integration        │
└──────────────┬───────────────────────┬─────────────┘
               │ aggregated            │ disaggregated
               ▼                       ▼
┌──────────────── Inference Engines ────────────────┐
│ vLLM / SGLang / TensorRT-LLM                       │
│ scheduler → model runner → attention → local KV    │
└───────────────────────┬───────────────────────────┘
                        │ allocate / transfer / offload
                        ▼
┌──────────────── Compute and State ────────────────┐
│ GPU / HBM / CPU / SSD / object store / KV index    │
└───────────────────────────────────────────────────┘

control plane beside the request path:
┌───────────────────────────────────────────────────┐
│ CRD / deployment / planner / autoscaler / operator │
│ Dynamo / llm-d ecosystem / AIBrix control parts    │
└───────────────────────────────────────────────────┘
workers / runtime - - metrics · KV events · readiness - -> control plane
Model / SLO intent - - desired state - -> control plane
control plane - - config / replica targets - -> runtime / worker pools
```

这是职责地图，不表示每个部署都包含每个方框。[[vllm]] / [[sglang]] 是推理引擎；[[dynamo]]、[[llm-d]]、[[aibrix]] 覆盖的外围 runtime、路由和控制面范围不同，不能把三者当成同一种 engine。Gateway API、HTTPRoute、InferencePool 是配置/发现契约，实际接收请求的是 Proxy/Frontend；KV index 保存位置线索，不等同于 KV 数据存储。D1 表示依赖边界，实际请求和异步循环分别展开在 D2、D3。

## D2 · 在线请求热路径

```text
aggregated:
Client → Gateway/Frontend → Router/EPP → Engine Scheduler → Model Runner → stream

disaggregated:
Client → Gateway/Frontend → Router/EPP
                              │
                              ├→ Prefill worker ── KV metadata/data ─┐
                              │                                     ▼
                              └───────────────────────────────→ Decode worker → stream
```

连接处理、endpoint 选择、token 执行是三项不同职责。Gateway/Frontend 接收连接、执行入口策略并转发流；Router/EPP 根据模型、负载和 KV locality 选 worker；引擎 Scheduler 组成 batch，Model Runner 执行模型。图中 Router/EPP 是逻辑选点步骤：在 [llm-d 的 Proxy/EPP 结构](https://llm-d.ai/docs/dev/architecture)和 [AIBrix 的 ext_proc 结构](https://aibrix.readthedocs.io/latest/getting_started/overview.html)中，Proxy 咨询选点服务后直接向 engine 转发，请求流不必穿过 EPP 进程。

P/D 模式还需要 [[disaggregated-serving|KV-transfer 契约]]：请求身份、KV 布局/传输元数据、接收完成条件、超时和取消必须由 backend 组合共同定义。图中的双分支表示角色协作，不规定统一的触发顺序；具体由谁发起 prefill、谁等待 KV、谁返回 stream，要查该部署的 engine/connector/router 配置。

## D3 · 扩缩与部署控制循环

```text
Model / SLO / topology intent
             ┆ desired state
             ▼
CRD / Deployment / InferencePool / platform config
             ┆ watch / reconcile
             ▼
Operator / Planner / Autoscaler
             ┆ config / replica targets
             ▼
worker pools / engine pods
  - - metrics / queue / KV / readiness - -> Operator / Planner / Autoscaler
```

这是后台收敛循环，竖向的 `┆` 与横向的 `- -` 都表示异步观察/控制，副本目标并非同步请求调用。[[dynamo]] 的 Planner 与 Kubernetes Operator 可以分别承担容量决策和部署执行；[[llm-d]] 用 InferencePool 表达后端集合，部署和扩缩由配套的 Kubernetes 组件承担；[[aibrix]] 的 controllers 管理模型/adapter、角色组和副本，AI Runtime 协助 pod 内的模型生命周期。它们的 API、运行时依赖和控制对象不同，接入时要确认谁拥有副本目标，避免两个控制器竞争写入。见 [[model-serving-operator]]、[[src-dynamo-architecture]]、[[src-llm-d-architecture]]、[[src-aibrix-architecture]]。

> [!warning] Conflict
> 2026-09-22 的 [llm-d dev 架构文档](https://llm-d.ai/docs/dev/architecture#autoscaling)已将 Workload Variant Autoscaler 标为 deprecated，并描述 EPP metrics → KEDA Prometheus scaler → HPA 的扩缩路径。[[src-llm-d-workload-variant-autoscaler-architecture]] 与 [[llm-d-workload-variant-autoscaler]] 保存的是较早的 WVA 设计；本页将其作为历史设计参考。Source 保留原分析时点，版本迁移与实际发布适配仍需单独核验。

## D4 · KV 状态生命周期

```text
prompt tokens
     │ prefill
     ▼
local KV blocks - - publish events/index - -> routing locality signal
     │
     ├── direct P→D transfer ─────────────→ decode-local KV
     ├── offload → CPU / SSD / remote tier → recall/promote
     └── pressure / expiry / model change ─→ evict or recompute
```

引擎拥有 local KV 的表示、分配和有效性判断，包括 block/page、prefix identity 与模型布局约束。外围层可以索引、路由、传输和 offload：[[llm-d-kv-cache]] 的 locality signal 帮助选点，[[dynamo]] 的传输/缓存组件和 [[aibrix]] 的 KV 能力则按具体集成参与跨 worker 或跨存储层的复用。路由索引里的“可能命中”不能代替引擎对 KV 的验证。

直接 P→D 传输、分层 offload 和事件发布是不同接口，不要求同时启用。CPU/SSD/remote tier 是候选层级；可用介质、格式兼容性、缓存失效和回收策略取决于版本及 backend。见 [[kv-cache-offload]]、[[paged-attention]]、[[radix-attention]]。

## D5 · 故障与降级边界

本节的 `failure → conditional response` 箭头表示“故障发生后，按契约采取条件响应”的因果场景，不表示同步调用链；其中涉及的发现、摘除和扩缩仍遵循异步控制语义。

```text
EPP/router unavailable → fail open / fail close / reject according to gateway policy
worker not ready        → discovery removes/inhibits endpoint → choose another worker
prefill/decode failure  → cancel, retry, or recompute according to backend contract
KV index stale          → lower hit quality; engine correctness remains independent
autoscaler lag          → queue/load shedding protects the request path
```

这张图列的是部署时需要明确的故障契约，不表示所有项目都实现每一种 fallback。EPP 故障能否 fail open 取决于 Gateway 配置及是否存在合法的备用路由；worker 摘除依赖 readiness/discovery 的传播，新选点也可能遇到旧状态。P/D 已输出 token 后是否可重试或迁移，必须检查 backend 对流、采样状态和取消的支持，不能假定透明恢复。

KV 索引只作为优化信号且引擎独立验证缓存身份时，索引过期通常影响命中率与排队质量；这不代表 KV 数据损坏或传输失败也无害。扩缩存在启动延迟，只有配置了有界队列、admission 或 load shedding，热路径才有相应保护。故障注入应分别覆盖 Gateway、worker、KV 通道和控制器，见 [[inference-routing]]。

## 一句话分层

| 项目 / 概念 | 一句话定位 | 抽象层 |
|-------------|------------|--------|
| [[vllm]] | 推理引擎基线，[[paged-attention]] 把 KV cache 按 block 管理，调度和模型执行在 engine 内完成 | 推理引擎，可跨设备/节点并行 |
| [[sglang]] | 以 [[radix-attention]]、Scheduler/ModelRunner 和执行优化组织 serving runtime | 推理引擎，可跨设备/节点并行 |
| [[dynamo]] | NVIDIA 数据中心级 LLM 推理编排层，把 vLLM/SGLang/TRT-LLM 组成协调集群 | 多节点 serving 编排 |
| [[llm-d]] | CNCF Sandbox 分布式 LLM inference serving stack，围绕 Router/EPP、InferencePool、KV/P-D/autoscaling 组织 | K8s serving control plane |
| [[aibrix]] | 围绕 engine fleet 提供路由、扩缩、model/adapter lifecycle、KV 和多角色编排 | K8s serving/control plane |
| [[llm-d-router]] | llm-d 智能入口层，用 EPP filters/scorers/scrapers 对 InferencePool endpoints 做选择 | Endpoint picking / routing |
| [[llm-d-kv-cache]] | llm-d KV locality index / scorer，把 vLLM/SGLang KV events 转成 cache-hit routing signal | KV-aware routing signal |
| [[llm-d-batch-gateway]] | OpenAI Batch API / 离线推理控制面，把 batch job/file/queue/output 接到下游 llm-d Router/model endpoint | Batch serving control plane |
| [[llm-d-benchmark]] | llm-d 实验编排器，把 scenario/spec、K8s lifecycle、harness 和 result workspace 串起来 | Benchmark lifecycle |
| [[llm-d-workload-variant-autoscaler]] | 已摄入的多 variant 全局 allocation 设计；当前 dev 文档已标 deprecated，见 D3 冲突说明 | 历史 autoscaling 设计 |
| [[llm-d-inference-sim]] | 无 GPU vLLM 行为模拟器，用 OpenAI/vLLM API、KV events、latency/failure/metrics 验证控制面 | Simulator / test double |
| [[src-skypilot-architecture|SkyPilot]] | AI/ML 多云算力控制平面，负责跨云/K8s/Slurm 选择资源、failover、managed jobs/serve | 算力控制平面 |
| [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | device plugin / GPU Operator / DRA / CDI / DCGM / GPU sharing | GPU 资源基础设施 |

## 横向对比

按主要职责分组；同一项目可以跨多个边界，表中不把它们视为可直接互换的 engine。

| 层 | 项目 | 核心抽象与职责 | KV / P-D 边界 | 采用代价与下一步验证 |
|----|------|----------------|--------------|----------------------|
| 推理引擎 | [[vllm]] | EngineCore / Scheduler / ModelRunner，batch 与模型执行 | local KV block；prefix cache、connector 随配置启用 | 用目标模型/硬件验证吞吐、TTFT/ITL 和 connector；block 大小不能写成统一常量 |
| 推理引擎 | [[sglang]] | Scheduler / ModelRunner / RadixCache，执行优化与并行 | prefix reuse、HiCache、P/D integration 依 backend 而定 | 验证投机解码、chunking、并行与传输的特性组合 |
| 分布式 runtime | [[dynamo]] | Frontend / Router / discovery / worker graph，另有 Planner/Operator | 可组织 aggregated 或 P/D workers，集成 KV events/transfer/offload | 需要运维 runtime 与控制组件；逐项验证 backend 支持和故障契约 |
| K8s serving/control plane | [[llm-d]] | Proxy + EPP / InferencePool / Model Server | 以事件、scorer 和可选 P/D 路径连接 engine | 需要 Gateway API/GAIE 兼容性；扩缩组件按当前版本验证，见 D3 |
| K8s serving/control plane | [[aibrix]] | Gateway plugins / controllers / AI Runtime，管理 engine fleet | KV、角色编排和 model/adapter lifecycle 按需组合 | 验证引擎适配、CRD 生命周期、路由策略与副本归属 |
| 基础设施/算力控制 | [[src-skypilot-architecture|SkyPilot]] | Task/Dag/Resources + Optimizer，资源选择与作业/服务生命周期 | 部署引擎和服务，不定义 local KV 布局 | 需对接云/K8s/Slurm 凭据、配额与容量；不解决模型执行性能 |
| 基础设施/设备 | [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | DevicePlugin / DRA / CDI / Operator / observability | 提供设备、拓扑和健康信号 | 设备分配、隔离和驱动兼容性需独立验证 |

## 架构交叉矩阵

| 交叉模式 | 采用项目 | 工程含义 |
|----------|----------|----------|
| KV cache 显式管理 | [[vllm]], [[sglang]], [[dynamo]], [[llm-d-kv-cache]], [[aibrix]] | 区分 engine 内 KV 分配、外部索引与存储层；职责见 D4 |
| 前缀复用 | [[vllm]], [[sglang]], [[dynamo]] | system prompt、few-shot、agent template 可共享，路由/调度要感知 prefix |
| Prefill/Decode 分离 | [[vllm]], [[sglang]], [[dynamo]], [[llm-d]], [[aibrix]] | engine connector 与平台路由协作；收益取决于 workload、带宽和传输契约 |
| 多级 KV offload / locality signal | [[dynamo]], [[kv-cache-offload]], [[llm-d-kv-cache]] | GPU 显存不够时，把 KV 分层；路由时则把 KV locality 变成 endpoint score |
| Speculative decoding | [[sglang]], [[vllm]] | 用 draft/target 或 ngram 等方法降低 decode latency |
| K8s 控制面 | [[dynamo]], [[llm-d]], [[aibrix]], [[src-skypilot-architecture|SkyPilot]] | 不同系统分别收敛 serving graph、engine fleet 或底层算力，见 D3 |
| Batch / benchmark / simulator | [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-inference-sim]] | serving 选型需要异步任务、可复现实验和低成本控制面替身 |
| Variant allocation（历史设计） | [[llm-d-workload-variant-autoscaler]] | 可研究多硬件/多角色的容量分配；当前采用路径须考虑 D3 的 deprecated 状态 |
| 资源经济 | [[src-skypilot-architecture|SkyPilot]], [[dynamo]] Planner, [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | 不只是跑得快，还要按 SLA、成本和容量调度 |

## 核心设计轴

### 1. KV cache：从内存优化到系统接口

LLM serving 的很多架构分歧都来自 KV cache：

- [[vllm]] 的 [[paged-attention]] 把 KV cache 切成 block，解决传统最大 seq_len 预分配浪费。
- [[sglang]] 的 [[radix-attention]] 把前缀共享做到 token 级，适合 agent template、few-shot、tree-of-thought 这类大量共享前缀场景。
- [[dynamo]] 在引擎外连接 KV events/index、传输与可选缓存层；[[src-dynamo-architecture]] 中的 KVBM/SequenceHash 细节属于该分析版本，部署时需核对 backend 集成。

结论：KV cache 已经从“GPU 内部 buffer”变成 serving 系统的一等资源。后续的路由、扩缩、迁移、offload、GPU sharing 都需要知道 KV 的存在。

### 2. 引擎执行和集群编排是两层问题

[[vllm]] / [[sglang]] 负责引擎内执行，实例本身也可使用跨设备/节点并行；[[dynamo]] 组织实例间 runtime，[[llm-d]] / [[aibrix]] 则从 Kubernetes serving 与 fleet 管理边界补齐路由和控制能力。

```text
engine execution: tokenizer → scheduler → model runner → attention / local KV
cluster requests: frontend → route → aggregated or P/D workers → stream
cluster control:  metrics - - -> capacity decision - - -> deployment / replicas
```

把这两层混淆会导致选型误判。vLLM/SGLang 的强项是内核执行与 batching；Dynamo 的强项是多节点协调、KV-aware routing、P/D disaggregation 和 SLA planner。SkyPilot 再往上，解决集群/云在哪里、怎么拉起、失败怎么换区/换云。

### 3. P/D 分离改变了 GPU 池形态

Prefill 和 decode 的资源特征不同：

- prefill：长 prompt，计算密集，吞吐更像大矩阵计算。
- decode：逐 token，低 batch 情况下内存带宽和 KV 访问更敏感。

[[disaggregated-serving]] 把两者拆开后，系统需要额外解决：

- prefill worker 和 decode worker 如何匹配。
- KV 如何从 prefill 传到 decode。
- decode worker 是否已有相关 prefix KV。
- prefill/decode 分别按什么指标扩缩。
- 请求迁移时哪些状态可重建，哪些不可复制。

[Dynamo 官方架构](https://docs.nvidia.com/dynamo/dev/knowledge-base/concepts/architecture)覆盖 aggregated 与 disaggregated worker 组织；P/D 是需要选择的部署模式。[[sglang]] / [[vllm]] 的传输接口和 [[llm-d]] / [[aibrix]] 的外围编排应按 backend 组合核验，不能用项目名推断默认启用或完整兼容。

### 4. 路由不再只是负载均衡

传统 HTTP 负载均衡按连接数、延迟或权重分发。LLM serving 的路由还要考虑：

- 哪个 worker 已有 prompt prefix KV。
- prefill 队列和 decode 队列哪个更忙。
- KV 在 GPU、CPU、磁盘还是远端对象存储。
- 当前请求是否可迁移。
- LoRA/model adapter 是否匹配。

[[src-dynamo-architecture]] 描述的 KV-aware routing 用 prefix overlap 与负载估计平衡复用和排队；cost/softmax 等策略细节应随版本核验。[[llm-d-router]] 和 [[aibrix]] 也将 engine 状态纳入选点，但信号格式、策略插件和失败行为不同。见 [[inference-routing]]。

### 5. GPU 资源层正在变成 serving 架构的一部分

K8s GPU 资源层不再只是 “NVIDIA device plugin 把 `/dev/nvidia0` 暴露给 Pod”。

当前材料已经显示出完整栈：

- device plugin / GPU Operator / container toolkit。
- GPU Feature Discovery / DCGM exporter / GPUd。
- GPU sharing / vGPU：HAMi、vgpu-scheduler、gpushare、Volcano vGPU。
- DRA / CDI：下一代设备声明和分配。
- KV cache 资源化：kvcached 这类项目把 KV 也推向可调度资源。

当 serving 系统进入 P/D 分离、多级 KV、GPU sharing 后，K8s 的设备 API、DRA/CDI、GPU health 和调度策略会直接影响模型服务设计。

## 项目工程剖面

### [[vllm]]：推理引擎基线和 PagedAttention

[[vllm]] 以 Scheduler、ModelRunner 和 local KV 管理承接 token 执行。PagedAttention 的 block table 让显存按需分配；内部调用图见 [[src-vllm-architecture]]，当前职责对应上方官方核验。

适合借鉴的点：

- 把 KV cache 从连续大 buffer 变成可管理 block。
- 把 OpenAI-compatible serving 做成事实入口。
- 生态兼容和模型覆盖优先。

主要局限：

- KV page/block 粒度和 prefix reuse 需要按模型、attention/backend 与配置核验。
- 引擎的分布式执行或 KV connector 不等于完整的 Gateway、fleet lifecycle 和容量控制。
- 集群级 SLA 与跨副本路由需明确外部组件归属；offload 可以有 engine 侧接口及外围存储实现。

### [[sglang]]：执行路径与 KV 复用

[[src-sglang-architecture]] 在 2026-09-14 的分析版本中展示了以下结构；进程数、backend 数和特性兼容性随版本与部署方式变化：

- HTTP / TokenizerManager / Scheduler / DetokenizerManager 的职责分离。
- RadixCache token 级 KV 复用。
- EXTEND / DECODE / MIXED 等 forward mode。
- 可选 attention backend 与融合 kernel。
- speculative decoding 的 draft/verify 路径。
- P/D KV transfer backend 集成。
- OpenAI / Anthropic / Ollama / gRPC / Engine API。

它提供了研究执行优化和缓存复用的具体路径；代价是特性组合约束复杂。speculative、chunked prefill、disagg 能否组合，需要目标版本、模型和硬件上的验证。

### [[dynamo]]：数据中心级 serving 编排

[[dynamo]] 把 engine backend 接入分布式 serving runtime。请求经 Frontend/Router 到 aggregated 或 P/D workers；KV events/index 为路由提供异步信号，Planner/Operator 在请求链外调整容量。完整内部图见 [[src-dynamo-architecture]]，跨项目职责见 D1–D4。

它的工程难点集中在三平面解耦：

- request plane：低延迟请求路径。
- control plane：discovery、desired state、部署与容量收敛。
- storage/event plane：KV visibility、事件传播与可选 offload。

它把 [[vllm]] / [[sglang]] / TensorRT-LLM 当 backend，围绕多节点路由、KV transfer 和容量管理组织协作。传输、事件后端、缓存层级及请求迁移能力都需按所选 backend 和配置确认，不能从 runtime 存在推断所有能力已启用。

### [[llm-d]]：Gateway/EPP 与 Kubernetes serving 组合

[[llm-d]] 以 Proxy、EPP、InferencePool、Model Server 为主要边界：Proxy 承接连接，EPP 选 endpoint，engine 执行模型。KV、P/D、batch、benchmark 和扩缩是围绕这些边界组合的能力，具体采用路径随版本演进。当前扩缩状态见 D3；历史与内部架构见 [[src-llm-d-architecture]]、[[src-llm-d-router-architecture]]，对比见 [[src-k8s-serving-stack-comparison]]。

### [[aibrix]]：engine fleet 的路由与生命周期管理

[[aibrix]] 围绕 engine fleet 组合 Gateway routing、controllers、autoscaling 与 AI Runtime，并提供 model/adapter、KV 和多角色编排能力。它的控制资源与 pod 内适配职责有别于 llm-d 的 InferencePool/EPP 边界，也有别于 Dynamo 的分布式 runtime。接入前应明确模型/adapter 生命周期、副本写入权和引擎适配接口。见 [[src-aibrix-architecture]]、[[src-k8s-serving-stack-comparison]]。

### [[src-skypilot-architecture|SkyPilot]]：算力控制面而不是 serving engine

[[src-skypilot-architecture|SkyPilot]] 不优化 attention kernel，也不管理 KV cache。它解决的是：在 Kubernetes、Slurm、公有云、on-prem 之间怎么选择资源、启动集群、failover、运行 managed jobs / serve。

它在 serving 地图里的位置更高：

```
YAML / SDK intent
        ↓
API server request queue
        ↓
Optimizer
        ↓
CloudVmRayBackend / provider
        ↓
cluster / managed job / serve
```

对 LLM serving 来说，SkyPilot 适合承接“服务应该部署在哪、容量不足如何换 region/cloud、成本如何比较”的问题。它不替代 Dynamo/SGLang/vLLM，而是它们上方的资源选择和执行控制面。

### [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]]：设备层正在上移

K8s GPU & Device Plugins star list 已经足够说明：GPU 资源层正在从 device plugin 扩展为完整平台。

关键分层：

- runtime/container integration：NVIDIA container toolkit、CDI、NVML bindings。
- Kubernetes exposure：NVIDIA device plugin、GPU Operator、GPU Feature Discovery。
- sharing/virtualization：HAMi、vgpu-scheduler、Volcano vGPU、DRA。
- observability/diagnostics：DCGM exporter、GPUd、fake GPU。
- workload layer：TensorRT、KV cache virtualization。

对于 serving 系统，这层决定了 GPU 能不能细粒度共享、能不能按拓扑调度、能不能自动诊断、能不能把 KV cache/显存压力暴露给调度器。

## 核心难点

### 1. 吞吐和延迟不是同一个优化目标

Continuous batching 提高吞吐，但可能增加单请求排队延迟；speculative decoding 降低 decode latency，但引入 draft model 和验证开销；P/D 分离提高资源利用，但多一次 KV transfer。Serving 系统必须按 workload profile 调优，而不是追求单一指标。

### 2. KV 复用和负载均衡天然冲突

把请求发给已有 prefix KV 的 worker 能省 prefill，但那个 worker 可能很忙。把请求发给空闲 worker 延迟可能更低，但要重新 prefill。[[dynamo]]、[[llm-d-router]] 和 [[aibrix]] 的策略研究都需要在实测中比较命中收益与排队代价。

### 3. P/D 分离引入状态转移问题

Prefill 输出的 KV 必须被 decode 节点可见。这个过程涉及 RDMA/NIXL/Mooncake/Mori/Ascend 等 transfer backend，也涉及失败恢复：worker 挂掉后请求是否可迁移，guided decoding/n>1 这种状态机是否可复制。

### 4. 多级 KV offload 是缓存系统，不是简单 swap

把 KV 从 GPU 放到 CPU/NVMe/S3，需要回答：

- 谁决定 evict/promote。
- 访问代价如何进入 router。
- 多 worker 是否共享。
- hash 身份如何去重。
- cache miss 是否比重新 prefill 更慢。

[[src-dynamo-architecture]] 的 KVBM 材料可作为缓存层级和身份管理的设计参考；具体层级与策略应按版本验证。跨系统讨论见 [[kv-cache-offload]]。

### 5. GPU 资源调度和模型调度开始交叉

GPU sharing、MIG/vGPU、DRA/CDI、KV cache offload、P/D 分离都会改变“一个 Pod 需要几张 GPU”的简单假设。Serving control plane 需要更懂 GPU 拓扑、NVLink、NUMA、显存压力、KV cache 热度。

### 6. 可观测必须覆盖 token、KV、队列和 GPU

普通 HTTP latency 不够。现代 LLM serving 至少要观测：

- TTFT / ITL / output token latency。
- prefill/decode queue depth。
- KV hit/miss、tier、transfer latency。
- batch size、chunked prefill、CUDA graph hit。
- GPU utilization、memory pressure、DCGM health。
- autoscaler decision 和 provider capacity error。

## 设计分型

| 分型 | 代表 | 核心问题 |
|------|------|----------|
| 推理引擎 | [[vllm]]、[[sglang]] | local KV、batching、model execution、并行与 connector |
| 数据中心编排层 | [[dynamo]] | 多节点 routing、KV offload、SLA autoscale、K8s operator |
| K8s serving/control plane | [[llm-d]]、[[aibrix]]、[[kserve]] | 分别比较 endpoint picking、engine fleet lifecycle 与模型服务 API 的边界 |
| 算力控制面 | [[src-skypilot-architecture|SkyPilot]] | 多云/K8s/Slurm 资源选择、failover、managed jobs/serve |
| GPU 资源层 | [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | device plugin、DRA、GPU sharing、observability |

## 选型建议

| 目标 | 优先看 | 工程关注点 |
|------|--------|------------|
| 建立可测量的 serving baseline | [[vllm]] / [[sglang]] | 先测目标模型、硬件、TTFT/ITL，再比较执行特性 |
| 研究现代推理引擎内部优化 | [[sglang]] | RadixAttention、Scheduler、spec decoding、P/D transfer |
| 构建多节点高 SLA serving 集群 | [[dynamo]] | KV-aware routing、KVBM、Planner、K8s operator |
| 标准化 Gateway/endpoint picking | [[llm-d]] | Proxy/EPP、InferencePool、KV 信号及当前扩缩集成 |
| 管理 engine fleet 与 adapter 生命周期 | [[aibrix]] | Gateway plugins、controllers、AI Runtime、KV/角色编排 |
| 跨云/跨集群管理 AI workload | [[src-skypilot-architecture|SkyPilot]] | optimizer、failover、managed jobs、serve |
| 建生产 GPU Kubernetes 底座 | [[k8s-gpu-device-stack]] | device plugin、GPU Operator、DRA/CDI、DCGM/GPUd |

## 下一批候选

详见 [[llm-d-kubernetes-sigs-candidate-map]]。已有的 Entity/Source 不再列为待补项目；下一步聚焦尚未验证的跨层问题：

- 用 [[llm-d-benchmark]]、[[inference-perf]] 和 [[llm-d-inference-sim]] 构造相同 workload，比较路由策略、KV 命中率与 TTFT/ITL，而非只比吞吐。
- 核验 llm-d 当前 EPP/KEDA/HPA 路径与历史 WVA 的迁移边界，确认可用 release、配置差异和多 variant 场景。
- 联合 [[kueue]]、[[karpenter]]、[[lws]]、[[jobset]] 验证容量不足、模型冷启动与 worker group readiness 的时间线。
- 针对 D5 做 Gateway/EPP、P/D worker、KV 通道的故障注入，记录可重试阶段、取消传播和流式输出语义。

## 当前知识库缺口

- 还缺少同模型、同硬件、同 SLO 的跨项目实测，当前地图说明职责，不能据此直接给出性能排名。
- KV event schema、身份/布局兼容性和失效传播尚缺跨 engine/connector 的契约对照；“可接入”不等于任意组合可共享 KV。
- P/D 故障后在飞请求、已输出 token 和采样状态能恢复到哪一步，尚缺按 backend 分类的证据。
- 多级 KV 存储、GPU sharing 与拓扑调度如何共同影响路由/扩缩决策，仍需测量与控制权分析。

## 相关页面

- [[llm-inference]]
- [[vllm]]
- [[sglang]]
- [[dynamo]]
- [[llm-d]]
- [[aibrix]]
- [[llm-serving-engine-selection-map]]
- [[inference-routing]]
- [[model-serving-operator]]
- [[paged-attention]]
- [[radix-attention]]
- [[disaggregated-serving]]
- [[kv-cache-offload]]
- [[kubernetes]]
- [[llm-d-kubernetes-sigs-candidate-map]]
