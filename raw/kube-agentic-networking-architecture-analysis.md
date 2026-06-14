# kube-agentic-networking 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kube-agentic-networking · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

kube-agentic-networking 为 Kubernetes 中 agents/tools 提供 agentic networking policies and governance，面向 AI Agent 出口、工具调用和网络权限边界。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ kube-agentic-networking    │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CRD/polici │ │ Controller: po │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Gateway/ne │ │ Audit/governan │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| CRD/policies | agent/tool/network intent |
| Controller | policy reconciliation |
| Gateway/network integration | Gateway/network integration |
| Audit/governance signals | Audit/governance signals |

## 关键数据流

```
平台声明 agent/tool 网络策略
        │
        ▼
controller 解析目标和权限
        │
        ▼
下发到 gateway/network policy 层
        │
        ▼
Agent 调用工具时被策略约束
        │
        ▼
审计和状态回写
```

## 设计决策与哲学

- **Kubernetes-native control plane**：kube-agentic-networking 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它和 agentgateway/agent-sandbox 互补：sandbox 管运行时隔离，gateway/networking 管出入口策略。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Agent networking governance` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | kube-agentic-networking | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Agent networking governance | [[agentgateway]], [[agent-sandbox]], [[cloud-native-security]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

kube-agentic-networking 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
