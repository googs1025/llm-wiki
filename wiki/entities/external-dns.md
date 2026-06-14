---
title: external-dns
tags: [entity, kubernetes, networking, dns]
date: 2026-06-14
sources: [external-dns-architecture-analysis.md]
related: ["[[external-dns]]", "[[kubernetes]]", "[[gateway-api]]", "[[cloud-native-security]]"]
---

# external-dns

ExternalDNS 从 Service、Ingress、Gateway 等 Kubernetes 对象动态维护外部 DNS records，是声明式网络控制器代表。 详见 [[src-external-dns-architecture]]。

## 架构边界

Gateway/Ingress 决定流量入口；ExternalDNS 负责把入口地址发布到 DNS。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `网络 / DNS` 能力 | 适合，external-dns 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[gateway-api]], [[cloud-native-security]] 组合。 |

## 核心组件

- Sources: service/ingress/gateway/istio/contour 等
- Registry: TXT ownership and conflict protection
- Provider: Route53/CloudDNS/Cloudflare 等 DNS API
- Controller loop: desired endpoints -> record changes

## 选型提示

把 external-dns 放在 `网络 / DNS` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
