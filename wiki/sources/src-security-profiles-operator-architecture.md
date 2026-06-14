---
title: Security Profiles Operator 架构与设计思路分析
tags: [architecture, kubernetes, security, runtime]
date: 2026-06-14
sources: [security-profiles-operator-architecture-analysis.md]
related: ["[[security-profiles-operator]]", "[[kubernetes]]", "[[cloud-native-security]]", "[[agent-sandbox]]"]
---

# Security Profiles Operator 架构与设计思路分析

> 原文：`raw/security-profiles-operator-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/security-profiles-operator · 优先级 P1

## 一句话定位

Security Profiles Operator 管理 seccomp/AppArmor/SELinux profiles，并可通过 recording 把运行时行为转成可部署 profile。

## 核心架构图

```
┌────────────────────────────┐
│ User / platform intent     │
└──────────────┬─────────────┘
               │
┌──────────────▼─────────────┐
│ Security Profiles Operator │
│ control plane / tooling    │
└──────┬───────────┬────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ CRDs: Secc │ │ Daemon/control │
└──────┬─────┘ └───┬────────────┘
       │           │
┌──────▼─────┐ ┌───▼────────────┐
│ Recorder:  │ │ Admission/prof │
└────────────┘ └────────────────┘
               │
               ▼
     Kubernetes API / runtime / external systems
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CRDs | SeccompProfile, SelinuxProfile, ProfileRecording |
| Daemon/controller | install profiles on nodes |
| Recorder | capture syscalls/behavior |
| Admission/profile binding integrations | Admission/profile binding integrations |

## 关键数据流

```
用户声明或录制 profile
        │
        ▼
operator 分发到目标节点
        │
        ▼
Pod runtime 引用 profile
        │
        ▼
内核/runtime enforcement
        │
        ▼
状态和失败原因回写
```

## 设计决策与哲学

- **补齐 `Runtime security` 维度**：Security Profiles Operator 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：NetworkPolicy 管网络；SPO 管 syscall/LSM runtime confinement，适合高风险 workload 和 Agent sandbox 边界。
- **选型价值**：它应和 [[cloud-native-security]], [[agent-sandbox]] 一起看，而不是孤立评估。

## 相关页面

- [[security-profiles-operator]]
- [[kubernetes]]
- [[cloud-native-security]]
- [[agent-sandbox]]
