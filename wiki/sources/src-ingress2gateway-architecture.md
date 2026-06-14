---
title: ingress2gateway 架构与设计思路分析
tags: [architecture, kubernetes, gateway-api, networking]
date: 2026-06-14
sources: [ingress2gateway-architecture-analysis.md]
related: ["[[ingress2gateway]]", "[[kubernetes]]", "[[gateway-api]]", "[[inference-routing]]"]
---

# ingress2gateway 架构与设计思路分析

> 原文：`raw/ingress2gateway-architecture-analysis.md` · 仓库：https://github.com/kubernetes-sigs/ingress2gateway · 优先级 P1

## 一句话定位

ingress2gateway 把 Kubernetes Ingress resources 转换成 Gateway API resources，帮助从 annotation-heavy Ingress 迁移到 Gateway/HTTPRoute。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Existing Ingress estate                                                    │
│ Clusters have Ingress objects plus controller-specific annotations and     │
│ behaviors.                                                                 │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ ingress2gateway converter                                                  │
│ Reads Ingress resources and provider plugins to infer Gateway API          │
│ equivalents.                                                               │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Generated Gateway API                                                      │
│ Gateway, HTTPRoute, and related resources plus migration gaps and          │
│ unsupported fields.                                                        │
└────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ Output                                                                     │
│ Gateway API adoption plan that still requires validation against real      │
│ traffic behavior.                                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| Parser | 读取 Ingress/Service annotations |
| Provider translators | nginx/contour/gce 等差异 |
| Gateway API renderer | Gateway/HTTPRoute/TLSRoute |
| CLI/report | 迁移建议和限制 |

## 关键数据流

```
读取集群或 YAML Ingress
        │
        ▼
识别规则和 provider annotations
        │
        ▼
转换成 Gateway API resources
        │
        ▼
输出 YAML 和 warnings
        │
        ▼
用户审查后应用
```

## 设计决策与哲学

- **补齐 `Ingress -> Gateway API migration` 维度**：ingress2gateway 让当前 wiki 不只停留在 serving engine 或单个 operator，而能解释 Kubernetes 平台里的相邻控制面。
- **边界判断**：它不负责流量转发，只负责迁移配置模型。
- **选型价值**：它应和 [[gateway-api]], [[inference-routing]] 一起看，而不是孤立评估。

## 相关页面

- [[ingress2gateway]]
- [[kubernetes]]
- [[gateway-api]]
- [[inference-routing]]
