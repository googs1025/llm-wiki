---
title: LLM Inference
tags: [concept, ai-infra, llm-inference, llm-serving]
date: 2026-06-12
sources: [dynamo-architecture-analysis.md, k8s-serving-stack-comparison-2026-09-13.md, vllm-architecture-analysis.md, sglang-architecture-analysis.md, llm-d-architecture-analysis.md, llm-d-router-architecture-analysis.md, llm-d-kv-cache-architecture-analysis.md, aibrix-architecture-analysis.md, kserve-architecture-analysis.md, llm-d-batch-gateway-architecture-analysis.md, llm-d-benchmark-architecture-analysis.md, llm-d-workload-variant-autoscaler-architecture-analysis.md, llm-d-inference-sim-architecture-analysis.md]
related: [[vllm]], [[sglang]], [[dynamo]], [[llm-d]], [[llm-d-router]], [[llm-d-kv-cache]], [[aibrix]], [[kserve]], [[kubeai]], [[ome]], [[gpustack]], [[rbg]], [[kthena]], [[paged-attention]], [[radix-attention]], [[disaggregated-serving]], [[kv-cache-offload]], [[inference-routing]], [[batch-inference]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]]
---

# LLM Inference

LLM 推理（inference / serving）指把训练好的大语言模型部署成在线服务，对外提供 token 生成 API。核心挑战：高吞吐、低延迟、长 context、多并发、成本。

## 系统分层

| 层级 | 代表项目 | 关注点 |
|------|----------|--------|
| 推理引擎 | [[vllm]], [[sglang]] | KV cache 管理、batching、scheduler、kernel、模型加载 |
| 数据中心编排 | [[dynamo]] | P/D 分离、KV transfer/offload、router、planner、operator；把 engine 变成可扩缩、可迁移的集群服务 |
| K8s serving stack | [[llm-d]], [[aibrix]], [[kserve]], [[kubeai]], [[ome]], [[gpustack]], [[rbg]], [[kthena]] | 从标准模型 API、runtime/operator、LLM 路由、P/D workload 到 GPU/MaaS 的不同控制面 |
| 路由 / 网关 | [[llm-d-router]], [[semantic-router]], [[routellm]], [[gateway-api-inference-extension]], [[ai-gateway]] | 模型选择、endpoint picking、成本/质量/语义/KV-aware routing |
| KV locality / cache signal | [[llm-d-kv-cache]], [[dynamo]], [[kv-cache-offload]] | KV block index、cache-hit scoring、KV transfer/offload tiers |
| 离线 / 实验 / 扩缩外围 | [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]] | batch job、benchmark、variant autoscaling、无 GPU simulator |
| 硬件资源层 | [[hami]], [[gpu-operator]], [[k8s-device-plugin]], [[dra-driver-nvidia-gpu]] | GPU discovery、device plugin、DRA/CDI、sharing/vGPU/MIG |

## K8s serving stack 扩展比较

这八个项目不是同一层的替代品，建议先按抽象层分类：

| 类别 | 项目 | 核心对象/入口 | 主要解决的问题 |
|---|---|---|---|
| 分布式 LLM serving | [[llm-d]] | Gateway/EPP、InferencePool、model server | K8s 标准入口下的 endpoint picking、KV/P/D 和分布式推理 |
| GenAI 基础组件 | [[aibrix]] | Gateway、CRD、Unified AI Runtime、KV/LoRA 组件 | vLLM fleet 的路由、adapter、KV、autoscaling、故障检测和异构成本优化 |
| 通用模型平台 | [[kserve]] | InferenceService、LLMInferenceService、InferenceGraph | 用统一 API/operator 承载 predictive + generative AI，并支持 canary、缓存、KV offload 与 scale-to-zero |
| 轻量 AI operator | [[kubeai]] | Model CRD、model proxy、loader、autoscaler | 快速把 LLM/VLM/embedding/speech 模型变成 OpenAI-compatible API |
| Runtime/operator 抽象 | [[ome]] | model agent、runtime selector、accelerator config | 把模型生命周期、推理 runtime 和加速器配置解耦 |
| GPU/MaaS 平台 | [[gpustack]] | server、worker、scheduler、gateway、model service | 跨本地/K8s/云管理 GPU，并提供多模型 API、计量、认证和运维 |
| Workload 原语 | [[rbg]] | RoleBasedGroup、Role、RoleInstance、CoordinatedPolicy | 表达 gateway/router/prefill/decode 多角色有状态服务，保证拓扑和跨角色原子操作 |
| 一体化 LLM serving | [[kthena]] | ModelBooster、ModelServing、ModelServer、ModelRoute | 在 K8s/Volcano 内整合路由、P/D、限流、canary、扩缩、拓扑和 gang scheduling |

