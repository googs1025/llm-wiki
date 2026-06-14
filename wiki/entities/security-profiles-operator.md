---
title: Security Profiles Operator
tags: [entity, kubernetes, security, runtime]
date: 2026-06-14
sources: [security-profiles-operator-architecture-analysis.md]
related: ["[[security-profiles-operator]]", "[[kubernetes]]", "[[cloud-native-security]]", "[[agent-sandbox]]"]
---

# Security Profiles Operator

Security Profiles Operator 管理 seccomp/AppArmor/SELinux profiles，并可通过 recording 把运行时行为转成可部署 profile。 详见 [[src-security-profiles-operator-architecture]]。

## 架构边界

NetworkPolicy 管网络；SPO 管 syscall/LSM runtime confinement，适合高风险 workload 和 Agent sandbox 边界。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Runtime security` 能力 | 适合，Security Profiles Operator 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[cloud-native-security]], [[agent-sandbox]] 组合。 |

## 核心组件

- CRDs: SeccompProfile, SelinuxProfile, ProfileRecording
- Daemon/controller: install profiles on nodes
- Recorder: capture syscalls/behavior
- Admission/profile binding integrations

## 选型提示

把 Security Profiles Operator 放在 `Runtime security` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
