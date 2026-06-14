---
title: prometheus-adapter
tags: [entity, kubernetes, observability, autoscaling]
date: 2026-06-14
sources: [prometheus-adapter-architecture-analysis.md]
related: ["[[prometheus-adapter]]", "[[kubernetes]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[llm-d-workload-variant-autoscaler]]"]
---

# prometheus-adapter

Prometheus 到 Kubernetes custom/external metrics API 的适配层，让 HPA 能基于 QPS、队列长度、业务指标或推理指标扩缩。 详见 [[src-prometheus-adapter-architecture]]。

## 架构边界

metrics-server 给 CPU/memory resource metrics；prometheus-adapter 给自定义/外部指标，是高级 autoscaling 的关键桥。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `custom/external metrics` 能力 | 适合，prometheus-adapter 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] 组合。 |

## 核心组件

- Discovery: 根据 rules 发现 Prometheus series
- Mapper: series -> Kubernetes resource/custom/external metric
- APIService: custom.metrics.k8s.io / external.metrics.k8s.io
- Query renderer: 把 HPA 请求转成 PromQL

## 选型提示

把 prometheus-adapter 放在 `custom/external metrics` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
