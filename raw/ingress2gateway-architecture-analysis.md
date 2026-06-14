# ingress2gateway 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/ingress2gateway · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

ingress2gateway 把 Kubernetes Ingress resources 转换成 Gateway API resources，帮助从 annotation-heavy Ingress 迁移到 Gateway/HTTPRoute。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ ingress2gateway            │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Parser: 读取 │ │ Provider trans │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Gateway AP │ │ CLI/report: 迁移 │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Parser | 读取 Ingress/Service annotations |
| Provider translators | nginx/contour/gce 等差异 |
| Gateway API renderer | Gateway/HTTPRoute/TLSRoute |
| CLI/report | 迁移建议和限制 |

## 关键数据流

```
读取集群或 YAML Ingress
        │
        ▼
识别规则和 provider annotations
        │
        ▼
转换成 Gateway API resources
        │
        ▼
输出 YAML 和 warnings
        │
        ▼
用户审查后应用
```

## 设计决策与哲学

- **Kubernetes-native control plane**：ingress2gateway 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：它不负责流量转发，只负责迁移配置模型。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `Ingress -> Gateway API migration` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | ingress2gateway | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | Ingress -> Gateway API migration | [[gateway-api]], [[inference-routing]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

ingress2gateway 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
