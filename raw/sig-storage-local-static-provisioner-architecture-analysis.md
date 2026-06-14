# Local Static Provisioner 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/sig-storage-local-static-provisioner · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Local Static Provisioner 发现节点本地磁盘/目录并创建 local PersistentVolume，配合调度绑定把数据固定到节点。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Local Static Provisioner   │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Discovery  │ │ PV controller: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Node affin │ │ Cleanup script │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Discovery daemon | scan mount directories |
| PV controller | create/delete local PV |
| Node affinity | bind PV to node |
| Cleanup scripts/classes | Cleanup scripts/classes |

## 关键数据流

```
节点挂载本地盘
        │
        ▼
daemon 发现可用路径
        │
        ▼
创建带 node affinity 的 PV
        │
        ▼
PVC 绑定后 Pod 调度到对应节点
        │
        ▼
释放后清理或保留
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Local Static Provisioner 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：local PV 性能高但节点绑定强；动态网络存储更灵活但可能牺牲本地性能。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Local PV static provisioning` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Local Static Provisioner | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Local PV static provisioning | [[kubernetes]], [[llm-inference]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Local Static Provisioner 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
