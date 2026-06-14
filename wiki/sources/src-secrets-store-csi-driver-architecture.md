---
title: Secrets Store CSI Driver 架构与设计思路分析
tags: [architecture, kubernetes, security, storage]
date: 2026-06-14
sources: [secrets-store-csi-driver-architecture-analysis.md]
related: ["[[secrets-store-csi-driver]]", "[[kubernetes]]", "[[cloud-native-security]]", "[[agent-credential-isolation]]"]
---

# Secrets Store CSI Driver 架构与设计思路分析

> 原文：`raw/secrets-store-csi-driver-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/secrets-store-csi-driver · 优先级 P0

## 一句话定位

Secrets Store CSI Driver 通过 CSI volume 把外部 secret store 注入 Pod，并支持 provider、rotation 和可选 Kubernetes Secret 同步。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Secrets Store CSI Driver   │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CSI node p │ │ Provider gRPC: │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ SecretProv │ │ Rotation/sync  │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CSI node plugin | mount volume into pod |
| Provider gRPC | Vault/Azure/GCP/AWS 等外部 secret |
| SecretProviderClass API | SecretProviderClass API |
| Rotation/sync controller | Rotation/sync controller |

## 关键数据流

```
Pod 引用 SecretProviderClass volume
        │
        ▼
CSI driver 调用 provider
        │
        ▼
provider 拉取外部 secret
        │
        ▼
driver mount 到 Pod filesystem
        │
        ▼
可选同步为 Kubernetes Secret 并轮转
```

## 设计决策与哲学

- **补齐 `存储 / 凭据` 维度**：Secrets Store CSI Driver 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：Kubernetes Secret 是集群内对象；Secrets Store CSI Driver 把真凭据留在外部 secret manager，运行时挂载。
- **选型价值**：它应和 [[cloud-native-security]], [[agent-credential-isolation]] 一起看，而不是孤立评估。

## 相关页面

- [[secrets-store-csi-driver]]
- [[kubernetes]]
- [[cloud-native-security]]
- [[agent-credential-isolation]]
