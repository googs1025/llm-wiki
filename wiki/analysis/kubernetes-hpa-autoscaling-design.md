---
title: Kubernetes HPA Autoscaling Design
tags: [analysis, kubernetes, kep, sig-autoscaling, hpa, metrics, autoscaling, design-deep-dive]
date: 2026-07-07
sources: [src-kubernetes-keps-design-tracking.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/4951-configurable-hpa-tolerance/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/2021-scale-from-zero/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/5679-external-metric-fallback/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/1610-container-resource-autoscaling/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/5325-hpa-pod-selection-accuracy/README.md, /Users/zhenyu.jiang/enhancements/keps/sig-autoscaling/5030-attach-limit-autoscaler/README.md]
related: [[kubernetes]], [[kubernetes-keps-design-tracking]], [[kubernetes-keps-implementation-matrix]], [[metrics-server]], [[prometheus-adapter]], [[karpenter]], [[kubernetes-workload-automation]], [[llm-d-workload-variant-autoscaler]]
---

# Kubernetes HPA Autoscaling Design

这页拉出 `sig-autoscaling` 中最值得详细讲解的一组设计文档：HPA tolerance、container resource metrics、pod selection accuracy、scale from zero、external metric fallback，以及 Cluster Autoscaler 的 attach limit integration。逐个 KEP 的 Alpha/Beta/GA、是否实现和 feature gate 见 [[kubernetes-keps-implementation-matrix]]。

## 一句话定位

这组 KEP 的共同目标是让 HPA 从“基于粗粒度全局参数和 selector 的普通副本数调节器”，变成更可解释、更可靠、更适合高成本 workload 的 autoscaling 控制面。

## HPA 的设计问题

HPA 的核心公式是根据当前指标与目标指标的 ratio 推导 desired replicas。问题在生产里通常不在公式本身，而在这些边界：

- 10% 全局 tolerance 对小 workload 和大 workload 都不合适。
- Pod selector 可能选中同 label 但不属于目标 workload 的 Pod。
- sidecar-heavy workload 中，Pod 总资源指标会稀释真正主容器的信号。
- 外部指标不可用时，HPA 缺少保守 fallback。
- `replicas: 0` 既可能表示用户手动暂停，也可能表示自动 scale-to-zero，语义混乱。
- Cluster Autoscaler 需要理解 scheduler 之外的容量约束，例如 CSI attach limit。

## Configurable HPA Tolerance

`4951-configurable-hpa-tolerance` 给 `HPAScalingRules` 增加 `tolerance` 字段。它的设计非常小，但影响很大：

```text
HPA
  spec.behavior.scaleUp.tolerance
  spec.behavior.scaleDown.tolerance
```

过去 tolerance 是 kube-controller-manager 的全局参数，默认 10%。这意味着：

- 100 个副本的 workload，7% 负载上涨不会扩到 107。
- GPU/LLM serving workload 的每个副本很贵，scale-down tolerance 又不能太激进。
- scale-up 和 scale-down 通常应该有不同策略。

新字段让 workload owner 可以对单个 HPA 配置 scale-up 和 scale-down 的容忍区间。字段缺省时仍使用全局默认值，因此兼容性好。

设计取舍：它没有改变 HPA 算法，只是把一个已有参数从 cluster-wide 下放到 workload-level。这种 KEP 风险小、收益明确。

## Container Resource Autoscaling

`1610-container-resource-autoscaling` 解决的是 sidecar 干扰。传统 resource metrics 以 Pod 为单位聚合，适合“Pod 中只有一个主要业务容器”的假设。但现在常见 Pod 包含：

- service mesh sidecar
- logging/metrics sidecar
- model warmup sidecar
- proxy 或 adapter sidecar

如果 HPA 读 Pod 总 CPU/memory，主容器压力会被 sidecar 稀释，或者 sidecar 抖动会误导扩缩容。

Container resource metrics 让 HPA 指定某个 container 的 CPU/memory 作为 scaling 信号。它把指标目标从“Pod 总和”改成“业务容器”。这对 LLM inference、agent runtime、带 proxy 的 serving workload 很关键。

