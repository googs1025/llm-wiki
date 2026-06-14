# JobSet 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/jobset · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

JobSet 是 K8s native API for distributed ML training and HPC workloads，用多个 replicated jobs 表达一个整体作业。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Distributed batch / ML job intent                                          │
│ A training or HPC workload needs multiple related Kubernetes Jobs.         │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ JobSet API                                                                 │
│ Replicated jobs, dependencies, startup ordering, success policy, and       │
│ failure behavior.                                                          │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ JobSet controller                                                          │
│ Creates child Jobs and reconciles status, completion, restart, and failure │
│ policy.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Kueue, scheduler, Pods, and distributed frameworks run the actual work.    │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| API | JobSet / replicatedJobs |
| Controller | child Job lifecycle and status aggregation |
| Failure policy | restart / recreate / fail fast |
| Integrations | Kueue, batch, ML training |

## 关键数据流

```
用户提交 JobSet
        │
        ▼
controller 展开多个 child Jobs
        │
        ▼
各 job 创建 Pods
        │
        ▼
聚合成功/失败状态
        │
        ▼
按 failure policy 处理重试或终止
```

## 设计决策与哲学

- **Kubernetes-native control plane**：JobSet 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Kueue 负责 queue/admission；JobSet 负责表达分布式作业拓扑，二者常一起出现。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `分布式 workload API` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | JobSet | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 分布式 workload API | [[llm-inference]], [[batch-inference]], [[kueue]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

JobSet 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
