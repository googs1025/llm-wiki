---
title: RouteLLM
tags: [entity, inference-routing, llm-routing, evaluation, python]
date: 2026-06-12
sources: [routellm-architecture-analysis.md]
related: [[inference-routing]], [[ai-gateway]], [[semantic-router]], [[llm-inference]]
---

# RouteLLM

RouteLLM 是成本/质量 LLM routing 的算法与评测基线项目，围绕 Python routers、evals 和 benchmarks 比较不同模型路由策略。详见 [[src-routellm-architecture]]。

## 架构边界

它更像路由算法参考和评测框架，不是生产级 Kubernetes gateway，也不是 model serving operator。与 [[semantic-router]] 相比，RouteLLM 偏成本/质量决策基线，semantic-router 偏系统级 router / dashboard / operator。

## 选型判断

适合快速理解 LLM routing 的质量-成本权衡、离线评测和基线实现。不适合直接承担 K8s endpoint picking 或多后端生产流量治理。
