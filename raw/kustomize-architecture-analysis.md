# Kustomize 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/kustomize · 分析日期：2026-06-14 · 优先级：P1

## 一句话定位

Kustomize 用 overlay/patch/transformer 管理 Kubernetes YAML 差异，是 kubectl 原生支持的配置定制工具链。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Kustomize                  │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Resources/ │ │ Transformers:  │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Patches: s │ │ Generators: Co │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 主要职责 |
|----------|----------|
| Resources/bases/overlays | Resources/bases/overlays |
| Transformers | namePrefix/labels/images/namespace |
| Patches | strategic merge/json6902/replacements |
| Generators | ConfigMap/Secret |

## 关键数据流

```
base 定义通用资源
        │
        ▼
overlay 引入 base
        │
        ▼
transformers/patches 应用环境差异
        │
        ▼
生成最终 YAML
        │
        ▼
kubectl/Argo CD 应用
```

## 设计决策与哲学

- **Kubernetes-native control plane**：Kustomize 把自身问题域投射到 Kubernetes API、controller、CLI 或 adapter 模型里，因此适合和 [[kubernetes]]、[[model-serving-operator]]、[[llm-inference]] 的控制面一起比较。
- **边界清晰比功能堆叠更重要**：Helm 是模板和 package；Kustomize 是 YAML transformer，适合 GitOps 中的环境 overlay。
- **适合作为选型坐标而不是孤立工具**：在当前 wiki 中，它补的是 `配置管理` 这一层，和已收录的 [[llm-d]]、[[kserve]]、[[aibrix]]、[[agent-sandbox]] 或 [[cloud-native-security]] 形成横向对照。

## 与同类对比

| 维度 | Kustomize | 相邻项目 / 概念 |
|------|--------------|-----------------|
| 抽象层 | 配置管理 | [[gitops]], [[kubernetes]] |
| 主要输入 | Kubernetes object、配置、指标或 workload intent | 取决于上层平台 |
| 主要输出 | 状态、资源、指标、诊断结果或生成配置 | 下游 controller/runtime/gateway |
| 不适合 | 代替相邻层的职责 | 需要和相邻组件组合选型 |

## 安全 / 运维注意点

Kustomize 通常需要读取或修改 Kubernetes API 对象、节点/运行时状态、外部系统或指标后端。生产环境要重点检查 RBAC、namespace 边界、controller leader election、metrics/audit 暴露范围，以及生成/变更资源是否可回滚。