## Pod Selection Accuracy

`5325-hpa-pod-selection-accuracy` 的问题更隐蔽：HPA 通常先用 target workload 的 label selector 找 Pod。但 label 不等于 ownership。不同 controller、canary、历史 Pod 或同 label workload 都可能被选中。

它提出 `SelectionStrategy`：

| 策略 | 含义 |
|---|---|
| `LabelSelector` | 当前行为，只按 label selector。 |
| `OwnerReference` | 先按 label selector，再沿 owner reference 过滤，只保留目标 workload 拥有的 Pod。 |

`OwnerReference` 需要 controller 做额外 API 查询，因此设计里包含 cache、TTL、fallback 行为。如果 ownership 检查失败，系统回退到默认 selector 行为，避免因为 RBAC 或 API 错误导致 autoscaling 完全失效。

这条 KEP 的本质是：HPA 的准确性依赖“指标分母是否正确”。如果 Pod 集合错了，再精细的 metrics 和算法都没用。

## Scale From Zero

`2021-scale-from-zero` 让 HPA 支持基于 object/external metrics 从 0 副本启动。它明确不支持 resource metrics 从 0 启动，因为 CPU/memory 需要运行中的 Pod 才能测量。

关键设计点：

- 允许 `minReplicas: 0`。
- 引入 HPA status condition 表达 `ScaledToZero`。
- 当 HPA 自己把 workload 从 1 缩到 0 时记录条件。
- 当外部/object metric 表明需要恢复时，从 0 扩到 1 并清掉条件。

为什么需要 condition？因为在 Kubernetes 里 `replicas: 0` 也可能是用户手动暂停 workload。如果 HPA 看到 0 就自动拉起，会破坏用户意图；如果永远不拉起，又无法实现 scale-from-zero。`ScaledToZero` 用状态区分“这是 HPA 自动缩到 0”还是“用户手动设置为 0”。

## External Metric Fallback

`5679-external-metric-fallback` 处理外部指标不可用。外部指标经常来自 CloudWatch、Prometheus adapter、队列系统、第三方监控或 SaaS API，这些系统不在 Kubernetes 控制面直接掌控内。

设计选择：

- fallback 只用于 external metrics。
- 每个 external metric 独立配置 fallback。
- fallback 使用固定 replicas，而不是 last-known-good 或自动估算。
- failure threshold 用 duration，而不是失败次数。
- fallback desired replicas 进入 HPA 原有多指标算法，和其他指标取 max。

duration-based 设计很实际：HPA sync period 可以是 15s，也可以被不同集群改成 30s。用“连续失败 3 次”会在不同集群表现不同；用“失败持续 180 秒”更稳定。

## HPA 决策链路

```text
metric source
  |
  +-- resource / container resource / pods / object / external
  |
pod selection
  |
  +-- label selector
  +-- optional owner-reference filtering
  |
replica calculation
  |
  +-- target ratio
  +-- per-direction tolerance
  +-- scale behavior policies
  |
multi-metric merge
  |
  +-- max desired replicas
  +-- fallback desired replicas can join here
  |
scale subresource update
```

## Cluster Autoscaler Attach Limit

`5030-attach-limit-autoscaler` 不在 HPA 内部，但属于 autoscaling 设计链。它解决 CSI volume attach limit 对 scale-up 模拟的影响。

如果 scheduler 因 volume attach limit 无法放置 Pod，Cluster Autoscaler 需要知道新增什么节点才有用。否则可能出现：

- autoscaler 加了节点，但 Pod 仍因为 attach limit pending。
- scheduler 和 autoscaler 对“节点是否能承载 Pod”的模拟不一致。
- scale from zero node group 时缺少真实节点 attach limit 信息。

这个 KEP 的意义是把 autoscaler 和 scheduler 的可行性判断拉近。类似问题未来也会出现在 DRA、PodGroup、topology-aware workload scheduling 上。

## 关键失败模式

