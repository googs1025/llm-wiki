# llm-d Workload Variant Autoscaler 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-workload-variant-autoscaler · 分析日期：2026-06-13 · 版本：HEAD `526ce85`（2026-06-12）

## 一句话定位

llm-d Workload Variant Autoscaler（WVA）是面向分布式 LLM 推理的 Kubernetes 全局 autoscaler，核心对象是同一模型/InferencePool 下的多个 serving variant。它通过 Prometheus、Gateway API Inference Extension、KEDA/HPA、GPU inventory 和 scale target 状态，把“不同硬件/角色/成本的变体应该各扩多少副本”转成外部指标和 status，而不是直接取代 HPA/KEDA。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| API 层 | `api/v1alpha1/variantautoscaling_types.go` | 定义 `VariantAutoscaling` spec/status/conditions。 |
| Manager 启动层 | `cmd/main.go` | 注册 K8s、Prometheus Operator、Gateway API Inference Extension、KEDA、LWS 等 scheme，组装 reconciler 和 engines。 |
| Reconcile 层 | `internal/controller` | 解析 scale target、更新 conditions、读取 decision cache、patch status、watch Deployment/StatefulSet/LWS/InferencePool/HPA/KEDA。 |
| Metrics 收集 | `internal/collector`, Prometheus source registry | 采集 request rate、replica、queue/cache/capacity 相关指标。 |
| 优化引擎 | `internal/engines/saturation` | 维护 capacity store、GPU inventory、queueing/saturation analyzer、cost-aware optimizer。 |
| 执行动作 | `internal/actuator` | 不直接替代 HPA/KEDA，而是发出 desired/current replica 等指标供它们消费。 |
| 协调/存储 | `internal/coordinator`, `internal/datastore` | 共享 scaling decision、容量知识和运行期状态。 |
| 部署样例 | `deploy`, `charts`, `docs` | HPA/KEDA/simulator/OpenShift 等部署路径。 |

WVA 的关键分层是“决策”和“执行”分离：它负责算 variant allocation，并通过指标驱动 Kubernetes autoscaler；实际 scale subresource 仍由 HPA/KEDA 这类成熟组件执行。

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

当 KEDA 或 LWS CRD 不存在时，`cmd/main.go` 会做运行时探测并按能力注册 controller，避免把所有集群都绑定到同一套扩缩组件。

## 设计决策与哲学

- **Variant 是 autoscaling 的一等对象**：`VariantAutoscaling` 不只看单个 Deployment 的 CPU/GPU 指标，而是把同一模型下不同硬件、角色或配置变体纳入一个优化问题。
- **不直接抢 HPA/KEDA 的职责**：`internal/actuator/actuator.go` 主要发指标，实际 scale 由 HPA/KEDA 读 metrics API 完成，降低与 Kubernetes autoscaling 生态冲突。
- **Gateway API Inference Extension 是 serving 语义入口**：manager 注册 InferencePool scheme，说明 WVA 需要理解 endpoint pool 和 model serving variant，而不是只做通用 workload autoscaling。
- **优化引擎需要容量知识而不只是当前利用率**：saturation engine 组装 capacity store、GPU inventory、queueing analyzer 和 optimizer，体现了 LLM serving autoscaling 需要估计 capacity curve。
- **可选集成而非硬依赖**：KEDA、LWS、Prometheus Operator 等都按 CRD/配置检测，适合在不同 Kubernetes 发行版和成熟度环境中渐进部署。

## 关键组件深入解读

### VariantAutoscaling Reconciler（`internal/controller/variantautoscaling_controller.go`）

Reconciler 负责把 CRD spec 变成可追踪状态：读取 `VariantAutoscaling`，resolve scale target，更新 conditions，从 shared decision cache 拿优化结果，patch status，并暴露 metrics。它还 watch deployment/statefulset/LWS、ServiceMonitor、InferencePool、HPA 和 ScaledObject，说明它既关心 serving 语义，也关心最终执行扩缩的 Kubernetes 对象。

### Saturation Engine（`internal/engines/saturation/engine.go`）

Saturation engine 是 WVA 的决策核心。`NewEngine` 里会装配 Prometheus request count source、GPU inventory、type inventory、saturation limiter、capacity knowledge store、queueing model analyzer 和 default cost-aware optimizer。它把“现在有多少请求、每个 variant 大概能吃多少、GPU 还有多少、成本约束是什么”合成 desired allocation。

## 与同类对比

| 维度 | llm-d WVA | HPA / KEDA | KServe autoscaling / Knative |
|------|-----------|------------|------------------------------|
| 决策对象 | 同一模型下多个 serving variant | 单 workload 或 event source | service / revision / model service |
| 推理语义 | modelID、InferencePool、variant cost、P/D 场景 | 指标驱动，语义较弱 | model service 语义较强，但 variant allocation 不是核心 |
| 执行方式 | 发指标给 HPA/KEDA | 直接 scale subresource | controller/activator/autoscaler |
| 适合问题 | 多硬件、多角色、多成本 LLM serving fleet | 通用扩缩 | 模型服务平台级生命周期 |

## 性能 / 资源开销

WVA 的开销主要来自 controller-runtime cache、Prometheus 查询、优化计算和 metrics 暴露。它不在请求路径上，因此不会直接增加推理延迟；风险在于指标滞后或 capacity model 偏差导致扩缩慢、震荡或过度扩容。

## 安全模型

WVA 需要读取/patch CRD status、读取 workload scale target、读取 Prometheus 指标、创建或协调 HPA/KEDA 相关对象。RBAC 应限制在目标 namespace 和必要资源上；Prometheus 查询权限也要和租户边界一致，否则可能通过指标侧泄露模型流量、队列和容量信息。
