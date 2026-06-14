# controller-tools 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/controller-tools · 分析日期：2026-06-14 · 优先级：P0

## 一句话定位

controller-tools 提供 controller-gen，用 Go marker 生成 CRD、RBAC、webhook、deepcopy 等 Kubernetes API 工程资产。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ controller-tools           │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Markers pa │ │ CRD generator: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ RBAC/webho │ │ object/deepcop │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Markers parser | 读取 Go type/comment markers |
| CRD generator | OpenAPI schema and validation |
| RBAC/webhook generators | RBAC/webhook generators |
| object/deepcopy generation | object/deepcopy generation |

## 关键数据流

```
开发者在 API types 写 markers
        │
        ▼
controller-gen 解析 package
        │
        ▼
生成 CRD/RBAC/webhook/deepcopy
        │
        ▼
kubebuilder/kustomize 打包部署
```

## 设计决策与哲学

- **Kubernetes-native control plane**：controller-tools 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：kubebuilder 是脚手架；controller-tools 是实际生成 CRD/RBAC 等产物的工具链。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `API 生成工具` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | controller-tools | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | API 生成工具 | [[kubernetes]], [[model-serving-operator]], [[declarative-agent-management]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

controller-tools 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
