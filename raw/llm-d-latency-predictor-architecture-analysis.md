# llm-d Latency Predictor 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-latency-predictor · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

llm-d Latency Predictor 是给 llm-d inference scheduler 的 ML-based latency scoring service，用预测延迟信号增强 endpoint picking。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Inference scheduling context                                               │
│ Request features, current load, cache state, and serving configuration     │
│ affect latency.                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Latency predictor service                                                  │
│ Extracts features and predicts latency or cost for candidate endpoints.    │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Training and evaluation path                                               │
│ Historical request data and benchmark traces calibrate prediction quality. │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Consumer                                                                   │
│ llm-d router or scheduler uses scores to choose an endpoint or route.      │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Service API | latency scoring endpoint |
| Model/features | 请求、模型、endpoint 或历史指标特征 |
| Integration | llm-d scheduler/router scoring |
| Training/evaluation utilities | Training/evaluation utilities |

## 关键数据流

```
scheduler 准备候选 endpoint
        │
        ▼
调用 latency predictor 计算 score
        │
        ▼
与负载/KV/健康分数融合
        │
        ▼
选择 endpoint
        │
        ▼
真实延迟回流用于校准
```

## 设计决策与哲学

- **Kubernetes-native control plane**：llm-d Latency Predictor 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它不是 router 本体，而是 router/scorer 的外部预测信号。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `latency predictor` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | llm-d Latency Predictor | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | latency predictor | [[llm-d]], [[inference-routing]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

llm-d Latency Predictor 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
