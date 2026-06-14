---
title: LLM Inference / Serving 项目地图
tags: [llm-inference, llm-serving, kv-cache, project-map, ai-infra]
date: 2026-06-09
sources: [src-dynamo-architecture, src-sglang-architecture, src-skypilot-architecture, src-k8s-gpu-device-plugins-stars, src-llm-d-architecture, src-llm-d-batch-gateway-architecture, src-llm-d-benchmark-architecture, src-llm-d-workload-variant-autoscaler-architecture, src-llm-d-inference-sim-architecture]
related: [[dynamo]], [[vllm]], [[sglang]], [[llm-d]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]], [[batch-inference]], [[llm-inference]], [[paged-attention]], [[radix-attention]], [[disaggregated-serving]], [[kv-cache-offload]], [[kubernetes]], [[llm-d-kubernetes-sigs-candidate-map]]
---

# LLM Inference / Serving 项目地图

这页把当前知识库里的 LLM 推理与 serving 相关材料横向整理。核心结论：LLM serving 已经从“单机推理引擎优化”演进成多层系统工程：KV cache 管理、batch 调度、P/D 分离、KV-aware routing、多级 offload、SLA 扩缩、GPU 资源调度和多云控制面都在同一条链路上。

```
Client API / OpenAI-compatible protocol
        ↓
serving frontend: HTTP/SSE/gRPC, tokenizer, request validation
        ↓
scheduler: continuous batching, prefill/decode, admission, chunking
        ↓
KV cache manager: paged blocks / radix tree / offload tiers
        ↓
GPU execution: attention backend, CUDA graph, speculative decoding
        ↓
cluster orchestration: P/D pools, routing, KV transfer, autoscaling
        ↓
infrastructure control plane: Kubernetes, GPU sharing, multi-cloud, observability
        ↓
peripheral control planes: batch jobs, benchmark, simulator, variant autoscaling
```

## 一句话分层

