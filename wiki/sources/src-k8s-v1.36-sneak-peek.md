---
title: "Kubernetes v1.36 Sneak Peek"
tags: [kubernetes, release, security, networking]
date: 2026-03-30
sources: [k8s-v1.36-sneak-peek.md]
related: ["[[kubernetes]]", "[[gateway-api]]", "[[ingress-nginx]]"]
---

# Kubernetes v1.36 Sneak Peek

## 摘要
Kubernetes v1.36 预计 2026 年 4 月底发布，包含重要的安全强化和弃用清理。

## 关键变更

### 弃用
- **Service.spec.externalIPs** 因中间人攻击风险（CVE-2020-8554）被弃用，v1.43 移除。替代方案：[[gateway-api]]、LoadBalancer、NodePort

### 移除
- **gitRepo Volume Driver** 永久禁用（自 v1.11 弃用），存在 root 提权风险。替代：init containers + git-sync

### GA 升级
- **SELinux 卷标签加速**：用 `mount -o context` 替代递归重标签，显著减少 Pod 启动时间

### 退役
- **[[ingress-nginx]]** 于 2026-03-24 正式退役，不再维护
