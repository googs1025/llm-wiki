---
title: Kustomize 架构与设计思路分析
tags: [architecture, kubernetes, config, gitops]
date: 2026-06-14
sources: [kustomize-architecture-analysis.md]
related: ["[[kustomize]]", "[[kubernetes]]", "[[gitops]]"]
---

# Kustomize 架构与设计思路分析

> 原文：`raw/kustomize-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/kustomize · 优先级 P1

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

| 层 / 模块 | 职责 |
|----------|------|
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

- **补齐 `配置管理` 维度**：Kustomize 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Helm 是模板和 package；Kustomize 是 YAML transformer，适合 GitOps 中的环境 overlay。
- **选型价值**：它应和 [[gitops]], [[kubernetes]] 一起看，而不是孤立评估。

## 相关页面

- [[kustomize]]
- [[kubernetes]]
- [[gitops]]
