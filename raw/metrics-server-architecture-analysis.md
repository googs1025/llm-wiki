# metrics-server 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/metrics-server · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Kubernetes 资源指标管道，把 kubelet summary/metrics 暴露成 `metrics.k8s.io`，供 HPA/VPA/kubectl top 使用。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ metrics-server             │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Scraper: 周 │ │ Storage: 只保留最新 │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ APIService │ │ Consumers: HPA │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
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

- **Kubernetes-native control plane**：metrics-server 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：metrics-server 只服务资源指标，不是 Prometheus 替代品；custom/external metrics 需要 prometheus-adapter 等组件。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `可观测 / autoscaling` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | metrics-server | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 可观测 / autoscaling | [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

metrics-server 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
