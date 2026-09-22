---
title: vLLM
tags: [entity, ai-infra, llm-inference, llm-serving, kv-cache, oss]
date: 2026-09-22
sources: [vllm-architecture-analysis.md]
related: [sglang, paged-attention, radix-attention, flash-attention]
---

# vLLM

> 最新代码级架构资料：[[src-vllm-architecture]]，基于本地 HEAD `dc36fcce90`。

**UC Berkeley Sky Computing Lab 开源的 LLM 推理与 serving 引擎。** Apache 2.0，最早把 [[paged-attention]] 引入开源界（SOSP 2023 论文），是目前最广泛使用的 LLM serving 框架之一。

## 一句话定位

LLM serving 的"事实标准基线"：用 [[paged-attention]] 将 KV 缓存组织为固定大小的逻辑/物理 block（类比 OS 虚存分页），并通过 block table 建立映射；具体 block 大小取决于配置、attention backend 和版本。这把 GPU 显存从"按最大 seq_len 预分配"改成"按需 block 分配 + block table 映射"，让吞吐量数倍于 HuggingFace transformers。后来的 [[sglang]] / TensorRT-LLM / TGI 都把 vLLM 当对标。

## 最小架构图

```text
API / Offline LLM → V1 Engine Core
                    ├─ Scheduler：token budget、waiting/running
                    ├─ KV Manager：block allocator、block table
                    └─ Model Input：sampling / attention metadata
                              ↓
                 GPU ModelRunner → Attention / Fused MoE
                              ↓
                    TP · PP · EP · DP → Sampler → Stream
```

## 关键能力（与 [[sglang]] 对照）

| 维度 | vLLM | [[sglang]] |
|------|------|---------|
| **KV 缓存粒度** | 固定大小的逻辑/物理 block + block table（大小依配置/backend/版本） | token 级（[[radix-attention]]） |
| **前缀共享** | 按 block 边界共享；末尾未填满的 partial block 在完整前可能无法复用 | 任意分叉点自动 share |
| **投机解码** | EAGLE / Medusa（少量） | 7 算法（EAGLE / NGRAM / MTP / DFLASH / Standalone / 多层 EAGLE / v2） |
| **P/D 分离** | 实验性 | 生产级 + 5 transfer backend |
| **Attention 后端** | FlashAttn / xFormers / TorchSDPA | 10+ 后端 |
| **结构化输出** | outlines | 4 backend |
| **协议入口** | OpenAI | OpenAI / Anthropic / Ollama / gRPC / Engine |
| **国产硬件** | 实验 | Ascend NPU 一等公民 |
| **生态广度** | 最大（HF 模型几乎全支持）| 追赶中 |

## 历史与影响

- **2023-09**：vLLM 0.1 发布，论文 *"Efficient Memory Management for Large Language Model Serving with PagedAttention"* (SOSP 2023)
- **首创性**：把虚存分页思想引入 LLM KV cache，是行业转折点
- **采用度**：HuggingFace TGI、Ray Serve、Anyscale、Together AI 等都基于 vLLM 或受其启发；几乎所有"LLM as a Service"产品的 baseline

## 与 SGLang 的差异点（基于 sglang 架构分析）

- **vLLM PagedAttention 使用 block table**：将固定大小的逻辑 KV block 映射到物理 KV block；具体 block 大小和未用容量行为随配置、attention backend 与版本而异
- **vLLM PrefixCache 按 block 边界共享**：末尾未填满的 partial block 在完整前可能无法复用；SGLang radix 树支持在任意 token 边界 split
- **vLLM 单进程主导**：scheduler + tokenizer + worker 多线程；SGLang 4 进程异步流水线
- **vLLM 投机解码生态较窄**：EAGLE + Medusa；SGLang 7 算法

## 在 M4 模块地图中的位置

vLLM 位于 engine 层，负责请求调度、模型执行、attention backend 和本地 KV 管理；外部流量路由与自动扩缩由外围 serving 层承担。职责边界见 [[llm-inference-serving-project-map]]，组合选择见 [[llm-serving-engine-selection-map]]。

## 相关页面

- 核心算法：[[paged-attention]]
- 主要对标：[[sglang]]
- 概念对照：[[radix-attention]]
- 依赖：[[flash-attention]]
