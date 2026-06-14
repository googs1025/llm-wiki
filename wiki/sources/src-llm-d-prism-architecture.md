---
title: llm-d Prism 架构与设计思路分析
tags: [architecture, llm-serving, observability, benchmark]
date: 2026-06-14
sources: [llm-d-prism-architecture-analysis.md]
related: ["[[llm-d-prism]]", "[[kubernetes]]", "[[llm-d-benchmark]]", "[[llm-inference]]"]
---

# llm-d Prism 架构与设计思路分析

> 原文：`raw/llm-d-prism-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-prism · 优先级 P1

## 一句话定位

llm-d Prism 是分布式推理性能分析 dashboard，把 benchmark 和运行数据做交互式分析，用于理解 P/D、路由和资源配置的效果。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Benchmark and runtime data                                                 │
│ Runs, traces, latency, throughput, token counts, and error signals feed    │
│ analysis.                                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ llm-d Prism backend                                                        │
│ Ingests benchmark output and models experiment/run/config dimensions.      │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Dashboard                                                                  │
│ Visualizes latency, throughput, token breakdowns, topology, and P/D        │
│ comparisons.                                                               │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Serving tuning decisions for routing, batching, topology, and resource     │
│ sizing.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Frontend/dashboard | experiment visualization |
| Data ingestion | benchmark result files or APIs |
| Analysis views | latency/throughput/token/error breakdown |
| Comparison workflow | stack/config/run dimensions |

## 关键数据流

```
导入 benchmark/run 数据
        │
        ▼
解析实验维度和指标
        │
        ▼
可视化 latency/throughput/token stats
        │
        ▼
对比不同 serving 配置
        │
        ▼
输出调参判断
```

## 设计决策与哲学

- **补齐 `performance analysis` 维度**：llm-d Prism 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：llm-d-benchmark 负责跑实验；Prism 负责看懂实验结果。
- **选型价值**：它应和 [[llm-d-benchmark]], [[llm-inference]] 一起看，而不是孤立评估。

## 相关页面

- [[llm-d-prism]]
- [[kubernetes]]
- [[llm-d-benchmark]]
- [[llm-inference]]
