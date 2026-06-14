# controller-runtime 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/controller-runtime · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Custom controller binary                                                   │
│ Operator code is built around controller-runtime primitives.               │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Manager                                                                    │
│ Scheme, leader election, metrics, health probes, webhooks, cache, and      │
│ lifecycle.                                                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Controller layer                                                           │
│ Informer cache, typed client, workqueue, reconciler, retry, status, and    │
│ finalizers.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Runtime boundary                                                           │
│ Kubernetes API server, admission webhooks, and envtest form the execution  │
│ surface.                                                                   │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Manager | lifecycle、leader election、scheme、metrics |
| Cache/Client | informer cache + API writer |
| Controller/Reconciler | workqueue and reconcile loop |
| Webhook/envtest | admission and test harness |

## 关键数据流

```
manager 启动 cache/webhook/controllers
        │
        ▼
watch 事件进入 workqueue
        │
        ▼
reconciler 读取 cache/API
        │
        ▼
patch status/finalizer/owned resources
        │
        ▼
错误重试或完成
```

## 设计决策与哲学

- **Kubernetes-native control plane**：controller-runtime 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：client-go 是底层机制；controller-runtime 是现代 operator 工程默认抽象；kubebuilder 在其上做项目脚手架。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Operator SDK` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | controller-runtime | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Operator SDK | [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

controller-runtime 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
