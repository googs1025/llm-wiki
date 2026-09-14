---
title: vLLM 架构与推理优化
tags: [architecture, llm-serving, kv-cache, inference-optimization]
date: 2026-09-14
sources: [vllm-architecture-analysis.md]
related: [[vllm]], [[paged-attention]], [[radix-attention]], [[llm-inference]], [[inference-routing]]
---

# vLLM 架构与推理优化

> 原文：`raw/vllm-architecture-analysis.md` · 仓库：`/Users/zhenyu.jiang/vllm` · 版本：local HEAD `dc36fcce90`

## 一句话定位

[[vllm]] 是高吞吐 LLM serving 引擎：以 [[paged-attention]] 管理 KV block，以 continuous batching、编译/融合 kernel 和 TP/PP/EP/DP 扩展推理容量与吞吐。

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

## 请求与 KV 数据流

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

## 推理优化要点

- **KV**：PagedAttention 解决碎片与动态增长；Prefix Caching 复用完整 KV block；offload/connector 扩展 GPU 之外的容量；FP8 等 KV dtype 以精度换容量。
- **连续批**：每轮按 token budget 调度；chunked prefill 与 decode 交错，平衡 TTFT、ITL、吞吐和队列等待。
- **融合**：attention backend、CUDA Graph、torch.compile fusion、RMSNorm/ROPE/KV 写入和 Fused MoE 降低 launch 与中间 tensor 成本。
- **并行**：TP 切层内权重，PP 切层，DP 复制模型，EP 分布 MoE 专家；通信拓扑和 batch shape 决定真实收益。

## 关键设计

- Engine Core 管理状态、预算和 KV；GPU worker 专注执行，形成清晰的调度/执行边界。
- 固定 block 换取可预测的内存管理；代价是 prefix sharing 受 block 边界影响。
- 后端可替换，允许按硬件、shape 和 prefill/decode 阶段选择不同 kernel。

## 代码级关键路径

```text
EngineCore.step()
  → Scheduler.schedule()
  → KVCacheManager.allocate_slots()
  → SchedulerOutput
  → GPUModelRunner.execute_model()
  → _prepare_inputs() / attention metadata
  → Attention backend
  → sampler
  → Scheduler.update_from_output()
```

```text
EngineCore.step()
  ├─ scheduler.has_requests()
  ├─ Scheduler.schedule()
  │    ├─ new_step_starts()
  │    ├─ 先遍历 running requests
  │    ├─ 再从 waiting queue admission
  │    ├─ KVCacheManager.allocate_slots()
  │    ├─ 空间不足 → preempt lowest-priority / tail request
  │    └─ 生成 SchedulerOutput
  ├─ model_executor.execute_model(non_block=True)
  ├─ future.result() / sample_tokens()
  └─ scheduler.update_from_output()
```

```text
waiting Request
    ↓ get_computed_blocks(request)
local prefix hit + external connector hit
    ↓
num_computed_tokens / shared_prefix_boundary
    ↓ allocate_slots(num_new_tokens, num_lookahead_tokens)
 ┌───────────────┴────────────────┐
 │ 有足够 block                   │ 无足够 block
 │ 返回 new_blocks                │ 选择 running victim
 │                                │ _preempt_request()
 └───────────────┬────────────────┘
                 ↓
SchedulerOutput.req_to_new_blocks
                 ↓
GPU ModelRunner 写入 KV block table
```

vLLM V1 用 request 的 `num_computed_tokens` 统一描述 chunked prefill、decode 和 speculative lookahead；KV admission 与 preemption 在 `schedule()` 内完成。`Attention` 通过 selector 选择 FlashAttention、FlashInfer、Triton 等后端；P/D、CPU offload 和远端 KV 通过 `KVConnectorBase_V1` 的 scheduler/worker metadata 接口接入。

## 与 SGLang 的代码实现对比

| 维度 | vLLM | SGLang |
|---|---|---|
| 主循环 | `EngineCore.step()` | Scheduler event loop + `run_batch/process_batch_result` |
| Batch 状态 | `SchedulerOutput` + request state | `ScheduleBatch` + mixin/组件 |
| KV | block table / coordinator | radix/unified tree + token pool |
| Spec | lookahead slots + proposer/verify | `BaseSpecWorker` + `spec_info` + target verify |
| Attention | selector/enum/class | registry + forward-mode backend selection |

## TP / PP / EP / DP 代码路径

```text
initialize_model_parallel(TP, PP, DP, EP)
          ↓ process groups / rank mapping
Transformer block
  ├─ ColumnParallelLinear → local shard
  │       └─ optional all-gather
  ├─ RowParallelLinear → local partial output
  │       └─ tensor_model_parallel_all_reduce
  ├─ PP stage boundary → send/recv intermediate tensors
  └─ MoE gate → expert token dispatch all-to-all
          ↓
logits / sampler → DP shard gather or rank-local result
```

代码入口：`distributed/parallel_state.py:1977`、`distributed/communication_op.py:12-31`、`model_executor/layers/linear.py:428/1621`、`v1/worker/gpu_worker.py:1179/1216`、`layers/fused_moe/all2all_utils.py`。


## 相关页面

- [[vllm]]
- [[paged-attention]]
- [[radix-attention]]
- [[llm-inference]]
- [[inference-routing]]
