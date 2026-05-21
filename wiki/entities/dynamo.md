---
title: Dynamo
tags: [entity, ai-infra, llm-inference, llm-serving, distributed-serving, kv-cache, kubernetes, nvidia, oss]
date: 2026-05-16
sources: [dynamo-architecture-analysis.md]
related: [vllm, sglang, paged-attention, radix-attention, disaggregated-serving, kv-cache-offload, llm-inference, kubernetes, k8s-operator]
---

# Dynamo

**NVIDIA 开源的数据中心级 LLM 推理编排层。** Apache 2.0，2026-03 推 1.0，5 月 1.2.0，最早把"分离式 prefill/decode + KV-aware 路由 + 多级 KV cache + SLA 自动扩缩"在开源世界做成一套统一栈。

## 一句话定位

Dynamo 不是另一个推理引擎，而是让多个推理引擎（[[sglang]] / [[vllm]] / TensorRT-LLM）组成集群的**编排层**：HTTP 前端 + KV-aware 路由 + 分离式 P/D worker pool + 四级 KV 缓存（KVBM）+ Planner SLA 自动扩缩 + K8s CRD 控制面。详见 [[src-dynamo-architecture]]。

## 核心能力

| 能力 | 说明 |
|------|------|
| **[[disaggregated-serving|分离式 Prefill/Decode]]** | 计算密集的 prefill 和内存密集的 decode 拆成独立可扩缩的 GPU 池 |
| **[[radix-attention|KV-aware 路由]]** | Router 用 cost function 同时权衡 prefix overlap 命中率和 worker 负载，softmax 采样选 worker |
| **[[kv-cache-offload|KV 多级缓存（KVBM）]]** | G1=GPU / G2=CPU pinned / G3=NVMe / G4=S3 四层，LRU+TinyLFU 升降级，NIXL 统一传输 |
| **ModelExpress 权重流式** | GPU-to-GPU 经 NIXL/NVLink 流送权重，冷启动 7× 提速 |
| **Planner SLA 自动扩缩** | Prometheus 拉指标 + throughput/load 双分支决策，输出 ScalingDecision 给 K8s operator |
| **Grove 拓扑感知 gang scheduling** | NVL72 上 rack/host/NUMA 感知放置（外部 scheduler） |
| **AIConfigurator 配置扫描** | 离线扫 10K+ TP/EP/DEP 配置选 Pareto 前沿 |
| **请求迁移（fault tolerance）** | RetryManager 让 worker 死亡对客户端透明 |

## 技术栈

| 组件 | 语言 | 占比 |
|------|------|------|
| Runtime / HTTP / 路由 / KVBM | Rust（22 个 workspace crate，edition 2024） | ~1000 个 .rs 文件 |
| Backend wrapper / Planner / 前端 entry | Python（PyO3 经 maturin 绑定） | ~896 个 .py 文件 |
| K8s Operator | Go（DGDR/DGD/DCD 三层 CRD） | ~258 个 .go 文件 |

依赖： tokio + axum（HTTP）+ etcd-client + async-nats + cudarc + prometheus + opentelemetry + tower-http。

## 与同类对比

| 维度 | Dynamo | [[vllm]] 单引擎 | [[sglang]] Router | Ray Serve / KServe |
|------|--------|-----------------|-------------------|---------------------|
| 主要场景 | 多 GPU/多节点协调 | 单节点 LLM serving | 单节点请求路由 | 通用模型服务 |
| 分离 P/D | ✅ 默认 | ❌ | ❌ | 自己拼 |
| KV-aware 路由 | ✅ radix tree + NATS | ❌ | ✅（单进程） | ❌ |
| KV 多级 offload | ✅ G1-G4 + NIXL | 部分 | ❌ | ❌ |
| 在飞请求迁移 | ✅ RetryManager | ❌ | ❌ | ❌ |
| SLA 自动扩缩 | ✅ Planner + AIConfigurator | ❌ | ❌ | K8s HPA |

定位差异：vLLM/SGLang/TRT-LLM 解决"一个 GPU 怎么跑得快"，Dynamo 解决"一群 GPU 怎么跑得协调"。

## 历史与影响

- **2026-03**：Dynamo 1.0 发布，宣告"production-ready" + 70+ community contributors
- **生态采用**：Baseten（2× TTFT）、Mistral AI（Mistral Large 3 10× 提速）、Moonshot AI（Kimi K2 10× 提速）、Alibaba（APSARA 2025）、Dell PowerScale 集成 NIXL（19× TTFT）、WEKA KV 缓存存储合作
- **当前状态**：1.2.0（commit 7997117，2026-05），Day-0 DeepSeek-V4 recipes 已合入 main

## 出处

- 仓库：https://github.com/ai-dynamo/dynamo
- 文档：https://docs.nvidia.com/dynamo/
- 架构深入：[[src-dynamo-architecture]]

## 相关页面

- 核心架构：[[src-dynamo-architecture]]
- 支持的 backend：[[vllm]]、[[sglang]]
- 核心理念：[[disaggregated-serving]]、[[radix-attention]]、[[kv-cache-offload]]、[[paged-attention]]
- 控制面基础：[[kubernetes]]、[[k8s-operator]]
- 上位概念：[[llm-inference]]