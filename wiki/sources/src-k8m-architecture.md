---
title: k8m 架构与设计思路分析
tags: [architecture, kubernetes, ai-ops, dashboard, mcp]
date: 2026-06-12
sources: [k8m-architecture-analysis.md]
related: [[[ai-ops]], [[kubernetes]], [[mcp]], [[cloud-native-security]]]
---

# k8m 架构与设计思路分析

`weibaohui/k8m` 是轻量 K8s AI dashboard。目录显示 Go backend (`internal`, `pkg/controller/service/plugins`) + 前端 UI + deploy manifests + MCP/自托管 AI 文档，定位是把集群浏览、操作权限、异常检测和 AI/MCP 能力压进一个小型控制台。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `weibaohui/k8m` 是轻量 K8s AI dashboard。目录显示 Go backend (`internal`, `pkg/c… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `internal/dao`, `pkg/service` · `pkg/controller`, `pkg/plugins`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `pkg/middleware`, `pkg/models`                     │  │ `ui/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `internal/dao`, `pkg/service` | 后端数据访问和业务服务。 |
| `pkg/controller`, `pkg/plugins` | K8s 控制/插件扩展。 |
| `pkg/middleware`, `pkg/models` | HTTP 中间件和模型定义。 |
| `ui/**` | 前端控制台。 |

## 关键数据流

1. 用户通过 UI 选择集群/资源。
2. 后端调用 K8s API 和 plugins 获取资源状态。
3. AI/MCP 功能用于解释、排障或辅助生成操作。

## 设计决策

- Dashboard-first，比 CLI assistant 更适合非命令行用户。
- 插件/MCP 让 AI 能力可插拔，而不是写死在 controller 中。
- 项目活跃度比 P0 项目弱，适合作为形态参考。

## 对比定位

和 kubewall 相比，k8m 更强调 AI/MCP；和 kagent 相比，它是管理界面，不是 agent workflow 平台。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
