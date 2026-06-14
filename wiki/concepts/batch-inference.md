---
title: Batch Inference
tags: [concept, llm-serving, batch-inference, ai-infra]
date: 2026-06-13
sources: [llm-d-batch-gateway-architecture-analysis.md]
related: [[llm-d-batch-gateway]], [[llm-d]], [[llm-inference]], [[model-serving-operator]], [[inference-routing]]
---

# Batch Inference

Batch inference 指把大量推理请求作为离线或异步任务提交，系统负责排队、持久化、执行、重试、取消、进度追踪和结果归档。它和在线 serving 共用模型服务能力，但关注点不同：在线请求优化 tail latency，batch inference 优化吞吐、可靠性、成本和可审计输出。

## 和在线 serving 的区别

| 维度 | Batch inference | 在线 inference |
|---|---|---|
| 入口 | 文件 / job / JSONL / Batch API | HTTP/SSE/gRPC 单请求 |
| 用户体验 | 异步提交，稍后查询结果 | 同步或 streaming 返回 |
| 状态 | job status、progress、output/error file | request state、stream state |
| 调度目标 | 吞吐、成本、重试、可恢复 | 延迟、排队、公平性、cache hit |
| 代表项目 | [[llm-d-batch-gateway]] | [[llm-d]], [[gateway-api-inference-extension]], [[ai-gateway]] |

## 典型架构

```
Client uploads JSONL
        │
        ▼
Batch API creates file + job metadata
        │
        ▼
Queue stores executable job refs
        │
        ▼
Processor downloads input and builds execution plans
        │
        ▼
Model serving endpoints process requests under concurrency limits
        │
        ▼
Output/error files are uploaded and job status is finalized
```

## 选型提示

如果用户关心“一个请求尽快返回”，看 [[inference-routing]]、[[llm-inference]] 和 gateway；如果用户关心“几十万条请求稳定跑完、失败可追踪、结果可下载”，就需要 [[batch-inference]] 这一层。[[llm-d-batch-gateway]] 的价值正在于把 batch job control plane 和下游 [[llm-d]] serving fleet 解耦。
