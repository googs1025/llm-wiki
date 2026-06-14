# NFS Subdir External Provisioner 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

NFS Subdir External Provisioner 在远端 NFS server 上为 PVC 动态创建子目录，是轻量实验/中小集群常见 storage class。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ PVC requests NFS-backed storage                                            │
│ A StorageClass points dynamic claims at a shared NFS export.               │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ NFS subdir provisioner                                                     │
│ Watches PVCs and creates one directory per claim under the configured      │
│ export.                                                                    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ PV lifecycle                                                               │
│ Creates PersistentVolumes, binds claims, and handles reclaim behavior.     │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Pods mount shared NFS-backed volumes through standard Kubernetes PV/PVC    │
│ objects.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Provisioner controller | watch PVC/PV |
| NFS backend | shared export path |
| StorageClass parameters | StorageClass parameters |
| Cleanup/reclaim policy | Cleanup/reclaim policy |

## 关键数据流

```
用户创建 PVC
        │
        ▼
external provisioner 创建 NFS 子目录
        │
        ▼
生成 PV 指向该路径
        │
        ▼
Pod 挂载 PVC
        │
        ▼
删除时按 reclaim policy 清理
```

## 设计决策与哲学

- **Kubernetes-native control plane**：NFS Subdir External Provisioner 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它简单易用但隔离和性能弱于云盘/CSI，适合实验或非关键共享文件场景。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `NFS dynamic provisioning` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | NFS Subdir External Provisioner | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | NFS dynamic provisioning | [[kubernetes]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

NFS Subdir External Provisioner 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
