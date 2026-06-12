---
title: kagent 架构与设计思路分析
tags: [architecture, kubernetes, ai-ops, agentic-ai, mcp]
date: 2026-06-12
sources: [kagent-architecture-analysis.md]
related: [[[ai-ops]], [[kubernetes]], [[mcp]], [[agent-runtime-sandbox-selection-map]], [[mcp-gateway-tooling-map]]]
---

# kagent 架构与设计思路分析

`kagent-dev/kagent` 是 cloud-native agentic AI 平台，面向 Kubernetes/DevOps 操作而不是通用 chat agent。仓库由 Go control plane、Python package/samples、Helm charts、UI、内置 tools/skills 组成，适合补 [[ai-ops]] 中“agentic workflow + MCP + K8s runtime”的路线。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kagent-dev/kagent` 是 cloud-native agentic AI 平台，面向 Kubernetes/DevOps 操作… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `go/api`, `go/core`, `go/adk` · `python/packages`, `python/samples`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `helm/**`                     │  │ `ui/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `go/api`, `go/core`, `go/adk` | Go 侧 API、核心对象和 ADK 集成。 |
| `python/packages`, `python/samples` | Python agent/tool package 和示例。 |
| `helm/**` | kagent、agents、tools 的安装分发。 |
| `ui/**` | 管理界面。 |

## 关键数据流

1. 用户从 UI/CLI/API 创建或调用 agent。
2. agent 通过工具/MCP/K8s API 执行 DevOps 操作。
3. Go control plane 负责状态、配置、流式事件和部署对象，Helm 安装到集群。

## 设计决策

- 按 cloud-native control plane 组织，而不是单机 CLI。
- 把 tools/skills 作为可扩展资产，适合和 MCP 网关路线结合。
- 最近 Bedrock streaming 修复说明其模型 provider 事件流是关键路径。

## 对比定位

和 `kubectl-ai` 相比，kagent 更像平台；和 `k8m`/`kubewall` 相比，它不是 dashboard，而是 agentic workflow 运行层。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
