---
title: Kustomize
tags: [entity, kubernetes, config, gitops]
date: 2026-06-14
sources: [kustomize-architecture-analysis.md]
related: ["[[kustomize]]", "[[kubernetes]]", "[[gitops]]"]
---

# Kustomize

Kustomize 用 overlay/patch/transformer 管理 Kubernetes YAML 差异，是 kubectl 原生支持的配置定制工具链。 详见 [[src-kustomize-architecture]]。

## 架构边界

Helm 是模板和 package；Kustomize 是 YAML transformer，适合 GitOps 中的环境 overlay。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `配置管理` 能力 | 适合，Kustomize 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[gitops]], [[kubernetes]] 组合。 |

## 核心组件

- Resources/bases/overlays
- Transformers: namePrefix/labels/images/namespace
- Patches: strategic merge/json6902/replacements
- Generators: ConfigMap/Secret

## 选型提示

把 Kustomize 放在 `配置管理` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
