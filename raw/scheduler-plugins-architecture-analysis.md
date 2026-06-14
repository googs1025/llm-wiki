# scheduler-plugins 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/scheduler-plugins · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

scheduler-plugins 是基于 kube-scheduler framework 的 out-of-tree 插件集合，用于研究和生产化调度扩展。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ scheduler-plugins          │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Framework  │ │ Scheduler bina │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Controller │ │ Integration te │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Framework plugins | queueSort/preFilter/filter/score/reserve 等扩展点 |
| Scheduler binary/config | Scheduler binary/config |
| Controllers/examples for capacity/placement policies | Controllers/examples for capacity/placement policies |
| Integration tests and manifests | Integration tests and manifests |

## 关键数据流

```
Pod 进入 scheduler queue
        │
        ▼
插件在各 extension point 参与决策
        │
        ▼
score/filter/reserve 改变节点选择
        │
        ▼
scheduler bind Pod
        │
        ▼
控制器/指标反馈策略效果
```

## 设计决策与哲学

- **Kubernetes-native control plane**：scheduler-plugins 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Kueue 做 workload admission；scheduler-plugins 影响 Pod 到 Node 的 placement。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `调度 / 资源` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | scheduler-plugins | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 调度 / 资源 | [[kubernetes]], [[llm-inference]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

scheduler-plugins 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