| 项目 / 概念 | 一句话定位 | 抽象层 |
|-------------|------------|--------|
| [[vllm]] | LLM serving 的事实基线，[[paged-attention]] 把 KV cache 按 block 管理 | 单机推理引擎 |
| [[sglang]] | 高性能推理引擎，[[radix-attention]] token 级 KV 复用 + 4 进程流水线 + speculative decoding | 单机/多实例推理引擎 |
| [[dynamo]] | NVIDIA 数据中心级 LLM 推理编排层，把 vLLM/SGLang/TRT-LLM 组成协调集群 | 多节点 serving 编排 |
| [[llm-d]] | CNCF Sandbox 分布式 LLM inference serving stack，围绕 Router/EPP、InferencePool、KV/P-D/autoscaling 组织 | K8s serving control plane |
| [[llm-d-batch-gateway]] | OpenAI Batch API / 离线推理控制面，把 batch job/file/queue/output 接到下游 llm-d Router/model endpoint | Batch serving control plane |
| [[llm-d-benchmark]] | llm-d 实验编排器，把 scenario/spec、K8s lifecycle、harness 和 result workspace 串起来 | Benchmark lifecycle |
| [[llm-d-workload-variant-autoscaler]] | 同一模型多个 serving variant 的全局 autoscaling 决策层，经 Prometheus/HPA/KEDA 执行扩缩 | Variant autoscaling |
| [[llm-d-inference-sim]] | 无 GPU vLLM 行为模拟器，用 OpenAI/vLLM API、KV events、latency/failure/metrics 验证控制面 | Simulator / test double |
| [[src-skypilot-architecture|SkyPilot]] | AI/ML 多云算力控制平面，负责跨云/K8s/Slurm 选择资源、failover、managed jobs/serve | 算力控制平面 |
| [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | device plugin / GPU Operator / DRA / CDI / DCGM / GPU sharing | GPU 资源基础设施 |

## 横向对比

| 维度 | [[vllm]] | [[sglang]] | [[dynamo]] | [[src-skypilot-architecture|SkyPilot]] | [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] |
|------|----------|------------|------------|--------------|---------------|
| 主问题 | 单机/单服务高吞吐推理 | 极致推理执行和 KV 复用 | 多 GPU/多节点协调 serving | 跨云/集群算力选择和作业控制 | GPU 设备暴露、共享、观测 |
| 核心抽象 | Paged KV block table | RadixCache + Scheduler pipeline | Request/control/event planes + KVBM | Task/Dag/Resources + Optimizer | DevicePlugin/DRA/CDI/Operator |
| KV 粒度 | 16-token block | token-level radix tree | SequenceHash + G1-G4 cache tiers | 不直接管理 KV | 不直接管理 KV，但影响显存资源 |
| 调度 | continuous batching | 4 进程 pipeline + Scheduler mixins | KV-aware router + P/D pool + Planner | Optimizer 选 cloud/region/instance | kube-scheduler/device allocation |
| P/D 分离 | 实验/生态扩展中 | 多 backend 支持 | 默认核心架构 | 可部署 serving 集群 | 提供底层 GPU 资源 |
| 扩缩 | 通常交给外部平台 | 外部平台或自建 | Planner + K8s Operator | Managed jobs / serve / pools | HPA/Kueue/GPU operator 等 |
| 容错 | 引擎级错误处理 | 引擎级错误处理 | RetryManager 迁移在飞请求 | provisioning failover | 节点/设备健康与重调度 |
| 强项 | 生态最大、基线稳 | KV 复用和执行路径激进 | 集群协调、KV-aware、SLA | 多云和资源经济 | 生产 GPU 集群底座 |
| 代价 | block 级复用有碎片 | 复杂度高、特性组合约束多 | 系统栈重、组件多 | 不优化内核推理路径 | 只管资源，不管模型执行 |

## 架构交叉矩阵

| 交叉模式 | 采用项目 | 工程含义 |
|----------|----------|----------|
| KV cache 显式管理 | [[vllm]], [[sglang]], [[dynamo]] | KV cache 是 serving 吞吐和显存效率的核心资源，不再是模型内部细节 |
| 前缀复用 | [[vllm]], [[sglang]], [[dynamo]] | system prompt、few-shot、agent template 可共享，路由/调度要感知 prefix |
| Prefill/Decode 分离 | [[sglang]], [[dynamo]], [[disaggregated-serving]] | prefill 计算密集，decode 内存带宽密集，独立扩缩能提高资源利用 |
| 多级 KV offload | [[dynamo]], [[kv-cache-offload]] | GPU 显存不够时，把 KV 分层到 CPU/NVMe/Object store |
| Speculative decoding | [[sglang]], [[vllm]] | 用 draft/target 或 ngram 等方法降低 decode latency |
| K8s 控制面 | [[dynamo]], [[src-skypilot-architecture|SkyPilot]], [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | serving 从进程问题变成 CRD/operator/scheduler 问题 |
| Batch / benchmark / simulator | [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-inference-sim]] | serving 选型需要异步任务、可复现实验和低成本控制面替身 |
| Variant autoscaling | [[llm-d-workload-variant-autoscaler]] | 同一模型的多硬件/多角色/多成本 variant 需要全局 allocation，而不是单 Deployment 指标 |
| 资源经济 | [[src-skypilot-architecture|SkyPilot]], [[dynamo]] Planner, [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | 不只是跑得快，还要按 SLA、成本和容量调度 |

## 核心设计轴

### 1. KV cache：从内存优化到系统接口

LLM serving 的很多架构分歧都来自 KV cache：

- [[vllm]] 的 [[paged-attention]] 把 KV cache 切成 block，解决传统最大 seq_len 预分配浪费。
- [[sglang]] 的 [[radix-attention]] 把前缀共享做到 token 级，适合 agent template、few-shot、tree-of-thought 这类大量共享前缀场景。
- [[dynamo]] 把 KV 块变成跨 worker、跨 GPU/CPU/NVMe/Object tier 的全局对象，用 SequenceHash 做身份，路由和 offload 都围绕它展开。

结论：KV cache 已经从“GPU 内部 buffer”变成 serving 系统的一等资源。后续的路由、扩缩、迁移、offload、GPU sharing 都需要知道 KV 的存在。

### 2. 单机引擎和集群编排是两层问题

[[vllm]] / [[sglang]] 解决的是“一个实例怎么高效执行请求”；[[dynamo]] 解决的是“一组实例怎么协调”。

```
single engine:
  tokenizer → scheduler → model runner → KV cache → attention backend

cluster serving:
  frontend → route → prefill/decode worker pools → KV transfer → autoscale → recover
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

[[dynamo]] 把 P/D 分离做成默认集群架构；[[sglang]] 提供 Mooncake/NIXL/Mori/Ascend 等 KV transfer backend；[[vllm]] 仍更多是基线引擎和生态底座。

### 4. 路由不再只是负载均衡

传统 HTTP 负载均衡按连接数、延迟或权重分发。LLM serving 的路由还要考虑：

- 哪个 worker 已有 prompt prefix KV。
- prefill 队列和 decode 队列哪个更忙。
- KV 在 GPU、CPU、磁盘还是远端对象存储。
- 当前请求是否可迁移。
- LoRA/model adapter 是否匹配。

[[dynamo]] 的 KV-aware router 用 cost function 同时计算 prefix overlap credit 和 worker 负载，softmax 采样而不是绝对 argmin。这说明 serving router 的目标不是“最大化 cache hit”，而是在 cache hit、queue load、tail latency 之间做平衡。

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

### [[vllm]]：事实基线和 PagedAttention

[[vllm]] 的最大价值是把 KV cache 管理变成一个系统问题。PagedAttention 的 block table 让显存按需分配，替代按最大序列长度预留。这是 LLM serving 的转折点。

适合借鉴的点：

- 把 KV cache 从连续大 buffer 变成可管理 block。
- 把 OpenAI-compatible serving 做成事实入口。
- 生态兼容和模型覆盖优先。

主要局限：

- block 粒度共享会有碎片，system prompt 长度不对齐时复用不精细。
- P/D 分离和多节点协调不是它最强的原生边界。
- 集群级 SLA、KV-aware routing、offload 需要外部系统补齐。

### [[sglang]]：执行路径极致模块化

[[sglang]] 的工程特点是把推理执行的差异化轴都做成可插拔路径：

- HTTP / TokenizerManager / Scheduler / DetokenizerManager 四进程。
- RadixCache token 级 KV 复用。
- EXTEND / DECODE / MIXED 等 forward mode。
- 10+ attention backend。
- 7 套 speculative decoding。
- 5 个 P/D KV transfer backend。
- OpenAI / Anthropic / Ollama / gRPC / Engine API。

它的核心收益是性能和灵活性；代价是特性组合约束复杂，例如 speculative、chunked prefill、disagg 之间存在互斥/兼容边界。对于工程研究，它是理解现代推理引擎内部结构的最好材料之一。

### [[dynamo]]：数据中心级 serving 编排

[[dynamo]] 把 serving 从单实例推进到集群系统：

```
HTTP frontend
        ↓
preprocess / migration
        ↓
KV-aware routing
        ↓
prefill/decode worker pools
        ↓
KVBM G1-G4
        ↓
NATS JetStream KV events
        ↓
Planner + K8s Operator
```

它的工程难点集中在三平面解耦：

- request plane：低延迟请求路径。
- control plane：discovery、desired state、K8s/file/etcd。
- storage/event plane：KV visibility、JetStream、object store。

它的独特价值不是替代 vLLM/SGLang，而是把它们当 backend，补上多节点路由、KV transfer、请求迁移、SLA 扩缩和拓扑感知部署。

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

把请求发给已有 prefix KV 的 worker 能省 prefill，但那个 worker 可能很忙。把请求发给空闲 worker 延迟可能更低，但要重新 prefill。[[dynamo]] 的 cost-based softmax 正是在处理这个冲突。

### 3. P/D 分离引入状态转移问题

Prefill 输出的 KV 必须被 decode 节点可见。这个过程涉及 RDMA/NIXL/Mooncake/Mori/Ascend 等 transfer backend，也涉及失败恢复：worker 挂掉后请求是否可迁移，guided decoding/n>1 这种状态机是否可复制。

### 4. 多级 KV offload 是缓存系统，不是简单 swap

把 KV 从 GPU 放到 CPU/NVMe/S3，需要回答：

- 谁决定 evict/promote。
- 访问代价如何进入 router。
- 多 worker 是否共享。
- hash 身份如何去重。
- cache miss 是否比重新 prefill 更慢。

[[dynamo]] 的 KVBM 把它做成 G1-G4 tier + LRU/TinyLFU + SequenceHash，这说明 offload 已经是缓存系统设计。

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
| 单机基线引擎 | [[vllm]] | 高吞吐 serving、PagedAttention、生态兼容 |
| 高性能执行引擎 | [[sglang]] | token-level KV、pipeline、spec decode、P/D backend |
| 数据中心编排层 | [[dynamo]] | 多节点 routing、KV offload、SLA autoscale、K8s operator |
| K8s serving control plane | [[llm-d]]、[[aibrix]]、[[kserve]] | Gateway API / InferencePool、Operator、Endpoint picking、autoscaling |
| 算力控制面 | [[src-skypilot-architecture|SkyPilot]] | 多云/K8s/Slurm 资源选择、failover、managed jobs/serve |
| GPU 资源层 | [[src-k8s-gpu-device-plugins-stars|K8s GPU stack]] | device plugin、DRA、GPU sharing、observability |

## 选型建议

| 目标 | 优先看 | 工程关注点 |
|------|--------|------------|
| 需要最稳的开源 serving baseline | [[vllm]] | PagedAttention、模型兼容、OpenAI API |
| 研究现代推理引擎内部优化 | [[sglang]] | RadixAttention、Scheduler、spec decoding、P/D transfer |
| 构建多节点高 SLA serving 集群 | [[dynamo]] | KV-aware routing、KVBM、Planner、K8s operator |
| 构建 Kubernetes-native inference control plane | [[llm-d]] / [[aibrix]] / [[kserve]] | Gateway API、InferencePool、Operator、autoscaling、batch/benchmark 配套 |
| 跨云/跨集群管理 AI workload | [[src-skypilot-architecture|SkyPilot]] | optimizer、failover、managed jobs、serve |
| 建生产 GPU Kubernetes 底座 | [[k8s-gpu-device-stack]] | device plugin、GPU Operator、DRA/CDI、DCGM/GPUd |

## 下一批候选

详见 [[llm-d-kubernetes-sigs-candidate-map]]。当前 [[llm-d]] P0 外围能力已经补齐，下一步最值得做的是把这些能力连接到 Kubernetes 调度、队列和 metrics 生态：

- batch inference：[[llm-d-batch-gateway]] 已有，后续可拆 API server / processor / GC 细页。
- benchmark / simulator：[[llm-d-benchmark]]、[[llm-d-inference-sim]] 已有，后续可以细化 benchmark 报告模型；[[inference-perf]] 和 [[llm-d-prism]] 已补正式页。
- autoscaling / queueing：[[llm-d-workload-variant-autoscaler]] 已有，[[kueue]]、[[karpenter]]、[[metrics-server]]、[[prometheus-adapter]] 已补正式页。
- distributed workload API：[[lws]]、[[jobset]] 已补正式页。

## 当前知识库缺口

- 还缺少独立的 [[vllm]] 架构 source 页，当前主要来自 entity 和 SGLang 对照。
- 还缺少 TensorRT-LLM、TGI、Ray Serve 的深入页，无法完整覆盖 serving 生态。
- 还缺少 Kueue、Karpenter、LeaderWorkerSet、JobSet 这类 AI workload 调度 / 队列 / 分布式 API 页。
- 还缺少 `llm-d-latency-predictor`、`llm-d-prism`、`llm-d-pd-utils` 和 `llm-d-inference-payload-processor` 这类 P1/P2 配套页。
- 可以补一篇 “KV cache as schedulable resource” 概念页，把 KVBM、kvcached、P/D 分离和 GPU sharing 串起来。

## 相关页面

- [[llm-inference]]
- [[vllm]]
- [[sglang]]
- [[dynamo]]
- [[llm-d]]
- [[paged-attention]]
- [[radix-attention]]
- [[disaggregated-serving]]
- [[kv-cache-offload]]
- [[kubernetes]]
- [[llm-d-kubernetes-sigs-candidate-map]]
