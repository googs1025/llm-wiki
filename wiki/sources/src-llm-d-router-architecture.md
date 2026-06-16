---
title: llm-d Router 架构与设计思路分析
tags: [architecture, llm-serving, routing, gateway-api, kubernetes]
date: 2026-06-12
sources: [llm-d-router-architecture-analysis.md]
related: [[llm-d-router]], [[llm-serving-engine-selection-map]], [[mcp-gateway-tooling-map]], [[agentgateway]], [[gateway-api]], [[kv-cache-offload]], [[disaggregated-serving]], [[kubernetes]]
---

# llm-d Router 架构与设计思路分析

`llm-d/llm-d-router` 是 llm-d 的智能入口。它通过 Envoy/ext-proc 或 Gateway API Inference Extension 接入流量，核心 EPP 用 filters、scorers、scrapers 和 scheduling profiles 对 InferencePool pods 做过滤/打分/选择；同时包含 disaggregation sidecar，协调 encode/prefill/decode 多阶段推理。

## 核心架构图

```text
┌──────────────────────────── proxy / gateway ────────────────────────────────┐
│ Envoy FULL_DUPLEX_STREAMED ext-proc · Gateway API · standalone mode           │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ Endpoint Picker (EPP)                                                         │
│ request parser · filters · scorers · scrapers · scheduling profiles           │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ K8s discovery/data layer      │  │ request management APIs                     │
│ InferencePool · endpoints     │  │ InferenceObjective · InferenceModelRewrite  │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected model server pod / P-D-E sidecar orchestration                       │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/epp`, `pkg/epp/server/**` | EPP server 和 controller manager。 |
| `pkg/epp/config`, `pkg/epp/framework/plugins/**` | EndpointPickerConfig、plugins、scheduling profiles。 |
| `pkg/epp/datalayer/**` | K8s binding、InferencePool endpoint graph、runtime state。 |
| `pkg/common/envoy/**` | Envoy request/response/header/metadata/chunking 辅助。 |

## 关键数据流

1. proxy 收到请求后把 headers/body stream 给 EPP ext-proc。
2. EPP 解析请求模型/priority/profile，加载 EndpointPickerConfig，按 filters 排除不合适 endpoints。
3. scorers 访问 scrapers/datastore 中的 load、KV、metrics 等信号，按权重打分；picker 选择最高分 pod。

## 设计决策

- plugin 化 filters/scorers/scrapers 是 Router 的核心：新增路由策略不改主循环。
- EPP 通过 Gateway API/GIE 与 K8s 标准对齐，避免自定义所有流量原语。
- InferenceObjective 和 ModelRewrite 让“请求目标”进入控制面，而不是硬编码在路由器配置里。

## 对比定位

和 AIBrix gateway plugins 相比，llm-d-router 更聚焦标准 Router/EPP；和 [[agentgateway]] 相比，它面向 model server pod placement，而不是 MCP/A2A/LLM access governance；和 RouteLLM/semantic-router 相比，它更 K8s/runtime metrics 驱动。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
