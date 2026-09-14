---
title: RouteLLM
tags: [entity, inference-routing, llm-routing, evaluation, python, model-selection]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[inference-routing]], [[ai-gateway]], [[semantic-router]], [[llm-inference]]
---

# RouteLLM

RouteLLM 是用于 serving 和 evaluating LLM routers 的 Python 框架。它围绕 strong/weak model 路由，通过 threshold 在质量与成本之间做决策，并提供 OpenAI client 替换、OpenAI-compatible server 和 benchmark/evaluation。

## 解决的问题

不是每个请求都需要最强、最贵模型。RouteLLM 用训练好的或可扩展的 router 估计请求是否值得升级，把简单请求发送到 weak/cheap model，把复杂请求发送到 strong model。

## 核心抽象

内置路由包括 matrix factorization、weighted Elo、BERT classifier、causal LLM classifier 和 random baseline；评测维度是 router、模型对、benchmark、质量和成本曲线。

## 边界与选型

RouteLLM 是模型选择算法/评测层，不是 Kubernetes gateway、endpoint picker 或 operator。需要生产语义策略看 [[semantic-router]]；需要 K8s endpoint 看 [[llm-d-router]] / [[gateway-api-inference-extension]]。

详见 [[src-routellm-architecture]]、[[src-k8s-gateway-routing-comparison]]。
