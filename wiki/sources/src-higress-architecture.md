---
title: Higress 架构与设计思路分析
tags: [architecture, ai-gateway, api-gateway, wasm, kubernetes]
date: 2026-06-12
sources: [higress-architecture-analysis.md]
related: [[[mcp-gateway-tooling-map]], [[agentgateway]], [[gateway-api]], [[mcp]], [[agent-credential-isolation]]]
---

# Higress 架构与设计思路分析

`higress-group/higress` 是阿里系 AI Native API Gateway，基于 Envoy/Istio 控制面和多语言 WASM plugins。P1 中它的价值是 AI gateway/模型路由/凭据治理背景，尤其和 HiClaw 的凭据托管、MCP/LLM 网关能力相关。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `higress-group/higress` 是阿里系 AI Native API Gateway，基于 Envoy/Istio 控制面和多语… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/higress`, `pkg/**` · `api/**`, `client/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `plugins/**`                     │  │ `istio/**`, `envoy/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/higress`, `pkg/**` | Higress 控制面与网关逻辑。 |
| `api/**`, `client/**` | API 与客户端。 |
| `plugins/**` | WASM 插件：Go/Rust/C++/AssemblyScript。 |
| `istio/**`, `envoy/**` | 上游控制面/数据面依赖。 |

## 关键数据流

1. 用户配置 route/model-router/plugin。
2. 控制面生成 Envoy/Istio 配置并下发。
3. WASM 插件在数据面处理 AI auth、model route、MCP/HTTP 策略。

## 设计决策

- 插件化和服务发现能力强，适合传统 API gateway + AI gateway 融合。
- model-router 保留原始模型名选项说明多 provider/model 映射是活跃问题。
- 仓库较大，应聚焦 plugin/model-router/control plane，不必全读 Istio vendor。

## 对比定位

和 kgateway 相比，Higress 更偏 API gateway 产品和插件生态；和 Envoy AI Gateway 相比，范围更宽但 GenAI 专注度较低。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
