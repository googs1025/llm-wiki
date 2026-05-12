---
title: Argo CD
tags: [gitops, ci-cd, kubernetes, cncf]
date: 2026-04-22
sources: [argocd-overview.md]
related: ["[[kubernetes]]", "[[gitops]]"]
---

# Argo CD

Kubernetes 声明式 GitOps 持续交付工具（CNCF 毕业项目）。

## 核心特性
- Git 仓库作为单一事实来源
- 多模板支持（Helm / Kustomize / Jsonnet / YAML）
- 自动漂移检测与同步
- 多集群管理
- SSO + RBAC + 多租户
- 蓝绿 / 金丝雀部署（Sync hooks）

## 架构
K8s controller 持续比较 live state 与 Git desired state → OutOfSync 时提供同步选项。

## 相关
- [[gitops]] — Argo CD 所实现的模式
- [[kubernetes]] — 运行平台
- 详见 [[src-argocd-overview]]