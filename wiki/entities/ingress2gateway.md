---
title: ingress2gateway
tags: [entity, kubernetes, gateway-api, networking]
date: 2026-06-14
sources: [ingress2gateway-architecture-analysis.md]
related: ["[[ingress2gateway]]", "[[kubernetes]]", "[[gateway-api]]", "[[inference-routing]]"]
---

# ingress2gateway

ingress2gateway 把 Kubernetes Ingress resources 转换成 Gateway API resources，帮助从 annotation-heavy Ingress 迁移到 Gateway/HTTPRoute。 详见 [[src-ingress2gateway-architecture]]。

## 架构边界

它不负责流量转发，只负责迁移配置模型。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `Ingress -> Gateway API migration` 能力 | 适合，ingress2gateway 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[gateway-api]], [[inference-routing]] 组合。 |

## 核心组件

- Parser: 读取 Ingress/Service annotations
- Provider translators: nginx/contour/gce 等差异
- Gateway API renderer: Gateway/HTTPRoute/TLSRoute
- CLI/report: 迁移建议和限制

## 选型提示

把 ingress2gateway 放在 `Ingress -> Gateway API migration` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
