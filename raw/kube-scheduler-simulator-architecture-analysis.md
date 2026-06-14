# kube-scheduler-simulator 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kube-scheduler-simulator · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

kube-scheduler-simulator 提供 Kubernetes scheduler 行为模拟和可视化，用于理解 filter/score、调度失败原因和策略效果。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Scheduler scenario                                                         │
│ Users define nodes, pods, scheduler config, and policy experiments.        │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Simulator backend                                                          │
│ Runs scheduler logic and captures filter, score, bind, and decision        │
│ traces.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Visualization frontend                                                     │
│ Shows scheduling timeline, plugin results, and object state changes.       │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Scheduler policy debugging and education without requiring a real workload │
│ cluster.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Simulator API/server | Simulator API/server |
| Scheduler integration | Scheduler integration |
| Frontend visualization | Frontend visualization |
| Scenario objects | nodes/pods/policies |

## 关键数据流

```
用户创建模拟节点和 Pod
        │
        ▼
scheduler 执行调度周期
        │
        ▼
记录 filter/score/bind 过程
        │
        ▼
UI 展示每一步决策
        │
        ▼
用户调整策略复盘
```

## 设计决策与哲学

- **Kubernetes-native control plane**：kube-scheduler-simulator 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：KWOK 模拟大规模集群对象；scheduler simulator 解释单次或少量调度决策过程。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `scheduler 可视化模拟` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | kube-scheduler-simulator | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | scheduler 可视化模拟 | [[kubernetes]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

kube-scheduler-simulator 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
