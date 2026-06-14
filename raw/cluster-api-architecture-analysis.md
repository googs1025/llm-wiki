# Cluster API 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/cluster-api · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Cluster API 用声明式 API 管理 Kubernetes 集群生命周期，把 Cluster/Machine/MachineDeployment 和 provider infra/bootstrap/control-plane 拆成可组合控制器。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Cluster API                │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Core API:  │ │ Providers: inf │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Controller │ │ Clusterctl: pr │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Core API | Cluster, Machine, MachineDeployment, MachineSet |
| Providers | infrastructure/bootstrap/control-plane |
| Controllers | reconcile desired cluster state |
| Clusterctl | provider init/move/upgrade workflow |

## 关键数据流

```
用户声明 Cluster/Machine topology
        │
        ▼
CAPI core controller 协调对象
        │
        ▼
provider controller 创建云/裸金属资源
        │
        ▼
bootstrap/control-plane provider 初始化节点
        │
        ▼
状态回写并支持升级/迁移
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Cluster API 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Kubespray 偏 Ansible 部署；Cluster API 偏 Kubernetes-native 声明式集群生命周期。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `集群生命周期` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Cluster API | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 集群生命周期 | [[kubernetes]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Cluster API 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
