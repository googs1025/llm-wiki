---
title: Kata Containers
tags: [container-runtime, isolation, microvm]
date: 2026-05-13
sources: [agent-sandbox-architecture-analysis.md]
related: [[agent-sandbox]], [[gvisor]]
---

# Kata Containers

> Stub — 待充实

OpenInfra Foundation 旗下的**轻量 microVM 容器运行时**。每个 Pod 跑在独立的 QEMU 或 Firecracker microVM 里——真 Linux 内核但精简到秒级启动——把"容器的开发体验 + VM 的隔离强度"合到一起。

## 在 [[agent-sandbox]] 中的使用

K8s 配置 `runtimeClassName: kata-qemu` 或 `kata-fc`，agent-sandbox controller 原样透传给 Pod。`examples/kata-gke-sandbox/` 提供了 GKE 上 Kata 的完整 walkthrough。

## 与 [[gvisor]] 对比

详见 [[gvisor]] 页内对比表。**典型选择标准**：

- AI Agent 跑用户代码、强 syscall 兼容性要求 → Kata
- 高密度部署、syscall 密集型不多 → gVisor
- 不需要 multi-tenant 强隔离 → 直接 runc

## TODO

- [ ] 写 Kata 的双进程架构：runtime-rs + agent
- [ ] 写 Firecracker 与 QEMU 两种 hypervisor backend 的 trade-off
- [ ] GKE Sandbox 跟 Kata 的关系（GKE Sandbox 历史上用 gVisor，Kata 是另一个选项）