| 失败模式 | 设计处理 |
|---|---|
| tolerance 太粗导致扩容慢 | per-HPA / per-direction tolerance。 |
| sidecar 稀释业务指标 | container resource metrics。 |
| label selector 选错 Pod | OwnerReference selection strategy。 |
| 0 副本和手动暂停混淆 | `ScaledToZero` condition。 |
| 外部指标故障导致无法扩容 | per-metric external fallback。 |
| autoscaler 加节点但仍不可调度 | attach limit 纳入 autoscaler 模拟。 |

## 和指标生态的关系

- [[metrics-server]] 提供 resource/container resource metrics，是 HPA resource path 的基础。
- [[prometheus-adapter]] 提供 custom/external metrics，是 scale-from-zero、external fallback、business metric scaling 的关键路径。
- [[llm-d-workload-variant-autoscaler]] 这类项目如果要和原生 HPA/KEDA 对接，需要特别关注 external metrics fallback 和 selection accuracy。

## 阅读顺序

1. `4951-configurable-hpa-tolerance`：最小但最实用的 API 下放。
2. `1610-container-resource-autoscaling`：理解 sidecar-heavy workload 的指标边界。
3. `5325-hpa-pod-selection-accuracy`：理解 HPA 为什么可能读错 Pod 集合。
4. `2021-scale-from-zero`：理解 0 副本状态语义。
5. `5679-external-metric-fallback`：理解外部指标失败策略。
6. `5030-attach-limit-autoscaler`：理解 autoscaler 和 scheduler 模拟一致性。

## 关键 KEP 实现状态

| KEP | 当前状态 | Alpha / Beta / GA | Feature gate | 关键实现路径 |
|---|---|---|---|---|
| `4951-configurable-hpa-tolerance` | `implementable / stable`，GA 目标 v1.37 | v1.33 / v1.35 / v1.37 | `HPAConfigurableTolerance` | `HPAScalingRules.tolerance` 下放到单个 HPA 的 scaleUp/scaleDown。 |
| `853-configurable-hpa-scale-velocity` | `implemented / stable`，已实现/GA | - / - / - | - | HPA behavior policies、stabilization window、scale velocity。 |
| `2702-graduate-hpa-api-to-GA` | `implemented / stable`，已实现/GA | - / - / v1.23 | - | HPA v2 API GA。 |
| `1610-container-resource-autoscaling` | `implemented / stable`，已实现/GA | v1.20 / v1.27 / v1.30 | `HPAContainerMetrics` | HPA 使用指定 container 的 CPU/memory 指标。 |
| `117-hpa-metrics-specificity` | `implemented / stable`，已实现/GA | - / - / - | - | custom/external metrics 支持 label selector。 |
| `5325-hpa-pod-selection-accuracy` | `implementable / alpha`，仍在 alpha | v1.35 / v1.36 / v1.37 | `HPASelectionStrategy` | `OwnerReference` selection strategy，过滤非目标 workload Pod。 |
| `2021-scale-from-zero` | `implementable / beta`，仍在 beta | v1.16 / v1.37 / x.y | `HPAScaleToZero` | HPA 基于 object/external metrics 从 0 恢复，并用 condition 标记自动缩零。 |
| `5679-external-metric-fallback` | `implementable / alpha`，仍在 alpha | v1.36 / v1.37 / v1.38 | `HPAExternalMetricFallback` | external metric 连续失败后用固定 fallback replicas 进入 max 合并。 |
| `5030-attach-limit-autoscaler` | `implementable / beta`，仍在 beta | v1.35 / v1.37 / v1.38 | `VolumeLimitScaling` | Cluster Autoscaler scale-up 模拟纳入 CSI attach limit。 |

## 追踪重点

- HPA v2 API 新字段是否进入 stable，旧版本 conversion 是否完整。
- per-metric fallback 状态是否足够可观测，是否有 events/conditions/metrics。
- OwnerReference filtering 的 cache 是否会带来 API server 压力。
- scale-from-zero 与 KEDA、Karpenter、queue-based autoscaler 的边界。
- DRA、PodGroup、volume attach、topology 等复杂约束是否继续进入 autoscaler 模拟。
