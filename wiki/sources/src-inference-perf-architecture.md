---
title: inference-perf 架构与设计思路分析
tags: [architecture, llm-serving, benchmark, kubernetes]
date: 2026-06-14
sources: [inference-perf-architecture-analysis.md]
related: ["[[inference-perf]]", "[[kubernetes]]", "[[llm-d-benchmark]]", "[[llm-inference]]", "[[llm-d-inference-sim]]"]
---

# inference-perf 架构与设计思路分析

> 原文：`raw/inference-perf-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/inference-perf · 优先级 P1

## 一句话定位

GenAI inference performance benchmarking tool，用于对 OpenAI-compatible/serving endpoint 做负载、延迟和吞吐测量。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ inference-perf             │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CLI/config │ │ Load generator │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Metrics co │ │ Reports: 结果输出供 │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CLI/config | benchmark 参数与 endpoint 配置 |
| Load generator | 并发、请求分布、payload 模板 |
| Metrics collector | latency/throughput/error/token stats |
| Reports | 结果输出供 llm-d-benchmark / serving 选型使用 |

## 关键数据流

```
用户指定 endpoint/model/workload
        │
        ▼
工具生成请求负载
        │
        ▼
并发调用 inference endpoint
        │
        ▼
收集 TTFT/ITL/latency/throughput
        │
        ▼
输出 benchmark report
```

## 设计决策与哲学

- **补齐 `GenAI benchmark` 维度**：inference-perf 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：和 llm-d-benchmark 相比，inference-perf 更像单个 benchmark harness；llm-d-benchmark 负责更完整的实验生命周期。
- **选型价值**：它应和 [[llm-d-benchmark]], [[llm-inference]], [[llm-d-inference-sim]] 一起看，而不是孤立评估。

## 相关页面

- [[inference-perf]]
- [[kubernetes]]
- [[llm-d-benchmark]]
- [[llm-inference]]
- [[llm-d-inference-sim]]
