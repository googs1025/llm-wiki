# sig-storage-lib-external-provisioner 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/sig-storage-lib-external-provisioner · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

sig-storage-lib-external-provisioner 是 Kubernetes dynamic volume provisioner 的库，抽象 PVC watch、PV 创建、reclaim 和 controller lifecycle。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ sig-storage-lib-external-p │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ ProvisionC │ │ Provisioner in │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Leader ele │ │ Reclaim/delete │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| ProvisionController | PVC/PV watch and sync |
| Provisioner interface | Provisioner interface |
| Leader election/events | Leader election/events |
| Reclaim/delete handling | Reclaim/delete handling |

## 关键数据流

```
controller watch PVC
        │
        ▼
调用实现方 Provision()
        │
        ▼
创建 PV 并绑定
        │
        ▼
PVC/PV 删除时调用 Delete()
        │
        ▼
事件和错误重试
```

## 设计决策与哲学

- **Kubernetes-native control plane**：sig-storage-lib-external-provisioner 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：具体 provisioner 如 NFS provisioner 处理后端细节；这个库处理 Kubernetes 控制器通用模式。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `external provisioner library` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | sig-storage-lib-external-provisioner | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | external provisioner library | [[kubernetes]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

sig-storage-lib-external-provisioner 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
