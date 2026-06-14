---
title: llm-d Workload Variant Autoscaler
tags: [entity, llm-serving, autoscaling, kubernetes, llm-d]
date: 2026-06-13
sources: [llm-d-workload-variant-autoscaler-architecture-analysis.md]
related: [[llm-d]], [[gateway-api-inference-extension]], [[model-serving-operator]], [[llm-inference]], [[kubernetes]]
---

# llm-d Workload Variant Autoscaler

llm-d Workload Variant Autoscaler（WVA）是面向分布式 [[llm-inference]] 的 Kubernetes variant autoscaler，用 `VariantAutoscaling` CRD 把同一模型/InferencePool 下不同硬件、角色、成本或配置的 serving variant 纳入一个全局扩缩决策。详见 [[src-llm-d-workload-variant-autoscaler-architecture]]。

## 架构边界

WVA 不直接替代 HPA/KEDA。它通过 Prometheus、GPU inventory、[[gateway-api-inference-extension]] InferencePool、scale target 和 capacity model 计算 desired allocation，然后把 desired/current replica 指标暴露给 HPA/KEDA 这类 autoscaler 执行。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 同一模型有多个 serving variant | 适合，例如不同 GPU、prefill/decode、batch/interactive 或成本档位。 |
| 希望 autoscaling 理解 InferencePool/modelID | 适合，比通用 HPA 更有 serving 语义。 |
| 只需要单 Deployment CPU/GPU utilization 扩缩 | 可能 HPA/KEDA 直接够用。 |
| 没有 Prometheus/custom metrics 基础设施 | 需要先补可观测和 metrics API。 |

## 同类对比

| 维度 | [[llm-d-workload-variant-autoscaler]] | HPA / KEDA | [[kserve]] / Knative autoscaling |
|---|---|---|---|
| 决策对象 | 多 variant allocation | 单 workload 或 event source | service/revision/model service |
| 推理语义 | modelID / InferencePool / variant cost | 通用指标 | model serving 生命周期 |
| 执行方式 | 发指标给 HPA/KEDA | scale subresource | controller/autoscaler |

## 选型提示

当 serving fleet 开始出现 prefill/decode 分离、不同 GPU 型号、不同成本档位或不同 SLO 池时，WVA 才有明显价值。单模型单部署阶段先把 [[model-serving-operator]] 和普通 autoscaling 跑稳更重要。
