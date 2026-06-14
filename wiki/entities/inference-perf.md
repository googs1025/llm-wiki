---
title: inference-perf
tags: [entity, llm-serving, benchmark, kubernetes]
date: 2026-06-14
sources: [inference-perf-architecture-analysis.md]
related: ["[[inference-perf]]", "[[kubernetes]]", "[[llm-d-benchmark]]", "[[llm-inference]]", "[[llm-d-inference-sim]]"]
---

# inference-perf

GenAI inference performance benchmarking tool，用于对 OpenAI-compatible/serving endpoint 做负载、延迟和吞吐测量。 详见 [[src-inference-perf-architecture]]。

## 架构边界

和 llm-d-benchmark 相比，inference-perf 更像单个 benchmark harness；llm-d-benchmark 负责更完整的实验生命周期。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `GenAI benchmark` 能力 | 适合，inference-perf 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-d-benchmark]], [[llm-inference]], [[llm-d-inference-sim]] 组合。 |

## 核心组件

- CLI/config: benchmark 参数与 endpoint 配置
- Load generator: 并发、请求分布、payload 模板
- Metrics collector: latency/throughput/error/token stats
- Reports: 结果输出供 llm-d-benchmark / serving 选型使用

## 选型提示

把 inference-perf 放在 `GenAI benchmark` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
