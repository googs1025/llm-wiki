# Node Feature Discovery 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/node-feature-discovery · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Node Feature Discovery     │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ nfd-worker │ │ nfd-master/gc: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Feature so │ │ Rules: custom  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| nfd-worker | node local feature sources |
| nfd-master/gc | label publication and cleanup |
| Feature sources | cpu, kernel, pci, usb, custom hooks |
| Rules | custom feature labels |

## 关键数据流

```
worker 扫描节点硬件和系统信息
        │
        ▼
生成 feature set
        │
        ▼
master 写 node labels/extended info
        │
        ▼
scheduler/operator 根据 labels 选择节点
        │
        ▼
变化时更新或清理
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Node Feature Discovery 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：device plugin 暴露可分配资源；NFD 暴露节点能力标签，常作为 GPU/NUMA/硬件调度前置信号。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `节点能力发现` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Node Feature Discovery | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 节点能力发现 | [[kubernetes]], [[llm-inference]], [[gpu-sharing]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Node Feature Discovery 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
