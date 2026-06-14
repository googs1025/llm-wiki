---
title: llm-d Inference Sim 架构与设计思路分析
tags: [architecture, llm-serving, simulator, benchmark]
date: 2026-06-13
sources: [llm-d-inference-sim-architecture-analysis.md]
related: [[llm-d-inference-sim]], [[llm-d]], [[llm-d-benchmark]], [[inference-routing]], [[llm-inference]]
---

# llm-d Inference Sim 架构与设计思路分析

> 原文：`raw/llm-d-inference-sim-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-inference-sim · 分析版本 HEAD `6fb66f3`

## 一句话定位

[[llm-d-inference-sim]] 是一个轻量 vLLM 行为模拟器，用 Go 实现 OpenAI-compatible HTTP API、vLLM-compatible gRPC/API、KV cache 事件、LoRA 生命周期、延迟模型和 metrics，而不需要 GPU 或真实大模型。它让 [[inference-routing]]、scheduler、[[llm-d-benchmark]]、autoscaler 和 P/D/KV cache 策略能在便宜、可控、可注入故障的环境中被验证。

## 核心架构图

```
┌───────────────────────────────────────────────┐
│ Clients / Routers / Benchmark Harnesses       │
│ OpenAI HTTP, vLLM gRPC, llm-d Router, tests   │
└───────────────────┬───────────────────────────┘
                    │ same port, cmux
┌───────────────────▼───────────────────────────┐
│ Communication Layer                           │
│ pkg/communication                             │
│ HTTP routes + gRPC server + graceful drain    │
└──────────────┬───────────────────────┬────────┘
               │ request               │ metrics/admin
               ▼                       ▼
┌──────────────────────────┐   ┌────────────────────────┐
│ OpenAI / vLLM API layer  │   │ /metrics /fake_metrics │
│ pkg/openai-server-api    │   │ health/ready/admin     │
└──────────────┬───────────┘   └────────────────────────┘
               │ normalized request
               ▼
┌───────────────────────────────────────────────┐
│ Simulator Core                               │
│ pkg/llm-d-inference-sim                      │
│ - DP rank simulators                         │
│ - worker pool                                │
│ - latency calculators                        │
│ - streaming/non-streaming response           │
└───────┬───────────────┬───────────────┬───────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌──────────────┐ ┌────────────────┐
│ Tokenizer   │ │ Dataset      │ │ KV Cache       │
│ HF/regex    │ │ prompts/data │ │ block keys     │
└─────────────┘ └──────────────┘ │ events/stats   │
                                 └───────┬────────┘
                                         │ ZMQ / metrics
                                         ▼
                                llm-d KV-aware routing tests
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 入口命令 | 读取配置、初始化 simulator、启动 HTTP/gRPC 通信层和数据集工具。 |
| 通信层 | 同端口 cmux HTTP/gRPC，OpenAI/vLLM/admin/metrics/health routes，graceful drain。 |
| API 适配 | OpenAI-compatible completion/chat/responses/embeddings 和 vLLM-compatible 协议对象。 |
| 模拟核心 | 创建 DP rank simulator、worker pool、处理请求、模拟 TTFT/ITL/streaming。 |
| Token / Dataset | 支持 HuggingFace tokenizer、regex/simulated tokenizer、dataset-backed response。 |
| KV cache | 计算 llm-d kv block key，维护 block cache，生成 PrefixCacheStats 和事件。 |

## 关键数据流

```
OpenAI / vLLM 请求进入同一监听端口
        │
        ▼
cmux 分流 HTTP 或 gRPC
        │
        ▼
HTTP route / gRPC handler 解析请求
        │
        ▼
Simulator 根据 DP rank / worker pool 接收任务
        │
        ├── tokenizer 估算 prompt tokens
        ├── dataset 或 echo/random 生成候选输出
        ├── KV cache 计算 block keys / cached tokens
        ├── latency calculator 模拟 TTFT、ITL、remote prefill
        ├── failure injection / sleep / wake_up 可改变行为
        └── metrics / KV events 持续输出
        │
        ▼
Streaming 或 non-streaming response 返回给调用方
```

## 设计决策与哲学

- **协议兼容优先于真实模型计算**：它实现 OpenAI HTTP、vLLM/gRPC 和多种 admin/metrics endpoint，让上游系统无需知道自己面对的是 simulator。
- **延迟是可配置模型，不是固定 sleep**：TTFT、inter-token、load factor、remote prefill/KV transfer 被拆开建模。
- **KV cache 行为是一等模拟对象**：它计算 llm-d KV block key、cached prompt tokens 和 PrefixCacheStats，可测试 KV-aware routing。
- **无 GPU 可运行降低系统实验门槛**：[[llm-d-benchmark]]、router、WVA、Gateway API 相关测试能在 Kind 或普通集群中先跑通。

## 相关页面

- [[llm-d-inference-sim]]
- [[llm-d-benchmark]]
- [[llm-d]]
- [[inference-routing]]
- [[llm-inference]]
