# Descheduler 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/descheduler · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Descheduler 根据策略驱逐已经运行的 Pods，让 kube-scheduler 有机会重新放置，修复节点漂移、拓扑不均、约束变化等问题。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Descheduler                │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Policy con │ │ Strategies: re │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Evictor: s │ │ CronJob/contro │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Policy config | strategies/profiles |
| Strategies | remove duplicates, low utilization, topology spread, affinity violations |
| Evictor | safe pod eviction |
| CronJob/controller deployment modes | CronJob/controller deployment modes |

## 关键数据流

```
周期读取节点和 Pod 状态
        │
        ▼
策略识别需要移动的 Pods
        │
        ▼
检查 PDB/namespace/priority 等保护
        │
        ▼
evict Pod
        │
        ▼
scheduler 重新调度
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Descheduler 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：scheduler 决定新 Pod 放哪；descheduler 处理运行一段时间后的布局退化。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `调度后优化` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Descheduler | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 调度后优化 | [[kubernetes]], [[llm-inference]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Descheduler 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
