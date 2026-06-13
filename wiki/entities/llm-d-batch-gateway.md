---
title: llm-d Batch Gateway
tags: [entity, llm-serving, batch-inference, llm-d]
date: 2026-06-13
sources: [llm-d-batch-gateway-architecture-analysis.md]
related: [[llm-d]], [[batch-inference]], [[llm-inference]], [[model-serving-operator]], [[inference-routing]]
---

# llm-d Batch Gateway

llm-d Batch Gateway 是 [[llm-d]] 生态里的 OpenAI Batch API 实现，把 `/v1/files`、`/v1/batches`、JSONL 输入输出、任务状态、取消、重试和归档做成一套离线推理控制面。详见 [[src-llm-d-batch-gateway-architecture]]。

## 架构边界

它不是推理引擎，也不是在线 [[inference-routing]] 组件。它位于用户 batch API 与下游 llm-d Router/model endpoint 之间，负责 [[batch-inference]] 的 job lifecycle、对象存储、PostgreSQL 元数据、Redis/Valkey queue、processor 执行和 GC。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 OpenAI-compatible Batch API | 适合，用 `/v1/files` + `/v1/batches` 承接长时任务。 |
| 大量 JSONL 请求需要异步执行 | 适合，processor 支持 per-model execution plan 和受控并发。 |
| 想复用 llm-d Router / serving endpoint | 适合，它把 batch workload 接到已有 serving fleet。 |
| 只需要在线低延迟请求 | 不适合，直接看 [[llm-d]] Router、[[gateway-api-inference-extension]] 或 AI Gateway。 |

## 同类对比

| 维度 | [[llm-d-batch-gateway]] | [[llm-d]] Router | [[kserve]] / [[kubeai]] |
|---|---|---|---|
| 抽象对象 | batch job / file / output | request / InferencePool / endpoint | model / inference service |
| 主要状态 | PostgreSQL + Redis + object store | endpoint metrics / routing config | Kubernetes API status |
| 关注点 | 离线 job 可恢复、输出归档、进度 | 在线 endpoint picking | 模型部署生命周期 |

## 选型提示

如果要比较 serving stack，先把在线请求和离线 batch 分开。[[llm-d-batch-gateway]] 解决的是“很多请求如何异步、可恢复、可审计地跑完”；[[inference-routing]] 解决的是“一个在线请求应该打到哪个 endpoint”。
