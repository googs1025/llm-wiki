---
title: GitOps
tags: [gitops, ci-cd, kubernetes, methodology]
date: 2026-04-22
sources: [argocd-overview.md, k3s-gitops-k0rdent.md]
related: ["[[argocd]]", "[[kubernetes]]"]
---

# GitOps

以 Git 仓库为基础设施和应用配置的单一事实来源的运维方法论。

## 核心原则
1. **声明式** — 系统期望状态用声明式描述
2. **版本化** — 所有变更通过 Git 管理
3. **自动拉取** — Agent 持续将实际状态向期望状态调和
4. **持续调和** — 漂移自动检测和修复

## 工具生态
| 工具 | 定位 |
|------|------|
| [[argocd]] | K8s 应用交付 |
| Flux | K8s 应用交付（CNCF） |
| k0rdent | 多集群声明式管理 |
| Tekton | CI 流水线 |

## 实践案例
- On-prem K3s 集群的 GitOps 部署 → [[src-k3s-gitops-k0rdent]]
- Argo CD 概览 → [[src-argocd-overview]]
