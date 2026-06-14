---
title: llm-d Benchmark
tags: [entity, llm-serving, benchmark, llm-d]
date: 2026-06-13
sources: [llm-d-benchmark-architecture-analysis.md]
related: [[llm-d]], [[llm-d-inference-sim]], [[llm-inference]], [[model-serving-operator]]
---

# llm-d Benchmark

llm-d Benchmark 是 [[llm-d]] 生态的 Kubernetes 实验编排和评测工具，用 `llmdbenchmark` CLI 把 standup、smoketest、run、result collection、analysis、teardown 串成可复现流程。详见 [[src-llm-d-benchmark-architecture]]。

## 架构边界

它不是单一压测 engine。真正的负载生成可以来自 inference-perf、GuideLLM、vLLM benchmark 等 harness；llm-d Benchmark 负责渲染 scenario/specification、部署 stack、发现 endpoint、运行 harness、收集结果和保留 workspace。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要复现实验配置和 Kubernetes manifests | 适合，workspace 保留 rendered config、manifest、log、result。 |
| 需要比较多套 llm-d stack 或多组参数 | 适合，global step 顺序执行，per-stack step 可并行。 |
| 需要无 GPU 先验证控制面 | 可与 [[llm-d-inference-sim]] 配合。 |
| 只想测单个本地 vLLM server 的原始吞吐 | 可能直接用 harness 更轻。 |

## 同类对比

| 维度 | [[llm-d-benchmark]] | inference-perf / GuideLLM | vLLM benchmark |
|---|---|---|---|
| 主职责 | 实验生命周期编排 | 负载生成和测量 | engine-specific benchmark |
| 事实来源 | workspace + rendered spec | harness config/result | 脚本参数/result |
| 适合问题 | stack 对比、参数 sweep、部署到结果闭环 | 单次性能测量 | vLLM 基线性能 |

## 选型提示

如果目标是“快速理解 [[llm-d]] 部署参数如何影响结果”，优先看 llm-d Benchmark；如果目标是“某个 engine 的 kernel/throughput 极限”，它只是外围编排器，不能替代 engine 自带 benchmark。
