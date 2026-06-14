# LeaderWorkerSet 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/lws · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ LeaderWorkerSet            │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ API: Leade │ │ Controller: re │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Pod templa │ │ Integrations:  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| API | LeaderWorkerSet CRD |
| Controller | replica group rollout/status |
| Pod template | leader/worker roles |
| Integrations | serving/HPC/AI workload |

## 关键数据流

```
用户声明 LeaderWorkerSet
        │
        ▼
controller 创建 leader/worker pod group
        │
        ▼
维护副本、状态和滚动更新
        │
        ▼
服务或上层 operator 连接每组 leader/worker
```

## 设计决策与哲学

- **Kubernetes-native control plane**：LeaderWorkerSet 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：JobSet 面向作业集合；LWS 面向长期运行的 leader/worker 服务复制单元。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `分布式 workload API` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | LeaderWorkerSet | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 分布式 workload API | [[llm-inference]], [[batch-inference]], [[kueue]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

LeaderWorkerSet 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
