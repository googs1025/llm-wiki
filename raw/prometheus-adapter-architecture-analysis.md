# prometheus-adapter 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/prometheus-adapter · 分析日期：2026-06-14 · 优先级：P0

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

| 层 / 模块 | 主要职责 |
|----------|----------|
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

- **Kubernetes-native control plane**：prometheus-adapter 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：metrics-server 给 CPU/memory resource metrics；prometheus-adapter 给自定义/外部指标，是高级 autoscaling 的关键桥。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `custom/external metrics` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | prometheus-adapter | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | custom/external metrics | [[llm-inference]], [[model-serving-operator]], [[llm-d-workload-variant-autoscaler]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

prometheus-adapter 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
