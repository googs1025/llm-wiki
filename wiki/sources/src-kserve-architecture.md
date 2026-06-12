---
title: KServe 架构与设计思路分析
tags: [architecture, model-serving, kubernetes, operator, inference]
date: 2026-06-12
sources: [kserve-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[kubernetes]], [[gateway-api]], [[vllm]], [[disaggregated-serving]]]
---

# KServe 架构与设计思路分析

`kserve/kserve` 是 Kubernetes 标准化 model serving 平台。仓库超过 200MB，本次缩小到 `cmd/manager/llmisvc/router/localmodel`、`pkg/apis/controller/webhook`、charts/config/docs。新近 commit 修复 LLMISvc HTTPRoute parent status 过滤，说明 Gateway API/LLM service 路线正在快速演进。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kserve/kserve` 是 Kubernetes 标准化 model serving 平台。仓库超过 200MB，本次缩小到 `cmd/… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/manager`, `pkg/controller` · `cmd/llmisvc`, `config/llmisvc`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `cmd/localmodel`, `config/localmodels`                     │  │ `pkg/apis`, `pkg/webhook`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/manager`, `pkg/controller` | 核心 controller manager。 |
| `cmd/llmisvc`, `config/llmisvc` | LLM InferenceService 相关控制面。 |
| `cmd/localmodel`, `config/localmodels` | 本地模型缓存/分发。 |
| `pkg/apis`, `pkg/webhook` | API 和 webhook。 |

## 关键数据流

1. 用户创建 InferenceService/LLMISvc/LocalModel 资源。
2. controllers 创建 predictor/router/storage runtime 和 Gateway/HTTPRoute。
3. status/webhook 维护可用性和校验。

## 设计决策

- KServe 是标准化/成熟路线，兼容传统 ML 与 GenAI。
- LLMISvc 是向 LLM serving 专门化的新增重点。
- 仓库历史包袱大，读源码要聚焦当前 LLMISvc/localmodel/control plane。

## 对比定位

和 OME/KubeAI 相比，KServe 更成熟和标准；和 llm-d/AIBrix 相比，它是 serving platform 基座，不专门做 SOTA routing/KV 优化。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
