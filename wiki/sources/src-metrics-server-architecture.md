---
title: metrics-server 架构与设计思路分析
tags: [architecture, kubernetes, observability, autoscaling]
date: 2026-06-14
sources: [metrics-server-architecture-analysis.md]
related: ["[[metrics-server]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[llm-d-workload-variant-autoscaler]]"]
---

# metrics-server 架构与设计思路分析

> 原文：`raw/metrics-server-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/metrics-server · 优先级 P0

## 一句话定位

Kubernetes 资源指标管道，把 kubelet summary/metrics 暴露成 `metrics.k8s.io`，供 HPA/VPA/kubectl top 使用。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Node resource usage                                                        │
│ Kubelets expose CPU and memory usage through stats and summary APIs.       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ metrics-server                                                             │
│ Scrapes kubelets, normalizes samples, and serves an aggregated APIService. │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Resource metrics API                                                       │
│ metrics.k8s.io backs kubectl top and basic Kubernetes autoscaling.         │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Consumers                                                                  │
│ HPA, VPA, dashboards, and platform controllers read current resource       │
│ metrics.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Scraper | 周期访问 kubelet metrics |
| Storage | 只保留最新 CPU/memory resource metrics |
| APIService | 注册 metrics.k8s.io aggregated API |
| Consumers | HPA/VPA/kubectl top |

## 关键数据流

```
kubelet 暴露节点和 Pod 指标
        │
        ▼
metrics-server 拉取并聚合
        │
        ▼
aggregated API 提供 NodeMetrics/PodMetrics
        │
        ▼
HPA/VPA/kubectl top 读取
```

## 设计决策与哲学

- **补齐 `可观测 / autoscaling` 维度**：metrics-server 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：metrics-server 只服务资源指标，不是 Prometheus 替代品；custom/external metrics 需要 prometheus-adapter 等组件。
- **选型价值**：它应和 [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] 一起看，而不是孤立评估。

## 相关页面

- [[metrics-server]]
- [[kubernetes]]
- [[llm-inference]]
- [[model-serving-operator]]
- [[llm-d-workload-variant-autoscaler]]
