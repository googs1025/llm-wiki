---
title: RouteLLM 架构与设计思路分析
tags: [architecture, llm-routing, evaluation, cost-quality]
date: 2026-06-12
sources: [routellm-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[llm-inference-serving-project-map]], [[mcp-gateway-tooling-map]]]
---

# RouteLLM 架构与设计思路分析

`lm-sys/RouteLLM` 是较早的 LLM router serving/evaluation framework，偏成本/质量路由算法基线。仓库小，核心在 `routellm/routers`、`routellm/evals` 和 benchmarks；最近 HEAD 停在 2024-08，不应按当前活跃 infra 项同等看待。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `lm-sys/RouteLLM` 是较早的 LLM router serving/evaluation framework，偏成本/质量路由算… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `routellm/routers` · `routellm/evals`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `benchmarks/**`                     │  │ `config.example.yaml`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `routellm/routers` | 不同 routing strategy。 |
| `routellm/evals` | 评估框架。 |
| `benchmarks/**` | MT-Bench 等 benchmark。 |
| `config.example.yaml` | 服务配置。 |

## 关键数据流

1. 请求先由 router 估计简单/困难或成本/质量权衡。
2. 路由到 cheaper/stronger model。
3. eval/benchmark 计算质量、成本和延迟指标。

## 设计决策

- 算法研究价值高，生产控制面弱。
- 健康检查 commit 说明有 serving 形态，但不是 cloud-native K8s control plane。
- 适合做 semantic/model routing baseline。

## 对比定位

和 semantic-router 相比，RouteLLM 更研究/算法；和 AI Gateway 项目相比，它不负责 auth、rate limit、provider 翻译。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
