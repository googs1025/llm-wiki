---
title: gVisor
tags: [container-runtime, isolation, sandbox]
date: 2026-05-13
sources: [agent-sandbox-architecture-analysis.md]
related: [[agent-sandbox]], [[kata-containers]]
---

# gVisor

> Stub — 待充实

Google 开源的 **用户态内核**容器隔离运行时（runsc）。在容器和宿主机内核之间插入一个 Go 实现的"应用内核"，拦截并重新实现 Linux 系统调用，让逃逸难度大幅升高——代价是少量性能损耗与部分 syscall 不兼容。

## 在 [[agent-sandbox]] 中的使用

K8s 配置 `runtimeClassName: gvisor`，agent-sandbox controller 原样透传给 Pod。这是 GKE Sandbox（GKE 用 gVisor 作为 untrusted workload 默认运行时）的承载机制。

## 与 [[kata-containers]] 对比

| 维度 | gVisor | Kata Containers |
|------|--------|-----------------|
| 隔离机制 | 用户态内核拦截 syscall | microVM（QEMU/Firecracker） |
| 启动开销 | 小（~1s） | 中等（~3-5s） |
| 性能损耗 | syscall 密集型 workload 受影响 | I/O 密集型 workload 受影响 |
| syscall 兼容 | 部分不兼容 | 完全（真 Linux 内核） |

## TODO

- [ ] 写 gVisor 的 platform：systrap vs ptrace vs kvm 三种 sentry 实现的取舍
- [ ] 写跟 OCI runtime spec 的对接（runsc 是 runc 的 drop-in 替换）
- [ ] 列出"AI Agent 跑用户代码"场景下，gVisor 已知不支持的 syscall（影响哪些工具链）
