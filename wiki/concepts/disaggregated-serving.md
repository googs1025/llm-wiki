---
title: Disaggregated Serving
tags: [concept, ai-infra, llm-inference, llm-serving, kv-cache]
date: 2026-05-16
sources: [dynamo-architecture-analysis.md]
related: [dynamo, vllm, sglang, paged-attention, kv-cache-offload, llm-inference]
---

# Disaggregated Serving（分离式服务）

把 LLM 推理的 **prefill（首 token 计算）** 与 **decode（后续 token 流式生成）** 拆到独立的 GPU 池中分别扩缩的部署模式。[[dynamo|NVIDIA Dynamo]] 把它做成默认架构，[[vllm]] / [[sglang]] / TensorRT-LLM 都开始实验性支持。

## 为什么要分离

Prefill 和 decode 的负载特征完全不同：

| 阶段 | 计算密度 | 内存压力 | 并行度 | 延迟敏感点 |
|------|----------|----------|--------|------------|
| **Prefill** | 高（O(n²) attention，n=输入 token 数） | 中（一次性算完） | 大 batch 友好 | TTFT（time to first token） |
| **Decode** | 低（每步 O(n)） | 高（KV cache 持续累积） | 小 batch 内存瓶颈 | ITL（inter-token latency） |

聚合模式（同一 GPU 同时跑 prefill 和 decode）会让两阶段互相干扰：
- 大 prefill 来一发，正在 decode 的请求被挤出，ITL 抖动
- 小 prefill 来很多发，GPU 算力没用满
- 显存按 max KV 预留，decode 用不到的 prefill 内存被浪费

分离模式让 prefill 池和 decode 池**独立扩缩**：prefill 用更多算力（H100 / B200），decode 用更大显存（H200 / GB200），各自 batch 策略也独立调优。

## 关键工程问题：KV 怎么传

Prefill 完算出的 KV 必须传到 decode 池才能续写：

```
[Prefill Worker]                          [Decode Worker]
    │                                          │
    │  ① 算 KV cache                          │
    │  ② 返回 disaggregated_params            │
    │  ③ KV blocks ──NIXL/GDS/RDMA──►         │
    │                                          │  ④ 接收 KV，开始 decode
    │                                          │  ⑤ stream tokens
```

主流传输方案：
- **NIXL（NVIDIA Inference Xfer Library）**：统一抽象 GPUDirect RDMA / NVLink / NVMe / 对象存储
- **GPUDirect-RDMA**：GPU 之间直接 RDMA，绕过 CPU
- **MooncakeConnector**（vLLM 实现）：基于 Mooncake 项目的 P/D 解耦传输

## [[dynamo|Dynamo]] 中的实现

Dynamo 把分离式做成第一类公民：
1. **PrefillRouter**（独立组件）选 prefill worker → 跑 prefill → 返回 disaggregated_params
2. PrefillRouter 选 decode worker → 把 KV 转移元数据传过去
3. KV blocks 经 NIXL 跨 worker 传输
4. Decode worker 开始流式生成

支持矩阵：[[sglang]] ✅、TensorRT-LLM ✅、[[vllm]] ✅（含 MooncakeConnector）。

## 收益与代价

**收益：**
- 各阶段独立扩缩，资源利用率更高
- 大 prefill 不再撞挂 decode（ITL 抖动消除）
- 异构硬件搭配（prefill 用算力强卡，decode 用显存大卡）

**代价：**
- 多一跳网络传输（KV blocks），需要高速互联（NVLink/RDMA）才划算
- 路由复杂度上升（要选两次 worker）
- 故障域增加（prefill worker 死了，decode worker 收不到 KV）

## 相关页面

- 旗舰实现：[[dynamo]]、[[src-dynamo-architecture]]
- 兼容 backend：[[vllm]]、[[sglang]]
- 协同概念：[[kv-cache-offload]]（KV 在多级存储间流动）、[[radix-attention]]（KV-aware 路由配套）
- 上位概念：[[llm-inference]]