---
title: LLM Serving Performance
tags: [concept, llm-inference, llm-serving, performance, benchmarking]
date: 2026-10-03
sources: [src-inference-perf-architecture, src-llm-d-benchmark-architecture, src-vllm-architecture, src-sglang-architecture]
related: [continuous-batching, llm-inference, disaggregated-serving, inference-routing, llm-d-benchmark, inference-perf, vllm, sglang]
---

# LLM Serving Performance

LLM serving 的性能不是单个吞吐数字，而是给定工作负载、硬件和 SLO 下的容量边界。[[continuous-batching]]、KV 复用和 [[disaggregated-serving]] 都会改变排队与资源分配；比较前必须先固定工作负载封套。

## Workload Envelope

一个可复现实验至少说明：模型及 revision、硬件与 GPU 数量、量化方式、TP/PP/DP/EP 并行配置、输入/输出长度分布、并发或到达过程、streaming 模式、cache-hit ratio，以及报告的百分位。缺少任一项时，结果最多是局部观察，不能用于横向排名。

长度应记录分布而非只写“平均 1K token”：长 prompt 放大 prefill 和 KV 占用，长输出放大 decode 时间；cache-hit ratio 又会改变实际 prefill 工作量。[[inference-routing]] 若按前缀或会话粘性选端点，也会改变该命中率，因此路由策略属于实验条件，而非背景信息。

## Latency Metrics

- **TTFT（time to first token）**：请求发出到收到第一个可见 token 的时间；通常包含排队、tokenize、prefill、调度和网络路径中已发生的部分。
- **ITL / TPOT（inter-token latency / time per output token）**：相邻输出 token 的时间间隔。TPOT 有时指单请求 decode 间隔，有时是全请求总时长除输出 token 数；报告必须标注定义、是否排除首 token、按 token 还是按请求聚合，并给出 p50/p95/p99。
- **端到端延迟**：客户端开始发送到请求完成的总时间。它覆盖 TTFT 后的所有流式 token，并受输出长度、客户端读取和网络影响。

平均值无法表明 SLO 是否可守住。面向交互服务应同时看 TTFT、ITL/TPOT 与端到端延迟的 percentile，并将错误、超时和取消请求单列；否则尾部排队会被均值掩盖。

## Throughput and Goodput

**请求吞吐**是单位时间完成的请求数，**token 吞吐**应明确是生成 token、处理 token，还是二者之和。二者不能互相替代：同样的请求/s 在不同输出长度下代表不同 GPU 工作量。

**goodput** 是满足预先声明质量门槛的有效产出，例如同时满足 TTFT、ITL 和成功率 SLO 的请求/s 或 token/s。它必须写清门槛和分母，不能把限流、取消或超时静默排除。并发是同时在途的请求数；它既可由 closed-loop 客户端控制，也可由 arrival rate 在 open-loop 负载下自然形成，两种实验不可直接等价。

## Capacity Envelope

容量评估从到达率、服务时间和排队开始：当 arrival rate 接近系统在该长度分布下的稳定服务能力时，队列会增长，tail latency 常先恶化；超过饱和点后，增加并发可能只增加排队、抢占或失败。[[continuous-batching]] 能提高资源利用率，却不取消 KV 容量、网络、前后处理和调度开销这些约束。

没有跨模型和引擎通用的容量公式。实际容量应以目标 SLO 下的最大稳定 arrival rate 或并发表示，并同时观察 GPU/显存、KV 使用率、队列深度、TTFT/ITL percentile 与错误率。[[disaggregated-serving]] 可分别扩展 prefill 与 decode，但增加 KV 传输和路由边界，需按同一 SLO 重新测量。

## Benchmark Matrix

下表是一次实用的最小矩阵；每格都要保留配置文件、原始结果和 percentile，而不是只保留图表。[[inference-perf]] 可作为负载与指标采集 harness，[[llm-d-benchmark]] 用于部署场景、实验编排和结果留存。

| 维度 | 最小覆盖 | 必报结果 | 目的 |
|---|---|---|---|
| 输入/输出长度 | 短/短、长/短、短/长、长/长，使用真实分布复验 | TTFT、ITL/TPOT、端到端 p50/p95/p99 | 分开 prefill 与 decode 压力 |
| 到达模式 | 低负载、接近饱和、超过 SLO 边界；open/closed loop 分列 | arrival rate、并发、队列、错误率、goodput | 找到稳定容量而非峰值 |
| 缓存条件 | 冷缓存、固定前缀命中、真实混合命中率 | token 吞吐、KV 使用率、命中率 | 防止把复用收益误当基础算力 |
| Serving 形态 | streaming/non-streaming；同置与 P/D 分离 | 首 token、完成延迟、网络/传输指标 | 暴露流式与传输代价 |
| 系统配置 | 硬件、量化、TP/PP/DP/EP、engine/version、policy | 完整 config 与 percentile | 让结果可复现、可归因 |

## Reading Results Safely

任何有效比较都必须在结论旁重述：model、hardware、quantization、TP/PP/DP/EP、input/output length distribution、concurrency、streaming mode、cache-hit ratio 和 percentiles。若其中一项变化，应视作新的实验单元，不应把两行结果的差异简单归因于 engine 或单个开关。

阅读结果时先问“哪个 SLO 下、哪种负载、哪些失败计入分母”，再问平均吞吐。[[vllm]]、[[sglang]] 的实现与版本可能具有不同 scheduler、cache、kernel 和并行路径；它们的 benchmark 数字是特定配置的证据，而不是通用排序。对接 [[inference-routing]] 或采用 [[continuous-batching]] 后，也应重新测量端到端路径，而不是从微基准直接推导线上 capacity。
