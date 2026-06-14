---
title: llm-d Prism
tags: [entity, llm-serving, observability, benchmark]
date: 2026-06-14
sources: [llm-d-prism-architecture-analysis.md]
related: ["[[llm-d-prism]]", "[[kubernetes]]", "[[llm-d-benchmark]]", "[[llm-inference]]"]
---

# llm-d Prism

llm-d Prism 是分布式推理性能分析 dashboard，把 benchmark 和运行数据做交互式分析，用于理解 P/D、路由和资源配置的效果。 详见 [[src-llm-d-prism-architecture]]。

## 架构边界

llm-d-benchmark 负责跑实验；Prism 负责看懂实验结果。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `performance analysis` 能力 | 适合，llm-d Prism 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-d-benchmark]], [[llm-inference]] 组合。 |

## 核心组件

- Frontend/dashboard: experiment visualization
- Data ingestion: benchmark result files or APIs
- Analysis views: latency/throughput/token/error breakdown
- Comparison workflow: stack/config/run dimensions

## 选型提示

把 llm-d Prism 放在 `performance analysis` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
