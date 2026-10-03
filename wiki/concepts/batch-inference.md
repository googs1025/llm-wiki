---
title: Batch Inference
tags: [concept, llm-serving, batch-inference, ai-infra]
date: 2026-10-03
sources: [src-llm-d-batch-gateway-architecture]
related: ["[[llm-d-batch-gateway]]", "[[llm-d]]", "[[llm-inference]]", "[[model-serving-operator]]", "[[inference-routing]]", "[[continuous-batching]]", "[[llm-serving-performance]]", "[[llm-serving-reliability]]"]
---

# Batch Inference

Batch inference 指把大量推理请求作为离线或异步任务提交，系统负责排队、持久化、执行、重试、取消、进度追踪和结果归档。它和在线 serving 共用模型服务能力，但关注点不同：在线请求优化 tail latency，batch inference 优化吞吐、可靠性、成本和可审计输出。

它属于 job/file/queue/output 控制面。[[continuous-batching]] 则是 engine 每轮模型执行时重新组织请求的调度机制；batch 系统调用的下游 engine 完全可以使用连续批处理。异步作业与在线请求是一种交付模式差异，连续批与静态批是另一种执行调度差异，两者不是对立方案。

## 和在线 serving 的区别

| 维度 | Batch inference | 在线 inference |
|---|---|---|
| 入口 | 文件 / job / JSONL / Batch API | HTTP/SSE/gRPC 单请求 |
| 用户体验 | 异步提交，稍后查询结果 | 同步或 streaming 返回 |
| 状态 | job status、progress、output/error file | request state、stream state |
| 调度目标 | 吞吐、成本、重试、可恢复 | 延迟、排队、公平性、cache hit |
| 代表项目 | [[llm-d-batch-gateway]] | [[llm-d]], [[gateway-api-inference-extension]], [[ai-gateway]] |

## 典型架构

下图表示 [[src-llm-d-batch-gateway-architecture]] 历史快照提炼的职责模型，具体数据库、队列和 API 版本需按部署实现核验。

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

## 完成语义与验证

任务完成不能仅由队列取空判断：输出和错误记录必须持久化，并明确取消、超时、部分失败及重试后的状态。控制面的重试需要幂等或去重契约，不能因为 engine 返回一次成功就推断整个 job 恰好执行一次；详见 [[llm-serving-reliability]]。

性能评估同时记录 job 完成时间、截止时间达成率、有效结果吞吐与成本；共享在线 endpoint 时还需观察对在线 TTFT/ITL 的影响。下游连续批处理的 token/sequence/KV 预算由 engine 决定，上游 job 并发不能直接当成 engine batch size。统一测量口径见 [[llm-serving-performance]]。
