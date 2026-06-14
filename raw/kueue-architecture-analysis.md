# Kueue 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kueue · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Kubernetes-native Job Queueing，用 ClusterQueue/LocalQueue/Workload/ResourceFlavor 把 batch、AI/HPC 和多租户资源配额做成 admission control。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Kueue                      │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ API: Clust │ │ Controller: wo │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Integratio │ │ Scheduler-like │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| API | ClusterQueue / LocalQueue / Workload / ResourceFlavor |
| Controller | workload admission, quota accounting, preemption |
| Integrations | Job, JobSet, RayJob, MPIJob, PyTorchJob 等 batch workload |
| Scheduler-like logic | cohort borrowing、fair sharing、flavor assignment |

## 关键数据流

```
用户提交 Job/JobSet/RayJob
        │
        ▼
Kueue 为 workload 建队列对象
        │
        ▼
ClusterQueue 检查资源配额与 flavor
        │
        ▼
admit 后 workload 才真正消耗集群资源
        │
        ▼
完成/失败后释放 quota
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Kueue 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：和 kube-scheduler 不同，Kueue 先决定 workload 是否能入场；真正的 Pod placement 仍由 scheduler 做。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `调度 / 队列` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Kueue | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 调度 / 队列 | [[llm-inference]], [[batch-inference]], [[model-serving-operator]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Kueue 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
