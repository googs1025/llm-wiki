# vLLM 架构与设计思路分析

> 仓库：https://github.com/vllm-project/vllm · 分析日期：2026-09-13 · 版本：main @ `de50029`（官方 README/docs）

## 一句话定位

[[vllm]] 是面向在线 LLM serving 的高吞吐推理引擎。它以 V1 Engine Core 为调度与执行中枢，用 PagedAttention 管理非连续 KV block，用 continuous batching、CUDA Graph/torch.compile、量化与并行通信把 GPU 计算、显存和网络带宽组合起来。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                         Client / OpenAI API                          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ request / stream tokens
┌──────────────────────────────▼───────────────────────────────────────┐
│ API Server / LLM entrypoint                                           │
│  request validation · tokenizer · output streaming · metrics          │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ IPC / multiprocessing
┌──────────────────────────────▼───────────────────────────────────────┐
│ V1 Engine Core                                                        │
│  Scheduler ──► Sequence groups ──► KV cache manager / block table     │
│      │                         │                                      │
│      └──────────────► Model input / sampling metadata                 │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ collective / IPC
┌──────────────────────────────▼───────────────────────────────────────┐
│ GPU Worker(s): ModelRunner                                           │
│  embedding → transformer blocks → attention backend → logits         │
│       │              │                    │                           │
│       │              ├─ TP all-reduce / all-gather                     │
│       │              ├─ PP send / receive between layer stages         │
│       │              └─ EP all-to-all for MoE experts                   │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ token ids / logprobs
┌──────────────────────────────▼───────────────────────────────────────┐
│ Detokenization / output processor ──► API stream                      │
└──────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要目录 / 文档 | 职责 |
|---|---|---|
| 接入层 | `vllm/entrypoints`, serving docs | OpenAI-compatible API、离线 LLM API、tokenize、流式输出 |
| 引擎与调度 | `vllm/v1`, `docs/design/arch_overview.md` | Engine Core、调度 token budget、请求生命周期、batch metadata |
| 内存层 | `docs/design/paged_attention.md`, `features/automatic_prefix_caching.md` | block allocator、block table、prefix hash、KV eviction/offload |
| 模型执行 | model runner、attention backends、model implementations | Transformer forward、sampling、speculative decoding |
| Kernel/编译层 | `docs/design/attention_backends.md`, `optimization_levels.md` | FlashAttention/FlashInfer/Triton/CUDA Graph、torch.compile、fused ops |
| 分布式层 | `distributed`, parallelism/data/expert deployment docs | TP、PP、DP、EP、通信 backend、跨节点部署 |

## 关键数据流

```
新请求
  │
  ├─ tokenize，计算 prompt token 与可复用 prefix hash
  │
  ├─ Scheduler 按 token budget 选择 waiting/running 请求
  │       ├─ 命中 block table → 只 prefill 未命中的 suffix
  │       └─ 未命中 → 分配 KV blocks；空间不足则 eviction / 等待
  │
  ├─ Prefill：批量处理 prompt，写入 paged KV cache
  │
  ├─ Decode：每轮为每条活跃序列生成一个 token；新序列可随时加入，完成序列释放 blocks
  │       └─ continuous batching + chunked prefill 平衡 TTFT 与 ITL
  │
  ├─ attention backend 通过 block table gather K/V，执行 fused attention
  │
  └─ logits → sampler → detokenize → stream；停止/异常时回收 sequence 与 KV blocks
```

PagedAttention 把每条序列的 KV cache 切成固定大小 block，逻辑 block 由 block table 映射到物理 GPU block，因此序列可增长、暂停和复用而不要求物理连续显存。Automatic Prefix Caching 对完整 KV block 做 hash，命中时复用；它不会改变采样结果，只减少重复 prefill。

## 设计决策与哲学

- **PagedAttention 优先解决显存碎片**：牺牲 block 粒度的边界灵活性，换取可预测的分配、共享与高并发。
- **调度以 token budget 为核心**：连续批不是固定 batch；每轮动态组合 prefill/decode，让短请求完成后立即补位，同时限制长 prompt 对 decode 的干扰。
- **计算与通信后端可替换**：attention backend、量化 kernel、collective、CUDA Graph 与 compile level 根据硬件/shape 选择，避免把单一 kernel 写死在引擎里。
- **并行策略按模型结构组合**：TP 切分层内权重，PP 切分层，DP 复制模型提升吞吐，MoE 用 EP 分布专家；不同轴的收益受通信拓扑和 batch shape 约束。

