---
title: vLLM
tags: [entity, ai-infra, llm-inference, llm-serving, kv-cache, oss]
date: 2026-05-15
sources: [sglang-architecture-analysis.md]
related: [sglang, paged-attention, radix-attention, flash-attention]
---

# vLLM

**UC Berkeley Sky Computing Lab 开源的 LLM 推理与 serving 引擎。** Apache 2.0，最早把 [[paged-attention]] 引入开源界（SOSP 2023 论文），是目前最广泛使用的 LLM serving 框架之一。

## 一句话定位

LLM serving 的"事实标准基线"：用 [[paged-attention]] 把 KV 缓存按 16-token block 管理（类比 OS 虚存分页），把 GPU 显存从"按最大 seq_len 预分配"改成"按需 block 分配 + block table 映射"，让吞吐量数倍于 HuggingFace transformers。后来的 [[sglang]] / TensorRT-LLM / TGI 都把 vLLM 当对标。

## 关键能力（与 [[sglang]] 对照）

| 维度 | vLLM | [[sglang]] |
|------|------|---------|
| **KV 缓存粒度** | 16-token block（[[paged-attention]]） | token 级（[[radix-attention]]） |
| **前缀共享** | 整 block 才能 share，碎片化严重 | 任意分叉点自动 share |
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

- **vLLM block table 强制 token 对齐**：16 token block 内即使只用 7 个也占满一格；SGLang flat KV pool 不浪费
- **vLLM PrefixCache 同 block 才共享**：system prompt 长度不是 16 倍数 → 末尾几个 token 无法被共享；SGLang radix 树天然支持任意 token 边界 split
- **vLLM 单进程主导**：scheduler + tokenizer + worker 多线程；SGLang 4 进程异步流水线
- **vLLM 投机解码生态较窄**：EAGLE + Medusa；SGLang 7 算法

## 相关页面

- 核心算法：[[paged-attention]]
- 主要对标：[[sglang]]
- 概念对照：[[radix-attention]]
- 依赖：[[flash-attention]]
