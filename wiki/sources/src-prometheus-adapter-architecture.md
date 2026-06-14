---
title: prometheus-adapter 架构与设计思路分析
tags: [architecture, kubernetes, observability, autoscaling]
date: 2026-06-14
sources: [prometheus-adapter-architecture-analysis.md]
related: ["[[prometheus-adapter]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[llm-d-workload-variant-autoscaler]]"]
---

# prometheus-adapter 架构与设计思路分析

> 原文：`raw/prometheus-adapter-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/prometheus-adapter · 优先级 P0

## 一句话定位

Prometheus 到 Kubernetes custom/external metrics API 的适配层，让 HPA 能基于 QPS、队列长度、业务指标或推理指标扩缩。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ prometheus-adapter         │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Discovery: │ │ Mapper: series │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ APIService │ │ Query renderer │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Discovery | 根据 rules 发现 Prometheus series |
| Mapper | series -> Kubernetes resource/custom/external metric |
| APIService | custom.metrics.k8s.io / external.metrics.k8s.io |
| Query renderer | 把 HPA 请求转成 PromQL |

## 关键数据流

```
Prometheus 抓取业务/系统指标
        │
        ▼
adapter 根据 rules 映射指标
        │
        ▼
HPA 请求 custom/external metrics
        │
        ▼
adapter 执行 PromQL 并返回值
        │
        ▼
HPA 根据指标扩缩 workload
```

## 设计决策与哲学

- **补齐 `custom/external metrics` 维度**：prometheus-adapter 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：metrics-server 给 CPU/memory resource metrics；prometheus-adapter 给自定义/外部指标，是高级 autoscaling 的关键桥。
- **选型价值**：它应和 [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] 一起看，而不是孤立评估。

## 相关页面

- [[prometheus-adapter]]
- [[kubernetes]]
- [[llm-inference]]
- [[model-serving-operator]]
- [[llm-d-workload-variant-autoscaler]]