## 推理优化专题

### KV Cache

Paged KV 是“容量与碎片”优化；Prefix Caching 是“重复 prompt”优化；KV offload/connector 是“容量层级”优化。典型链路是 GPU block → CPU/远端存储 → 需要时异步加载。KV dtype 可用 FP8 等低精度降低容量，但要验证 attention 数值误差、scale 与硬件支持。

### 连续批处理

调度器把请求拆成可推进的 token 工作量，而不是等待整批完成。Prefill 更偏算力，decode 更偏带宽；chunked prefill 将长 prompt 分块，并与 decode 交错。优化目标应同时看 TTFT、ITL、吞吐、队列等待和 KV 使用率。

### 算子融合与张量执行

官方设计文档列出 attention backend、CUDA Graph、torch.compile fusion、RMSNorm/量化/ROPE/KV cache 写入及 Fused MoE modular kernel 等路径。融合减少 kernel launch、global-memory round trip 和中间 tensor；但动态 shape、稀疏路由、量化格式和 graph capture 会限制可融合范围。应按 prefill/decode、batch size、head size、GPU 架构分别 benchmark。

### TP / PP / EP / DP

| 并行 | 切分/复制对象 | 主要通信 | 适用重点 |
|---|---|---|---|
| TP | 每层权重、attention heads | all-reduce/all-gather | 单节点或高速互联上装下大模型 |
| PP | 不同 transformer layers | stage 间 send/receive | 跨节点、深而窄模型；需 micro-batch 降低 bubble |
| DP | 完整模型副本与请求 | 副本间通常独立；MoE 可能需对齐 | 模型能放入单副本、目标是吞吐 |
| EP | MoE experts | token dispatch/reduce 的 all-to-all | 专家权重很大、需要分摊 MoE 计算 |

vLLM 文档特别指出，DP+TP 时 attention 可在 DP 副本内使用 TP；启用 EP 后，MoE expert group 通常按 DP×TP 组织。DP 部署还需要考虑每个 rank 独立 KV cache 带来的 prefix locality 与负载均衡问题。

## 关键组件深入解读

### V1 Engine Core

V1 将 API/前端与 Engine Core、GPU worker 分开。Core 接收请求并维护 waiting/running 状态、调度预算、KV block 生命周期和输出；worker 只接收结构化 model input，在 GPU 上完成 forward 与 sampling，再返回 token/output。这个边界让调度策略、执行后端和进程模型可以分别演进，也为 DP coordinator、KV events 与 P/D disaggregation 留出接口。

### PagedAttention + Prefix Cache

Attention 不读取连续的 `[sequence, token, head, dim]` 大数组，而是依据 block table 找到物理 block 并执行 paged gather。Prefix cache 以 token prefix 与模型/LoRA 等上下文生成 hash，只有完整且可验证的 block 才能共享；因此 block size 是内存碎片、hash 开销、prefix 命中率之间的折中。

## 与 SGLang 对比

vLLM 的核心优势是成熟、通用的 block allocator 与广泛模型/部署生态；SGLang 以 radix tree 做 token 级 prefix sharing，更适合高度重复的结构化程序、agent prompt 和多轮共享前缀。两者都已扩展到量化、投机解码、P/D 分离及 TP/PP/DP/EP，实际选择应以 workload、硬件和 benchmark 为准。

## 来源

- https://github.com/vllm-project/vllm/blob/main/README.md
- https://github.com/vllm-project/vllm/blob/main/docs/design/arch_overview.md
- https://github.com/vllm-project/vllm/blob/main/docs/design/paged_attention.md
- https://github.com/vllm-project/vllm/blob/main/docs/features/automatic_prefix_caching.md
- https://github.com/vllm-project/vllm/blob/main/docs/configuration/optimization.md
- https://github.com/vllm-project/vllm/blob/main/docs/serving/data_parallel_deployment.md
- https://github.com/vllm-project/vllm/blob/main/docs/serving/expert_parallel_deployment.md
