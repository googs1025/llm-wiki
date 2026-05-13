---
title: Kubernetes NetworkPolicy
tags: [kubernetes, network, security]
date: 2026-05-13
sources: [agent-sandbox-architecture-analysis.md]
related: [[kubernetes]], [[agent-sandbox]], [[cloud-native-security]]
---

# Kubernetes NetworkPolicy

> Stub — 待充实

K8s 内置的 **L3/L4 网络策略**资源（`networking.k8s.io/v1`）。用 podSelector 选定一组 Pod，声明它们的允许 ingress / egress 规则——任何不在白名单的流量被丢弃。**实际生效依赖 CNI 插件**（Calico / Cilium / Antrea 等）。

## 在 [[agent-sandbox]] 中的应用

`SandboxTemplate.Spec.NetworkPolicyManagement` 字段控制策略生成模式：
- **Managed（默认）**：controller 维护一个 Template 级共享 NetworkPolicy——默认 **deny all** + 仅放行公网 egress + **明确 deny RFC1918 内网网段** + **deny 云元数据服务**（169.254.169.254）。
- **Unmanaged**：用户自己管，controller 不碰（适合用 Cilium / NetworkPolicy CR 扩展接管）。

这个 default deny 决策很关键——因为 AI Agent 跑用户输入的代码，必须默认禁掉 SSRF 到云元数据 + 内网横向移动。

## TODO

- [ ] 写 NetworkPolicy 与 Cilium ClusterwideNetworkPolicy / FQDN policy 的关系
- [ ] 列出常见 CNI 插件对 NetworkPolicy 的支持完整度
- [ ] 写"AI Agent SSRF 防御"：metadata server + RFC1918 + 自定义 egress 域名黑名单
- [ ] NetworkPolicy 的局限：不能基于 L7（HTTP path / method），需要 Cilium 或 Gateway API 扩展
