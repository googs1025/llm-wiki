---
title: Secrets Store CSI Driver
tags: [entity, kubernetes, security, storage]
date: 2026-06-14
sources: [secrets-store-csi-driver-architecture-analysis.md]
related: ["[[secrets-store-csi-driver]]", "[[kubernetes]]", "[[cloud-native-security]]", "[[agent-credential-isolation]]"]
---

# Secrets Store CSI Driver

Secrets Store CSI Driver 通过 CSI volume 把外部 secret store 注入 Pod，并支持 provider、rotation 和可选 Kubernetes Secret 同步。 详见 [[src-secrets-store-csi-driver-architecture]]。

## 架构边界

Kubernetes Secret 是集群内对象；Secrets Store CSI Driver 把真凭据留在外部 secret manager，运行时挂载。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `存储 / 凭据` 能力 | 适合，Secrets Store CSI Driver 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[cloud-native-security]], [[agent-credential-isolation]] 组合。 |

## 核心组件

- CSI node plugin: mount volume into pod
- Provider gRPC: Vault/Azure/GCP/AWS 等外部 secret
- SecretProviderClass API
- Rotation/sync controller

## 选型提示

把 Secrets Store CSI Driver 放在 `存储 / 凭据` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
