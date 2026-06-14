# Secrets Store CSI Driver 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/secrets-store-csi-driver · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

Secrets Store CSI Driver 通过 CSI volume 把外部 secret store 注入 Pod，并支持 provider、rotation 和可选 Kubernetes Secret 同步。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Pod volume intent                                                          │
│ A Pod references a SecretProviderClass through a CSI volume.               │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Secrets Store CSI Driver node plugin                                       │
│ Handles mount requests and coordinates provider calls on the node.         │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Provider and sync layer                                                    │
│ Provider gRPC plugins fetch external secrets; rotation and optional K8s    │
│ Secret sync run separately.                                                │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Pods receive mounted secret files while source of truth remains in         │
│ external secret stores.                                                    │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| CSI node plugin | mount volume into pod |
| Provider gRPC | Vault/Azure/GCP/AWS 等外部 secret |
| SecretProviderClass API | SecretProviderClass API |
| Rotation/sync controller | Rotation/sync controller |

## 关键数据流

```
Pod 引用 SecretProviderClass volume
        │
        ▼
CSI driver 调用 provider
        │
        ▼
provider 拉取外部 secret
        │
        ▼
driver mount 到 Pod filesystem
        │
        ▼
可选同步为 Kubernetes Secret 并轮转
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Secrets Store CSI Driver 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Kubernetes Secret 是集群内对象；Secrets Store CSI Driver 把真凭据留在外部 secret manager，运行时挂载。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `存储 / 凭据` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Secrets Store CSI Driver | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 存储 / 凭据 | [[cloud-native-security]], [[agent-credential-isolation]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Secrets Store CSI Driver 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
