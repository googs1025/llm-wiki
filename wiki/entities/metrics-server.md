---
title: metrics-server
tags: [entity, kubernetes, observability, autoscaling]
date: 2026-06-14
sources: [metrics-server-architecture-analysis.md]
related: ["[[metrics-server]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[llm-d-workload-variant-autoscaler]]"]
---

# metrics-server

Kubernetes 资源指标管道，把 kubelet summary/metrics 暴露成 `metrics.k8s.io`，供 HPA/VPA/kubectl top 使用。 详见 [[src-metrics-server-architecture]]。

## 架构边界

metrics-server 只服务资源指标，不是 Prometheus 替代品；custom/external metrics 需要 prometheus-adapter 等组件。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `可观测 / autoscaling` 能力 | 适合，metrics-server 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] 组合。 |

## 核心组件

- Scraper: 周期访问 kubelet metrics
- Storage: 只保留最新 CPU/memory resource metrics
- APIService: 注册 metrics.k8s.io aggregated API
- Consumers: HPA/VPA/kubectl top

## 选型提示

把 metrics-server 放在 `可观测 / autoscaling` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
