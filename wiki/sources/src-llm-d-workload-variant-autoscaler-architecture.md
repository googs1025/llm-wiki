---
title: llm-d Workload Variant Autoscaler 架构与设计思路分析
tags: [architecture, llm-serving, autoscaling, kubernetes]
date: 2026-06-13
sources: [llm-d-workload-variant-autoscaler-architecture-analysis.md]
related: [[llm-d-workload-variant-autoscaler]], [[llm-d]], [[model-serving-operator]], [[llm-inference]], [[gateway-api-inference-extension]]
---

# llm-d Workload Variant Autoscaler 架构与设计思路分析

> 原文：`raw/llm-d-workload-variant-autoscaler-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-workload-variant-autoscaler · 分析版本 HEAD `526ce85`

## 一句话定位

[[llm-d-workload-variant-autoscaler]] 是面向分布式 [[llm-inference]] 的 Kubernetes 全局 autoscaler，核心对象是同一模型/InferencePool 下的多个 serving variant。它通过 Prometheus、[[gateway-api-inference-extension]]、KEDA/HPA、GPU inventory 和 scale target 状态，把“不同硬件/角色/成本的变体应该各扩多少副本”转成外部指标和 status。

## 核心架构图

```
┌──────────────────────────────────────────────┐
│ VariantAutoscaling CRD                       │
│ api/v1alpha1                                 │
│ modelID / min-max / variantCost / targetRef  │
└───────────────┬──────────────────────────────┘
                │ reconcile
┌───────────────▼──────────────────────────────┐
│ controller-runtime Manager                   │
│ cmd/main.go                                  │
│ - VariantAutoscaling reconciler              │
│ - HPA / KEDA ScaledObject reconciler         │
│ - InferencePool reconciler                   │
└───────┬─────────────┬──────────────┬─────────┘
        │             │              │
        │ target refs │ metrics      │ pool state
        ▼             ▼              ▼
┌────────────┐ ┌──────────────┐ ┌──────────────────────┐
│Deployment/ │ │ Prometheus   │ │ Gateway API          │
│StatefulSet/│ │ request rate │ │ InferencePool        │
│LWS scale   │ │ queue/cache  │ │ Endpoint / variants  │
└─────┬──────┘ └──────┬───────┘ └──────────┬───────────┘
      │               │                    │
      └───────────────▼────────────────────┘
                      │
┌─────────────────────▼────────────────────────┐
│ Saturation Engine                            │
│ internal/engines/saturation                  │
│ - replica metrics collector                  │
│ - capacity knowledge store                   │
│ - GPU inventory / limiter                    │
│ - queueing model analyzer                    │
│ - cost-aware optimizer                       │
└─────────────────────┬────────────────────────┘
                      │ desired optimized allocation
                      ▼
┌──────────────────────────────────────────────┐
│ Actuator / Metrics Emitter                   │
│ internal/actuator                            │
│ emits desired/current replica metrics        │
└───────────────┬──────────────────────────────┘
                │ external/custom metrics
        ┌───────▼────────┐
        │ HPA / KEDA     │
        │ scale subresource│
        └───────┬────────┘
                ▼
         Serving variants
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API 层 | 定义 `VariantAutoscaling` spec/status/conditions。 |
| Manager 启动层 | 注册 K8s、Prometheus Operator、Gateway API Inference Extension、KEDA、LWS 等 scheme，组装 reconciler 和 engines。 |
| Reconcile 层 | 解析 scale target、更新 conditions、读取 decision cache、patch status、watch workload 和 InferencePool。 |
| Metrics 收集 | 采集 request rate、replica、queue/cache/capacity 相关指标。 |
| 优化引擎 | 维护 capacity store、GPU inventory、queueing/saturation analyzer、cost-aware optimizer。 |
| 执行动作 | 发出 desired/current replica 等指标供 HPA/KEDA 消费。 |

## 关键数据流

```
用户创建 VariantAutoscaling
        │
        ▼
Reconciler resolve scaleTargetRef + InferencePool/modelID
        │
        ├── 写 TargetResolved / MetricsAvailable / OptimizationReady conditions
        └── 注册 namespace / watched resources
        │
        ▼
Saturation Engine 周期采集 Prometheus + replica + GPU inventory
        │
        ├── 估算 variant capacity / saturation
        ├── 使用 queueing model 推断请求压力
        ├── 应用 GPU / budget / min-max 约束
        └── cost-aware optimizer 计算 desired allocation
        │
        ▼
DecisionCache / VariantAutoscaling status
        │
        ▼
Actuator 发出 desired replica metrics
        │
        ▼
HPA 或 KEDA 读取 external/custom metrics
        │
        ▼
Deployment / StatefulSet / LWS 副本数变化
```

## 设计决策与哲学

- **Variant 是 autoscaling 的一等对象**：它不只看单个 Deployment 的 CPU/GPU 指标，而是把同一模型下不同硬件、角色或配置变体纳入一个优化问题。
- **不直接抢 HPA/KEDA 的职责**：WVA 主要发指标，实际 scale 仍由 HPA/KEDA 完成。
- **Gateway API Inference Extension 是 serving 语义入口**：它需要理解 InferencePool 和 endpoint pool，而不是只做通用 workload autoscaling。
- **优化引擎需要容量知识而不只是当前利用率**：capacity store、GPU inventory、queueing analyzer 和 optimizer 共同估计 serving capacity curve。

## 相关页面

- [[llm-d-workload-variant-autoscaler]]
- [[llm-d]]
- [[model-serving-operator]]
- [[gateway-api-inference-extension]]
- [[llm-inference]]
