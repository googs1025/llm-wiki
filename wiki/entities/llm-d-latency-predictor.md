---
title: llm-d Latency Predictor
tags: [entity, llm-serving, latency, inference-routing]
date: 2026-06-14
sources: [llm-d-latency-predictor-architecture-analysis.md]
related: ["[[llm-d-latency-predictor]]", "[[kubernetes]]", "[[llm-d]]", "[[inference-routing]]"]
---

# llm-d Latency Predictor

llm-d Latency Predictor 是给 llm-d inference scheduler 的 ML-based latency scoring service，用预测延迟信号增强 endpoint picking。 详见 [[src-llm-d-latency-predictor-architecture]]。

## 架构边界

它不是 router 本体，而是 router/scorer 的外部预测信号。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `latency predictor` 能力 | 适合，llm-d Latency Predictor 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-d]], [[inference-routing]] 组合。 |

## 核心组件

- Service API: latency scoring endpoint
- Model/features: 请求、模型、endpoint 或历史指标特征
- Integration: llm-d scheduler/router scoring
- Training/evaluation utilities

## 选型提示

把 llm-d Latency Predictor 放在 `latency predictor` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
