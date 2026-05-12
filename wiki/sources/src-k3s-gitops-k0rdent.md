---
title: "K3s + k0rdent GitOps 部署 On-Prem 集群"
tags: [kubernetes, k3s, gitops, on-prem]
date: 2026-04-17
sources: [k3s-gitops-k0rdent.md]
related: ["[[kubernetes]]", "[[gitops]]", "[[argocd]]"]
---

# K3s + k0rdent GitOps 部署 On-Prem 集群

## 摘要
使用 K3s + k0rdent 声明式模板 + Proxmox 虚拟化，将 on-prem K8s 部署变为完全声明式、GitOps 兼容的流程。

## 架构
k0rdent 管理层 → Proxmox BYOT 基础设施 → Control Plane Provider → K3s Bootstrap → 运行集群

## 关键设计
- **BYOT（Bring Your Own Template）**：复用已有 VM 模板 + cloud-init，跳过镜像构建
- **持续调和**：k0rdent 持续监控并自动纠正配置漂移
- **Helm chart 管理**：VM 克隆、资源分配、SSH 密钥注入全部声明式