### 选型不要只问“哪个最好”

- 要 **Gateway API + InferencePool 标准化**：优先研究 [[llm-d]] / [[kserve]]。
- 要 **vLLM 生态的 LoRA、KV、企业组件**：研究 [[aibrix]]。
- 要 **最短路径把模型暴露成 OpenAI API**：研究 [[kubeai]]。
- 要 **模型 runtime/accelerator 生命周期抽象**：研究 [[ome]]。
- 要 **GPU 集群、多云、MaaS、token/API 计量**：研究 [[gpustack]]。
- 要 **多角色、有状态、P/D workload 的原子升级/扩缩**：研究 [[rbg]]。
- 要 **K8s 原生完整 LLM serving，并深度结合 Volcano 拓扑/gang**：研究 [[kthena]]。

完整的 README/文档驱动对比、能力矩阵和选型流程见 [[src-k8s-serving-stack-comparison]]。

## 总体架构与请求流程

```text
Client / Application
        │ OpenAI / Anthropic / gRPC
        ▼
Gateway / Semantic Router
        │ auth · quota · model · KV locality
        ▼
InferencePool / Endpoint Picker
        │ queue · health · topology
        ▼
┌────────────────────── Serving Runtime ──────────────────────┐
│  Prefill Worker          KV Transfer          Decode Worker  │
│  tokenizer → scheduler ───────────────► scheduler → stream │
│       │                         │                          │
│       └──── attention / kernel / TP-PP-EP-DP ───────────────┘
└───────────────────────────┬─────────────────────────────────┘
                            ▼
                    GPU / CPU / NVMe KV tiers
                            │
                            ▼
                 Metrics → Autoscaling → Recovery
```

```text
请求进入 → 认证/限流 → KV-aware endpoint
       → Prefill → Decode → Sampling → Streaming
       ├─ 完成：释放 KV → 返回结果
       └─ 故障：重试 / 迁移 / 重新计算
```

## 核心技术主题

## 代码阅读入口

如果要从实现而不是概念开始，建议沿两条主链阅读：

```text
vLLM:
EngineCore.step
  → Scheduler.schedule
  → KVCacheManager.allocate_slots
  → GPUModelRunner.execute_model
  → Attention selector/backend
  → update_from_output

SGLang:
run_event_loop
  → get_next_batch_to_run
  → ScheduleBatch
  → UnifiedRadixCache.match_prefix + allocation
  → ModelRunner / ForwardMode backend
  → process_batch_result
```

详细的文件路径、函数职责、状态对象和两者差异见 [[src-vllm-architecture]] 与 [[src-sglang-architecture]]。

### Prefill vs Decode

Prefill 负责把 prompt/context 一次性编码成 KV cache，算力密集、吞吐敏感；Decode 每步生成一个 token，延迟敏感、状态持续时间长。[[disaggregated-serving]] 把两者拆到不同 GPU 池中分别扩缩，是 [[dynamo]]、[[llm-d]] 等系统的主线。

### Batching

Continuous batching / inflight batching 让不同请求在 token step 之间动态进出 batch，避免传统 fixed batch 的尾部浪费。它是 [[vllm]] / [[sglang]] 这类 engine 的吞吐基础。

### KV cache

