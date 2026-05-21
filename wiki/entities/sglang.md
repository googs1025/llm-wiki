---
title: SGLang
tags: [entity, ai-infra, llm-inference, llm-serving, kv-cache, oss]
date: 2026-05-15
sources: [sglang-architecture-analysis.md]
related: [vllm, radix-attention, paged-attention, speculative-decoding, prefill-decode-disaggregation, flash-attention, mooncake]
---

# SGLang

**LMSYS / sglang-project 开源的高性能 LLM 推理与 serving 引擎。** Apache 2.0，Python 3.10+，主仓库 [github.com/sgl-project/sglang](https://github.com/sgl-project/sglang)，活跃主线（HEAD `50f4058` 时分析）。

## 一句话定位

把 LLM 推理引擎的**所有"差异化轴"**做到接近开源极致：[[radix-attention]] 取代 [[paged-attention]] 把 KV 复用做到 token 级；4 进程异步流水线 + Scheduler 内 overlap 把 GPU 利用率拉到 95%+；7 套投机解码 + 5 KV transfer backend + 10+ attention backend + 4 grammar backend 全部可插拔；统一 OpenAI / Anthropic / Ollama 协议入口。论文里还提出"SGLang DSL"（fork / gen / select）做结构化生成的前端编译。

## 关键能力

| 维度 | 能力 |
|------|------|
| **KV 缓存** | [[radix-attention]] —— token 级 radix 树；4 RadixCache 变体（vanilla / hi / mamba / swa / cpp）|
| **批量化** | 连续批 + chunked prefill + EXTEND/DECODE/MIXED 三态调度 + CUDA Graph 替换 decode 路径 |
| **多进程流水线** | HTTP / TokenizerManager（主） / Scheduler（GPU subprocess） / DetokenizerManager（subprocess），ZMQ pyobj 三段管道 |
| **投机解码** | 7 算法：EAGLE-2 / EAGLE-v2 / 多层 EAGLE / FrozenKV-MTP / NGRAM / DFLASH / Standalone，走 `BaseSpecWorker` + `spec_registry` |
| **[[prefill-decode-disaggregation]]** | 5 transfer backend：[[mooncake]] / NIXL / Mori / Ascend / Fake；prefill 与 decode 节点独立扩容 |
| **Attention 后端** | 10+：FlashInfer（默认）/ FA3-4 / Triton / FlashMLA / NSA / DSV4 / FlexAttention / TorchNative / Wave / AITER / Intel-AMX |
| **结构化输出** | xgrammar / outlines / llguidance / reasoner，sampling 前 apply vocab mask |
| **协议入口** | OpenAI / Anthropic / Ollama / gRPC / 原生 Engine SDK |
| **分布式** | TP / PP / DP / EP（专家并行）+ Elastic-EP + 专家分布记录器 |
| **国产硬件** | Ascend NPU / Wave / AITER 一等公民（不是实验路径）|
| **模型库** | 100+ 模型：LLaMA / Qwen / DeepSeek / Mixtral / Gemma / GPT-OSS / 多模态 |
| **多模态** | image / audio（Whisper / Qwen-ASR）/ video 预处理 + KV 缓存 |
| **前端 DSL** | SGLang DSL（fork / gen / select）—— 编译到 RadixCache 友好的执行计划 |

## 接入形态

- **HTTP server**：`python -m sglang.launch_server --model-path ...` → FastAPI/uvicorn 默认 8000 端口；推荐用 `sglang serve` CLI
- **gRPC server**：`--grpc-mode`，走 `entrypoints/grpc_server.py` 适合内部高吞吐 RPC
- **离线 Engine API**：`from sglang import Engine; engine.generate(...)`，编程式调用不起 HTTP
- **encoder-only 模式**：`--encoder-only` 启动专用 encoder 实例（给 P/D disagg 用）
- **Ray 模式**：`--use-ray` 走 Ray cluster scheduler
- **SGLang DSL**：在 Python 程序里 `@sgl.function def chain_of_thought(s, q): s += sgl.user(q); s += sgl.gen("answer")` —— 编译成多步骤请求，RadixCache 共享 system prompt

## 设计哲学（与 [[vllm]] 等同类对照）

- **Token 级 KV 复用 vs [[vllm]] block 级**：vLLM 16-token block 对长 system prompt / few-shot / agent template 浪费严重；SGLang 用 token-level radix 树 + flat KV pool 让任意 token 边界都能 split & share，论文 throughput 1.6-6.4× over vLLM
- **4 进程异步流水线**：Tokenize / Forward / Detokenize 拆到不同 OS 进程，ZMQ 串联；任何一环堵塞都不卡其他环，GPU 维持高占用
- **Mixin 拼装 Scheduler**：4000+ 行的 `scheduler.py` 通过 10+ Mixin 把 disagg/PP/DPAttn/Dllm/Profiler/UpdateWeights 等横切关注点解耦，open-closed 友好；新加 disagg 后端不改主类
- **可插拔哲学贯穿整栈**：attention backend / spec algorithm / KV transfer / grammar / quantization / model 全可注册可替换；服务启动时按 `server_args` 选择
- **国产硬件一等公民**：Ascend NPU 不是 fallback 路径，专门有 disagg/ascend、 attention/ascend、`platforms/ascend`，跟 NVIDIA 路径并行

## 工程数据

| 指标 | 实际表现 |
|------|---------|
| **prefix 缓存收益** | RadixAttention 论文：LLaMA-7B tree-of-thought / few-shot throughput **1.6-6.4×** over vLLM |
| **decode latency** | CUDA graph replay → 单步 ≈ kernel-only |
| **投机解码加速** | EAGLE-2 默认 topk=5 step=5：典型 **1.5-2.5×** decode 加速 |
| **P/D 分离收益** | 长 prefill / 长 decode 场景吞吐 **1.3-2×** over collocated |
| **流水线 overlap** | 4 进程异步 + Scheduler overlap → 单 GPU 占用 95%+ |

## 学术与起源

- **来源论文**：Zheng et al., *"SGLang: Efficient Execution of Structured Language Model Programs"* (NeurIPS 2024) —— 论文里 RadixAttention + SGLang DSL 是核心贡献
- **组织起源**：LMSYS / UC Berkeley Sky Computing Lab 团队（FastChat / Chatbot Arena / vLLM 都来自相近社区）
- **生态**：在 DeepSeek 官方推荐推理引擎之一；DeepSeek-V3 的 MTP / MLA 实现是 SGLang 主导贡献

## 相关页面

- 架构详解：[[src-sglang-architecture]]
- 核心算法：[[radix-attention]]、[[speculative-decoding]]、[[prefill-decode-disaggregation]]
- 同类系统：[[vllm]]（最直接对标）
- 依赖：[[flash-attention]]（FlashInfer / FA3 / FlashMLA）、[[mooncake]]（KV transfer）
- 相关概念：[[paged-attention]]（vLLM 的对照系统）
