# KWOK 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kwok · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

KWOK 是 Kubernetes WithOut Kubelet，用 fake nodes/pods 模拟大规模集群，适合调度、控制器和 scalability 测试。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ KWOK                       │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ kwok contr │ │ kwokctl: clust │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Stage/Conf │ │ Integrations:  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| kwok controller | fake kubelet behavior |
| kwokctl | cluster lifecycle |
| Stage/Configuration | pod/node condition transitions |
| Integrations | kind/kube-apiserver tests |

## 关键数据流

```
创建 KWOK cluster 或接入现有 apiserver
        │
        ▼
声明大量 fake nodes/pods
        │
        ▼
kwok controller 模拟状态变化
        │
        ▼
被测 scheduler/controller 观察大规模对象
        │
        ▼
收集性能和行为结果
```

## 设计决策与哲学

- **Kubernetes-native control plane**：KWOK 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：kind 提供真实小集群；KWOK 提供便宜的大规模对象模拟。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `大规模集群模拟` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | KWOK | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 大规模集群模拟 | [[kubernetes]], [[model-serving-operator]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

KWOK 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
