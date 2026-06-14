# Headlamp 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/headlamp · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Headlamp 是可扩展 Kubernetes web UI，面向 dashboard、debugging、monitoring 和插件扩展。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Kubernetes UI need                                                         │
│ Users need browsing, debugging, monitoring, and plugin-driven cluster      │
│ operations.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Headlamp frontend                                                          │
│ React UI renders resources, logs, events, plugin views, and navigation.    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Backend/proxy and auth                                                     │
│ Kubeconfig, tokens, access checks, and API proxying connect the UI to      │
│ clusters.                                                                  │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Kubernetes API resources and extensions become an operator-facing web      │
│ experience.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Frontend | React/TypeScript UI |
| Backend/proxy | Kubernetes API access |
| Plugin system | UI and cluster extensions |
| Auth/context | kubeconfig, in-cluster, OIDC-like deployments |

## 关键数据流

```
用户打开 Headlamp
        │
        ▼
选择 cluster/context
        │
        ▼
后端代理 Kubernetes API
        │
        ▼
前端展示 workloads/events/logs/resources
        │
        ▼
插件扩展额外视图或动作
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Headlamp 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：kubewall 是 single-binary dashboard；Headlamp 更强调插件化和通用 Kubernetes UI。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Kubernetes UI` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Headlamp | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Kubernetes UI | [[kubernetes]], [[kubewall]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Headlamp 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
