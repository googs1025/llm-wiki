# llm-d Prism 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-prism · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

llm-d Prism 是分布式推理性能分析 dashboard，把 benchmark 和运行数据做交互式分析，用于理解 P/D、路由和资源配置的效果。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ llm-d Prism                │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Frontend/d │ │ Data ingestion │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Analysis v │ │ Comparison wor │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Frontend/dashboard | experiment visualization |
| Data ingestion | benchmark result files or APIs |
| Analysis views | latency/throughput/token/error breakdown |
| Comparison workflow | stack/config/run dimensions |

## 关键数据流

```
导入 benchmark/run 数据
        │
        ▼
解析实验维度和指标
        │
        ▼
可视化 latency/throughput/token stats
        │
        ▼
对比不同 serving 配置
        │
        ▼
输出调参判断
```

## 设计决策与哲学

- **Kubernetes-native control plane**：llm-d Prism 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：llm-d-benchmark 负责跑实验；Prism 负责看懂实验结果。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `performance analysis` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | llm-d Prism | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | performance analysis | [[llm-d-benchmark]], [[llm-inference]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

llm-d Prism 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
