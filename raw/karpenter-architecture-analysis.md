# Karpenter 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/karpenter · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Pending Pods with resource and topology constraints                        │
│ CPU, memory, GPU, zone, architecture, taints, and affinity shape demand.   │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Karpenter controller                                                       │
│ Provisioning, disruption, consolidation, and termination control loops.    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Capacity model                                                             │
│ NodePool, NodeClaim, scheduler simulation, and CloudProvider               │
│ pricing/capacity APIs.                                                     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Cloud instances join as Kubernetes nodes; idle or replaceable nodes are    │
│ consolidated.                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| API | NodePool / NodeClaim / EC2NodeClass-like provider API |
| Controller | provisioning、disruption、consolidation、termination |
| Scheduler simulation | 从 pending pods 推导 instance requirements |
| CloudProvider boundary | 云厂商容量、价格、可用区和实例类型 |

## 关键数据流

```
Pod pending
        │
        ▼
Karpenter 汇总调度约束
        │
        ▼
选择 NodePool 和实例需求
        │
        ▼
创建 NodeClaim/云主机
        │
        ▼
节点加入集群并承载 Pod
        │
        ▼
空闲或可合并时 disruption/consolidation
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Karpenter 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：和 HPA/KEDA 不同，Karpenter 扩的是节点容量；和 Cluster Autoscaler 相比，它更强调按 pending pods 即时求解容量。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `节点弹性 / 成本` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Karpenter | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 节点弹性 / 成本 | [[llm-inference]], [[kubernetes]], [[model-serving-operator]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Karpenter 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
