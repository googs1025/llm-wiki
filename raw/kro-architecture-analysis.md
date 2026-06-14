# KRO 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kro · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

KRO（Kube Resource Orchestrator）用 ResourceGraphDefinition 把多个 Kubernetes resources 组合成更高层 API。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Higher-level platform API intent                                           │
│ A team defines a ResourceGraphDefinition for application or platform       │
│ abstractions.                                                              │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ KRO controller                                                             │
│ Expands graph definitions, reconciles dependencies, and tracks composed    │
│ resource status.                                                           │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Generated API surface                                                      │
│ Application teams create simpler custom resources backed by multiple       │
│ Kubernetes objects.                                                        │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ The composed Kubernetes resources implement the higher-level API contract. │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| ResourceGraphDefinition API | ResourceGraphDefinition API |
| Controller | graph reconciliation |
| Generated instances/resources | Generated instances/resources |
| Status/value propagation | Status/value propagation |

## 关键数据流

```
平台定义 ResourceGraphDefinition
        │
        ▼
用户创建上层 instance
        │
        ▼
controller 渲染/协调底层 resources
        │
        ▼
从子资源聚合状态
        │
        ▼
提供简化的平台 API
```

## 设计决策与哲学

- **Kubernetes-native control plane**：KRO 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Crossplane composition 偏跨云资源；KRO 偏 Kubernetes resource graph 和平台 API 组合。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `higher-level API orchestration` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | KRO | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | higher-level API orchestration | [[kubernetes]], [[model-serving-operator]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

KRO 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
