---
title: vLLM Semantic Router 架构与设计思路分析
tags: [architecture, semantic-routing, llm-serving, vllm, ai-infra]
date: 2026-06-12
sources: [semantic-router-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[llm-inference-serving-project-map]], [[mcp-gateway-tooling-map]], [[vllm]], [[hybrid-search-rrf]]]
---

# vLLM Semantic Router 架构与设计思路分析

`vllm-project/semantic-router` 是 vLLM 生态的 system-level intelligent router，目标不是 KV cache locality，而是按请求语义/规则/模型能力做 mixture-of-models 路由。仓库超过 200MB，本次按 ingest-codebase 缩小到 `src/semantic-router`、Go/Rust bindings、config、deploy/operator、dashboard/README 等核心。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `vllm-project/semantic-router` 是 vLLM 生态的 system-level intelligent route… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `src/semantic-router`, `config/**` · `*-binding/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `deploy/**`                     │  │ `dashboard/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `src/semantic-router`, `config/**` | 语义路由主逻辑和决策配置。 |
| `*-binding/**` | Candle/ML/NLP/ONNX/OpenVINO 等加速/模型绑定。 |
| `deploy/**` | K8s/operator/helm/kserve/local 部署。 |
| `dashboard/**` | 管理界面，最近 first-admin setup 修复相关。 |

## 关键数据流

1. 请求进入 router。
2. router 读取 config 中 algorithm/decision/signal/knowledge base。
3. embedding/classifier/binding 产生语义信号，选择模型/endpoint。

## 设计决策

- 语义路由和 KV-aware routing 是不同维度，可叠加但不能混淆。
- 多 binding 说明它追求系统级低延迟/可部署性。
- dashboard/operator 表明它正从 library 走向平台组件。

## 对比定位

和 RouteLLM 相比，semantic-router 更工程化/系统化；和 llm-d-router 相比，它按语义/模型选择，不按 pod load/KV locality。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
