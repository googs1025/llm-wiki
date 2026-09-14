---
title: SGLang 架构与推理优化
tags: [architecture, llm-serving, radix-cache, kv-cache, inference-optimization]
date: 2026-09-14
sources: [sglang-architecture-analysis.md]
related: [[sglang]], [[vllm]], [[radix-attention]], [[paged-attention]], [[llm-inference]]
---

# SGLang 架构与推理优化

> 原文：`raw/sglang-architecture-analysis.md` · 仓库：`/Users/zhenyu.jiang/sglang` · 版本：local HEAD `2fd835b9c1`

## 一句话定位

[[sglang]] 是高性能 LLM serving runtime，核心差异是 [[radix-attention]]：用 radix tree 做 token-level KV prefix sharing；再以连续批、chunked prefill、融合 kernel、投机解码和 TP/PP/EP/DP 构成执行管线。

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

## 请求与缓存数据流

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

## 推理优化要点

- **KV**：RadixCache 做 token-level 前缀共享；HiCache 提供 GPU/host/storage 分层；量化 KV 降低容量；P/D 分离搬运 KV。
- **连续批**：EXTEND/DECODE/MIXED 与 chunked prefill 在 TTFT、ITL、吞吐间调节。
- **融合**：attention backend、sgl-kernel、JIT/torch.compile、CUDA Graph、fused MoE/量化 kernel 减少 launch 和中间读写。
- **并行**：TP 切权重，PP 切层，EP 分布 MoE 专家，DP 分区请求/批/KV；DP attention 可复制 attention、保留 FFN/MoE 的 TP/EP。

## 关键设计

- Radix tree 换取更细粒度 prefix reuse，同时增加树维护、eviction 与跨 rank locality 复杂度。
- Scheduler 只生成紧凑 batch/attention metadata，ModelRunner 专注 GPU 执行，backend 可替换。
- 结构化程序、会话缓存、投机解码和 P/D/EPD 复用同一套 runtime 扩展点。

## 代码级关键路径

```text
run_event_loop()
  → get_next_batch_to_run()
  → ScheduleBatch(EXTEND / DECODE / MIXED)
  → match_prefix() + alloc_for_extend/decode()
  → run_batch() / ModelRunner
  → Attention Backend（按 ForwardMode dispatch）
  → process_batch_result()
  → cache_finished_req() / next batch
```

```text
run_event_loop()
  ├─ 接收 request / abort / control message
  ├─ get_next_batch_to_run()
  │    ├─ 选择 running batch 继续 decode
  │    ├─ 从 waiting queue 取新请求
  │    ├─ match prefix / check memory
  │    └─ 形成 EXTEND / DECODE / MIXED ForwardMode
  ├─ run_batch(ScheduleBatch)
  │    └─ TP worker / ModelRunner forward
  ├─ process_batch_result()
  │    ├─ 更新 Req output / seq_lens
  │    ├─ 处理 stop / abort / grammar
  │    ├─ verify speculative result
  │    └─ cache_finished_req()
  └─ 继续下一轮 event loop
```

SGLang 当前以 `ScheduleBatch`、`UnifiedRadixCache`、`ForwardMode` 和 `BaseSpecWorker` 连接调度、KV、Attention 与投机解码。P/D 侧通过 `DecodeRequest`、transfer queue 和 connection contract 等状态对象等待/接收 KV；HiCache 可继续从 host/storage tier 恢复 prefix。

## 与 vLLM 的代码实现对比

| 维度 | SGLang | vLLM |
|---|---|---|
| 主循环 | `run_event_loop → get_next_batch_to_run → run_batch → process_batch_result` | `EngineCore.step → schedule → execute_model → update_from_output` |
| Batch | `ScheduleBatch` + mixins | `SchedulerOutput` + Request state |
| KV | `UnifiedRadixCache` + token/page pools | `KVCacheManager` + block coordinator/table |
| Spec | `BaseSpecWorker` + `SpecInput` + target verify | proposer + lookahead slots + scheduled spec tokens |
| Attention | registry 创建，ForwardMode 二次选择 | selector 选择 backend class/enum |

## TP / PP / EP / DP 与 Spec KV 修正

```text
bootstrap rank geometry
          ↓
ParallelState(TP / PP / DP-attn / EP / MoE-DP)
          ↓
ForwardBatch / ScheduleBatch metadata
  ├─ TP Linear / Attention head shard → all-reduce/gather
  ├─ PP stage → activation send/recv
  ├─ EP MoE gate → token all-to-all → local experts → reduce
  └─ DP attention → request/batch partition + rank-consistent padding
          ↓
tp_worker.forward_batch_generation()
          ↓
merge output / next Scheduler step
```

```text
draft worker propose → optimistic draft KV / spec_info
        ↓ target verify (TARGET_VERIFY)
accepted draft count + bonus token
        ├─ commit kv_committed_len / output / grammar
        └─ discard rejected tail / restore live seq_lens
        ↓
batch_result_processor → next draft or normal decode
```

```text
draft worker propose
        ↓ optimistic draft KV / spec_info
target verify (TARGET_VERIFY)
        ↓ accepted draft count + bonus token
┌───────────────┴────────────────┐
│ accepted                        │ rejected tail
│ kv_committed_len += accepted    │ drop/discard tail
│ commit output + grammar state   │ restore live seq_lens
└───────────────┬────────────────┘
                ↓
batch_result_processor
                ↓
Req.seq_lens / kv_committed_len / spec_info
                ↓
next draft or normal decode
```

代码入口：`distributed/bootstrap.py:271-290`、`distributed/parallel_state.py:649/1155/1280`、`scheduler_components/batch_result_processor.py:776-804`、`speculative/dflash_info_v2.py:160-218`。
| P/D | DecodeRequest + transfer queue/receiver | KVConnector metadata + worker hooks |

## 相关页面

- [[sglang]]
- [[vllm]]
- [[radix-attention]]
- [[paged-attention]]
- [[llm-inference]]
