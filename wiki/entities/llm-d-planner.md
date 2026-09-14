---
title: llm-d Planner
tags: [entity, llm-serving, capacity-planning, gpu, kubernetes, llm-d]
date: 2026-09-13
sources: [llm-d-core-projects-research-2026-09-13.md]
related: [[llm-d]], [[src-llm-d-core-projects-architecture]], [[model-serving-operator]], [[kubernetes]], [[vllm]], [[kserve]]
---

# llm-d Planner

[[llm-d-planner]] 是 llm-d-incubation 中的部署规划与推荐平台，把业务需求转换成模型/GPU/SLO/成本决策和 Kubernetes YAML。它处于 serving runtime 上游，不在在线 Router 请求路径中。

## 解决的问题

应用团队通常知道用户数、场景和预算，却不知道应该选什么模型、GPU、上下文长度、replica 数和 TTFT/ITL 目标。Planner 将这些决策从人工 trial-and-error 变成可解释、可编辑、可部署的流程。

## 架构图

~~~text
Business intent → Intent extraction → editable specification
                                      │ traffic + SLO + priorities
                                      ▼
Benchmark/quality/GPU/model knowledge base
                                      │
             capacity planner + recommender + scorer
                                      │ quality/cost/latency views
                                      ▼
              Jinja2 → KServe/vLLM/HPA/Monitor YAML
                                      │
                                      ▼
                                  Kubernetes
~~~

## 方法与集成

Planner 使用可替换 LLM provider 做 intent extraction，把 use case 映射到 traffic profile 和 TTFT/ITL/E2E SLO；Capacity Planner 估算 weights、KV、activation、GPU 数和并发；GPU Recommender 估算不同硬件的性能；Recommendation Service 按 quality、cost、latency 生成 Best Quality、Lowest Cost、Lowest Latency、Balanced 视图；Configuration Service 生成 KServe/vLLM/HPA/ServiceMonitor YAML。它还集成 vLLM simulator 支持无 GPU 开发。

当前定位偏 POC/平台入口，生产化仍需关注配置安全、认证、多租户、数据版本和实际部署 telemetry 回流。
