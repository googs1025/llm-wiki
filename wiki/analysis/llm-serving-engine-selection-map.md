---
title: LLM Serving / 推理引擎选型地图
tags: [llm-inference, llm-serving, kv-cache, selection, ai-infra]
date: 2026-06-11
sources: [src-dynamo-architecture, src-sglang-architecture, src-skypilot-architecture, src-k8s-gpu-device-plugins-stars]
related: [[llm-inference-serving-project-map]], [[vllm]], [[sglang]], [[dynamo]], [[paged-attention]], [[radix-attention]], [[disaggregated-serving]], [[kv-cache-offload]]
---

# LLM Serving / 推理引擎选型地图

已有 [[llm-inference-serving-project-map]] 把层次铺开。这页面向选型：单机推理引擎、集群 serving 编排、多云算力控制和 K8s GPU 底座不要混为一谈。

## GitHub 当前核验

截至 2026-06-11 通过 GitHub API 重新核验：

| 项目 | 仓库 | 最近 push | stars | 主语言 | 当前定位 |
|------|------|-----------|-------|--------|----------|
| [[vllm]] | https://github.com/vllm-project/vllm | 2026-06-11 | 82k | Python | high-throughput, memory-efficient inference engine |
| [[sglang]] | https://github.com/sgl-project/sglang | 2026-06-11 | 28k | Python | high-performance serving framework |
| [[dynamo]] | https://github.com/ai-dynamo/dynamo | 2026-06-11 | 7.2k | Rust | datacenter scale distributed inference serving |
| [[src-skypilot-architecture|SkyPilot]] | https://github.com/skypilot-org/skypilot | 2026-06-11 | 10k | Python | any-cloud AI workload control plane |

## 选型结论

| 场景 | 首选 | 原因 |
|------|------|------|
| 快速搭 OpenAI-compatible 模型服务 | [[vllm]] | 生态最大、模型覆盖广、PagedAttention 基线成熟 |
| 追求极致执行路径和前缀复用 | [[sglang]] | RadixAttention、speculative decoding、P/D transfer backend 多 |
| 多节点 P/D 分离、KV-aware routing、SLA 扩缩 | [[dynamo]] | 把 vLLM/SGLang/TRT-LLM 组织成集群 serving 系统 |
| 跨云/K8s/Slurm 选资源和启动 workload | [[src-skypilot-architecture|SkyPilot]] | 算力控制面，不替代推理引擎 |
| GPU 共享、DRA/CDI、设备观测 | K8s GPU stack | serving 底座，不处理模型执行 |

## 架构区别

| 维度 | [[vllm]] | [[sglang]] | [[dynamo]] | [[src-skypilot-architecture|SkyPilot]] |
|------|----------|------------|------------|--------------|
| 抽象层 | 单机/单服务推理引擎 | 单机/多实例推理引擎 | 多节点 serving 编排 | 多云算力控制 |
| KV 策略 | block table / [[paged-attention]] | token-level radix cache / [[radix-attention]] | SequenceHash + 多级 KV tier | 不直接管理 KV |
| 调度 | continuous batching | scheduler pipeline / mixins | KV-aware router + P/D pools | Optimizer 选云/区/实例 |
| 扩缩 | 外部平台为主 | 外部平台为主 | Planner + operator | managed jobs / serve |
| 强项 | 稳定基线和生态 | 性能路径和特性实验 | 集群级协调和 SLA | 资源经济和 failover |

## 决策轴

- **单实例吞吐**：优先比较 [[vllm]] 和 [[sglang]]。
- **多节点系统**：优先看 [[dynamo]]，不要期待单引擎自己解决 KV transfer、P/D pool 和 SLA planner。
- **成本/容量调度**：看 [[src-skypilot-architecture|SkyPilot]]，它决定 workload 跑在哪里。
- **K8s 生产化**：再看 DRA/CDI/GPU Operator/DCGM/Kueue/Volcano，底层设备模型会反过来影响 serving 架构。

## 避坑条件

- 不要把 [[dynamo]] 当成“另一个 vLLM”；它是 serving 编排层。
- 不要把 [[src-skypilot-architecture|SkyPilot]] 当成 inference engine；它是资源控制面。
- P/D 分离只有在 prompt/decode 负载、KV transfer、路由和扩缩都配套时才有收益。
- KV cache 已经是一等资源，路由、迁移、offload 都要显式建模。