长上下文和多轮对话让 KV cache 成为一等资源。[[paged-attention]] 用分页思想降低碎片，[[radix-attention]] 用 radix tree 加速 prefix 复用，[[kv-cache-offload]] 把 KV 在 GPU/CPU/SSD/远端之间迁移。到了 [[dynamo]] / [[llm-d]]，KV cache 还会反过来影响路由和调度：[[llm-d-kv-cache]] 把 KV events 变成 locality index，[[llm-d-router]] 再把 cache-hit score 和负载、profile 等信号一起纳入 endpoint picking。

### Chunked Prefill

Chunked prefill 把长 prompt 的 prefill 切块，与 decode 请求交错执行，减少长 prompt 阻塞短请求。它常和 prefix cache、P/D 分离、batch scheduler 一起出现。

### Speculative Decoding

Speculative decoding 用小模型或 draft head 先猜 token，再由大模型验证，目标是降低每个生成 token 的大模型前向次数。工程代价是调度、显存、accept rate 和模型兼容性变复杂。

### LoRA / Adapter Serving

LoRA serving 让一个 base model 同时服务多个轻量 adapter，关键问题是 adapter 加载、batch 内 adapter 混排、cache 隔离和多租户权限。[[aibrix]] 等 K8s serving 项目会把它放到模型生命周期和 gateway 层一起处理。

### Multi-modal Serving

VLM / speech / embedding / rerank 等任务把输入预处理、processor、tokenizer、模型 runtime 和输出格式变得更复杂。[[kubeai]] 这类 operator 会把 LLM/VLM/embedding/speech 纳入同一 Model CRD。

### Quantization

FP8 / INT4 / AWQ / GPTQ 等量化路线降低显存和带宽压力，但会影响 kernel 支持、精度、吞吐和 serving 兼容性。选型时要看 engine 是否原生支持目标量化格式，以及 GPU 架构是否匹配。

### Batch Inference

[[batch-inference]] 把大量请求作为异步 job 执行，关注文件、队列、状态、重试、取消、输出归档和成本，而不是单个请求的 streaming latency。[[llm-d-batch-gateway]] 说明 batch 层可以复用下游 [[llm-d]] Router/model endpoint，但必须额外引入 PostgreSQL、Redis/Valkey 和 object store 来承接长时状态。

### Benchmark / Simulator

推理系统选型不能只看架构图，还要能复现实验。[[llm-d-benchmark]] 把 stack standup、scenario 渲染、harness 运行和结果收集做成 workspace；[[llm-d-inference-sim]] 则用无 GPU 的 vLLM 行为模拟器验证 router、autoscaling、KV event 和 benchmark 流程。二者解决的是“如何测”和“如何低成本复现控制面行为”。

### Variant Autoscaling

普通 HPA/KEDA 面向单 workload 或通用 event source；LLM serving 进入 P/D 分离、多 GPU 型号、多成本池之后，需要按同一模型的多个 serving variant 做全局 allocation。[[llm-d-workload-variant-autoscaler]] 把 InferencePool、Prometheus、GPU inventory、capacity model 和 HPA/KEDA 串起来，是 [[model-serving-operator]] 之外更细粒度的资源经济层。

## 选型入口

- 只优化单机吞吐：优先看 [[vllm]] / [[sglang]]。
- 需要 P/D 分离、KV transfer、数据中心级编排：看 [[dynamo]] / [[llm-d]]。
- 需要 Kubernetes model serving API：看 [[kserve]] / [[kubeai]] / [[ome]]。
- 需要多租户平台和 GPU 集群管理：看 [[aibrix]] / [[gpustack]]。
- 需要路由模型或 endpoint：看 [[inference-routing]]、[[llm-d-router]]、[[semantic-router]]、[[gateway-api-inference-extension]]。
- 需要离线批处理、评测、仿真或 variant autoscaling：看 [[llm-d-batch-gateway]] / [[llm-d-benchmark]] / [[llm-d-inference-sim]] / [[llm-d-workload-variant-autoscaler]]。
