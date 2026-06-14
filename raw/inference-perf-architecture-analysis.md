# inference-perf 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/inference-perf · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

GenAI inference performance benchmarking tool，用于对 OpenAI-compatible/serving endpoint 做负载、延迟和吞吐测量。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Benchmark plan                                                             │
│ Model, endpoint, prompt mix, concurrency, request rate, and duration       │
│ define the run.                                                            │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ inference-perf runner                                                      │
│ Generates inference load and captures latency, throughput, token, and      │
│ error data.                                                                │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Target serving stack                                                       │
│ llm-d, vLLM, SGLang, KServe, AIBrix, or compatible OpenAI-style endpoints. │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Comparable performance reports for tuning routing, batching, and capacity. │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| CLI/config | benchmark 参数与 endpoint 配置 |
| Load generator | 并发、请求分布、payload 模板 |
| Metrics collector | latency/throughput/error/token stats |
| Reports | 结果输出供 llm-d-benchmark / serving 选型使用 |

## 关键数据流

```
用户指定 endpoint/model/workload
        │
        ▼
工具生成请求负载
        │
        ▼
并发调用 inference endpoint
        │
        ▼
收集 TTFT/ITL/latency/throughput
        │
        ▼
输出 benchmark report
```

## 设计决策与哲学

- **Kubernetes-native control plane**：inference-perf 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：和 llm-d-benchmark 相比，inference-perf 更像单个 benchmark harness；llm-d-benchmark 负责更完整的实验生命周期。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `GenAI benchmark` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | inference-perf | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | GenAI benchmark | [[llm-d-benchmark]], [[llm-inference]], [[llm-d-inference-sim]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

inference-perf 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
