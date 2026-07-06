---
title: Kubernetes Autoscaling Design
tags: [concept, kubernetes, autoscaling, hpa, metrics, kep]
date: 2026-07-06
sources: [src-kubernetes-resource-orchestration-keps.md]
related: [[kubernetes-resource-orchestration]], [[kubernetes]], [[metrics-server]], [[prometheus-adapter]], [[karpenter]], [[kubernetes-scheduling-design]], [[kubernetes-node-design]]
---

# Kubernetes Autoscaling Design

Kubernetes autoscaling design 关注控制器如何把 metrics、目标对象和策略转成 replica 或容量变化。当前 KEP 集合主要围绕 HPA API 的表达能力演进。

## HPA 设计主线

| 能力 | 代表 KEP | 设计含义 |
|---|---|---|
| API 稳定化 | `2702-graduate-hpa-api-to-GA` | 将 v2beta2 autoscaling API 推向 GA，承载多指标和 behavior。 |
| 扩缩速度 | `853-configurable-hpa-scale-velocity` | 用 per-HPA `behavior` 配置 scale up/down policies、selectPolicy 和 stabilization window。 |
| 容忍度 | `4951-configurable-hpa-tolerance` | 把全局 tolerance 下放到 workload，允许不同应用对抖动和响应速度做不同取舍。 |
| 指标精度 | `117-hpa-metrics-specificity` | custom/external metrics 加 label selector，避免必须改造指标管道才能精确选择序列。 |
| 容器级指标 | `1610-container-resource-autoscaling` | 让 HPA 可以针对主容器或关键 sidecar 的 CPU/memory，而不是 Pod 总和。 |
| 从零启动 | `2021-scale-from-zero` | 对 object/external metrics 支持 0 副本场景，依赖无 Pod 时仍可读的外部信号。 |
| 指标容错 | `5679-external-metric-fallback` | 外部指标获取失败时提供 fallback，避免 metrics adapter 问题直接变成错误扩缩。 |
| Pod 选择准确性 | `5325-hpa-pod-selection-accuracy` | 降低 label selector 匹配到非目标 Pod 的风险，使 HPA 指标集合更接近真实 target。 |

## 核心判断

HPA 已从“CPU utilization 控制器”演进成 workload-specific policy controller。真正的设计问题是：指标是否代表目标 workload、控制器是否能容忍噪声、扩缩是否符合业务成本和延迟、失败时是否保守。

## 和其他资源编排线的关系

- 和 [[kubernetes-scheduling-design]]：HPA 增加副本后，scheduler 负责放置；如果没有可行节点，pending Pod 又会驱动 [[karpenter]] 或 Cluster Autoscaler。
- 和 [[kubernetes-node-design]]：container metrics、resource metrics、PSI、pod resource exposure 等信号来自 kubelet/runtime/metrics 管道。
- 和 [[metrics-server]]：资源指标是 HPA 的基础输入。
- 和 [[prometheus-adapter]]：custom/external metrics 是业务指标扩缩的主要桥接层。

## 选型提示

在线服务优先检查 `behavior.scaleUp/scaleDown` 和 `tolerance`，否则容易在流量峰值或低谷时过度保守或过度抖动。带 sidecar 的服务应优先考虑 container resource metrics，否则主容器压力可能被 sidecar 低使用率稀释。基于队列长度或外部业务指标扩缩时，必须验证 metrics adapter 的失败策略和 fallback 行为。
