---
title: llm-d Latency Predictor 架构与设计思路分析
tags: [architecture, llm-serving, latency, inference-routing]
date: 2026-06-14
sources: [llm-d-latency-predictor-architecture-analysis.md]
related: ["[[llm-d-latency-predictor]]", "[[kubernetes]]", "[[llm-d]]", "[[inference-routing]]"]
---

# llm-d Latency Predictor 架构与设计思路分析

> 原文：`raw/llm-d-latency-predictor-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-latency-predictor · 优先级 P1

## 一句话定位

llm-d Latency Predictor 是给 llm-d inference scheduler 的 ML-based latency scoring service，用预测延迟信号增强 endpoint picking。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ llm-d Latency Predictor    │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Service AP │ │ Model/features │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Integratio │ │ Training/evalu │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Service API | latency scoring endpoint |
| Model/features | 请求、模型、endpoint 或历史指标特征 |
| Integration | llm-d scheduler/router scoring |
| Training/evaluation utilities | Training/evaluation utilities |

## 关键数据流

```
scheduler 准备候选 endpoint
        │
        ▼
调用 latency predictor 计算 score
        │
        ▼
与负载/KV/健康分数融合
        │
        ▼
选择 endpoint
        │
        ▼
真实延迟回流用于校准
```

## 设计决策与哲学

- **补齐 `latency predictor` 维度**：llm-d Latency Predictor 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它不是 router 本体，而是 router/scorer 的外部预测信号。
- **选型价值**：它应和 [[llm-d]], [[inference-routing]] 一起看，而不是孤立评估。

## 相关页面

- [[llm-d-latency-predictor]]
- [[kubernetes]]
- [[llm-d]]
- [[inference-routing]]
