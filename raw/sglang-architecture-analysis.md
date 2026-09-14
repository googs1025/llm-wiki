# SGLang 架构与设计思路分析

> 仓库：https://github.com/sgl-project/sglang · 分析日期：2026-09-13 · 版本：main @ `7f1f8c7`（官方 README/docs）

## 一句话定位

[[sglang]] 是面向 LLM/多模态模型的高性能 serving runtime，核心差异是 RadixAttention：用 radix tree 组织可共享前缀的 KV cache；再把结构化生成、连续批、chunked prefill、投机解码、attention/kernel backend 和多 GPU 并行组合为执行管线。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│ Client / OpenAI · Anthropic · Ollama · Native Engine                  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP / gRPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / TokenizerManager                                         │
│  request lifecycle · tokenizer · structured program · streaming       │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ ZMQ / shared memory
┌──────────────────────────────▼───────────────────────────────────────┐
│ Scheduler subprocess                                                  │
│  waiting/running batch · EXTEND/DECODE/MIXED · RadixCache · allocator  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ model input / metadata
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU ModelRunner                                                       │
│  attention backend · fused/quantized kernels · sampler                │
│       │                         │                                     │
│       ├─ TP/PP collectives         └─ EP token dispatch for MoE         │
│       └─ DP attention / batch partition                                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / states
┌──────────────────────────────▼───────────────────────────────────────┐
│ DetokenizerManager ──► stream response                                │
└──────────────────────────────────────────────────────────────────────┘
             │
             ├─ RadixCache / HiCache: GPU → host → storage tiers
             └─ PD/EPD disaggregation: transfer KV or encoder outputs
```

## 模块分层

| 层 / 模块 | 主要目录 / 文档 | 职责 |
|---|---|---|
| 接入与编程模型 | `python/sglang/`, README, serving docs | API、SGLang DSL、tokenize、流式输出 |
| 调度与批处理 | `python/sglang/srt`, continuous batching docs | request 状态、EXTEND/DECODE/MIXED、chunked prefill、overlap |
| 缓存层 | radix/session cache、`advanced_features/hicache*` | prefix sharing、eviction、GPU/CPU/storage 分层、量化 KV |
| 执行与 kernel | model runner、attention backend、`sgl-kernel` | attention、FFN/MoE、sampling、CUDA Graph、spec decode |
| 分布式拓扑 | TP/PP/DP/EP、PD/EPD docs、Model Gateway | collectives、expert routing、请求路由、P/D 分离 |

## 关键数据流

```
请求 / SGLang program
  │
  ├─ tokenizer + program state，形成可复用 token prefix
  ├─ RadixCache longest-prefix match：命中则复用 KV，否则分配 token/KV pool
  ├─ Scheduler 组成连续 batch：EXTEND / DECODE / MIXED
  │       └─ 长 prompt 以 chunked prefill 切片并与 decode 交错
  ├─ ModelRunner 选择 attention backend，执行 fused attention/FFN/MoE
  │       └─ TP/PP/DP/EP collective 或 all-to-all
  └─ sampler → DetokenizerManager → streaming response；完成后更新 radix tree
```

RadixAttention 以 token prefix 为树路径，适合 system prompt、few-shot、agent loop 和多轮会话。HiCache 增加 host/storage 层；PD disaggregation 通过 KV transfer 连接独立的 prefill/decode 实例。

## 设计决策与哲学

- **Radix tree 优先优化前缀复用**：牺牲比固定 block 更复杂的树维护与 eviction，换取任意 token 边界共享。
- **显式 batch mode**：EXTEND、DECODE、MIXED 与 chunked prefill 让算力型 prefill 和带宽型 decode 共存，并支持 overlap。
- **进程与 backend 解耦**：TokenizerManager、Scheduler、ModelRunner、DetokenizerManager 异步协作；attention、量化、speculation、KV transfer 可配置替换。
- **并行轴按模型结构组合**：TP/PP 解决规模，DP 解决副本吞吐，EP 解决 MoE 专家分布；DP attention 可复制 attention、保留 FFN/MoE 的 TP/EP。

## 推理优化专题

### KV Cache

RadixCache 做 GPU 内 token-level prefix sharing；session cache 保持会话树状态；eviction 释放冷叶节点。HiCache 扩展 GPU/host/storage 层，量化 KV 降低容量；P/D 分离用 NIXL/Mooncake 等 backend 搬运 KV。

### 连续批处理

Scheduler 每轮重新决定可执行 token 数量，新请求可插入 running batch；长 prompt 通过 chunked prefill 切片，EXTEND 与 DECODE/MIXED 调整公平性。overlap scheduler、two-batch/single-batch overlap 重叠 CPU 调度、通信和 GPU 计算。

### 算子融合与并行

FlashInfer、FlashAttention、Triton、AITER 等 attention backend，配合 sgl-kernel、JIT/torch.compile、CUDA Graph、fused MoE/量化 kernel，减少 launch 与中间读写。TP 切权重，PP 切层，EP 分布专家，DP 分区请求/批/KV；收益取决于 GPU 拓扑、shape、精度和负载。

## 与 vLLM 对比

vLLM 的 PagedAttention 以固定 block 获得简单、稳健的 allocator；SGLang 的 RadixAttention 以树获得更细粒度 prefix sharing。两者已在 kernel、量化、spec decode、P/D、TP/PP/EP/DP 上高度重叠，应以 prefix reuse、TTFT/ITL、吞吐和硬件 backend 实测选择。

## 来源

- https://github.com/sgl-project/sglang/blob/main/README.md
- https://github.com/sgl-project/sglang/blob/main/docs/index.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hicache_design.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/hicache.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/pipeline_parallelism.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/expert_parallelism.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/pd_disaggregation.mdx
- https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/attention_backend.mdx
