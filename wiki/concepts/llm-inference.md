---
title: LLM Inference
tags: [concept, ai-infra, llm-inference, llm-serving]
date: 2026-06-12
sources: [dynamo-architecture-analysis.md, vllm-architecture-analysis.md, sglang-architecture-analysis.md, llm-d-architecture-analysis.md, aibrix-architecture-analysis.md, kserve-architecture-analysis.md, llm-d-batch-gateway-architecture-analysis.md, llm-d-benchmark-architecture-analysis.md, llm-d-workload-variant-autoscaler-architecture-analysis.md, llm-d-inference-sim-architecture-analysis.md]
related: [[vllm]], [[sglang]], [[dynamo]], [[llm-d]], [[aibrix]], [[kserve]], [[paged-attention]], [[radix-attention]], [[disaggregated-serving]], [[kv-cache-offload]], [[inference-routing]], [[batch-inference]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]]
---

# LLM Inference

LLM 推理（inference / serving）指把训练好的大语言模型部署成在线服务，对外提供 token 生成 API。核心挑战：高吞吐、低延迟、长 context、多并发、成本。

## 系统分层

| 层级 | 代表项目 | 关注点 |
|------|----------|--------|
| 推理引擎 | [[vllm]], [[sglang]] | KV cache 管理、batching、scheduler、kernel、模型加载 |
| 数据中心编排 | [[dynamo]] | P/D 分离、KV transfer/offload、router、planner、operator |
| K8s serving stack | [[llm-d]], [[aibrix]], [[kserve]], [[kubeai]], [[ome]], [[gpustack]] | CRD/operator、gateway、autoscaling、endpoint picking、GPU 资源 |
| 路由 / 网关 | [[semantic-router]], [[routellm]], [[gateway-api-inference-extension]], [[ai-gateway]] | 模型选择、endpoint picking、成本/质量/语义/KV-aware routing |
| 离线 / 实验 / 扩缩外围 | [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]] | batch job、benchmark、variant autoscaling、无 GPU simulator |
| 硬件资源层 | [[hami]], [[gpu-operator]], [[k8s-device-plugin]], [[dra-driver-nvidia-gpu]] | GPU discovery、device plugin、DRA/CDI、sharing/vGPU/MIG |

## 核心技术主题

### Prefill vs Decode

Prefill 负责把 prompt/context 一次性编码成 KV cache，算力密集、吞吐敏感；Decode 每步生成一个 token，延迟敏感、状态持续时间长。[[disaggregated-serving]] 把两者拆到不同 GPU 池中分别扩缩，是 [[dynamo]]、[[llm-d]] 等系统的主线。

### Batching

Continuous batching / inflight batching 让不同请求在 token step 之间动态进出 batch，避免传统 fixed batch 的尾部浪费。它是 [[vllm]] / [[sglang]] 这类 engine 的吞吐基础。

### KV cache

长上下文和多轮对话让 KV cache 成为一等资源。[[paged-attention]] 用分页思想降低碎片，[[radix-attention]] 用 radix tree 加速 prefix 复用，[[kv-cache-offload]] 把 KV 在 GPU/CPU/SSD/远端之间迁移。到了 [[dynamo]] / [[llm-d]]，KV cache 还会反过来影响路由和调度。

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
- 需要路由模型或 endpoint：看 [[inference-routing]]、[[semantic-router]]、[[gateway-api-inference-extension]]。
- 需要离线批处理、评测、仿真或 variant autoscaling：看 [[llm-d-batch-gateway]] / [[llm-d-benchmark]] / [[llm-d-inference-sim]] / [[llm-d-workload-variant-autoscaler]]。
