---
title: "Argo CD 概览"
tags: [gitops, ci-cd, kubernetes, argocd]
date: 2026-04-22
sources: [argocd-overview.md]
related: ["[[kubernetes]]", "[[gitops]]"]
---

# Argo CD 概览

## 摘要
Kubernetes 声明式 GitOps 持续交付工具，以 Git 仓库为应用期望状态的单一事实来源。

## 核心能力
- 多模板：Kustomize / Helm / Jsonnet / YAML
- 多集群部署
- SSO + RBAC + 多租户
- 自动漂移检测 + 同步
- PreSync/Sync/PostSync hooks（蓝绿、金丝雀）
- 回滚到任意 Git 提交

## 架构
作为 K8s controller 持续比较 live state 与 Git desired state，OutOfSync 时可视化差异并提供同步选项。
