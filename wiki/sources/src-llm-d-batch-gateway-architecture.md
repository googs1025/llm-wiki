---
title: llm-d Batch Gateway 架构与设计思路分析
tags: [architecture, llm-serving, batch-inference, ai-infra]
date: 2026-06-13
sources: [llm-d-batch-gateway-architecture-analysis.md]
related: [[llm-d-batch-gateway]], [[llm-d]], [[batch-inference]], [[llm-inference]], [[model-serving-operator]], [[inference-routing]]
---

# llm-d Batch Gateway 架构与设计思路分析

> 原文：`raw/llm-d-batch-gateway-architecture-analysis.md` · 仓库：https://github.com/llm-d/llm-d-batch-gateway · 分析版本 HEAD `66fae7e`

## 一句话定位

[[llm-d-batch-gateway]] 是 [[llm-d]] 生态里实现 OpenAI Batch API 的离线推理入口，把 `/v1/batches` 和 `/v1/files` 这类长时任务拆成 API server、持久化数据层、Redis/Valkey 队列、batch processor 和 GC。它不替代 [[inference-routing]] 或推理引擎，而是在前面补上 [[batch-inference]] 的 job 生命周期、文件存储、重试、取消、进度和输出归档。

## 核心架构图

```
┌──────────────────────┐
│ OpenAI Batch Client  │
│ /v1/files /v1/batches│
└──────────┬───────────┘
           │ HTTP
┌──────────▼───────────┐
│ API Server            │
│ cmd/apiserver         │
│ internal/apiserver    │
└─────┬─────────┬───────┘
      │         │
      │ metadata/status
      │         │ file objects
┌─────▼─────┐   │   ┌─────────────────────┐
│PostgreSQL │   └──►│ S3 / filesystem     │
│jobs/files │       │ input/output/error  │
└─────┬─────┘       └──────────┬──────────┘
      │                        │
      │ job refs/events        │ download/upload
┌─────▼────────────────────────▼──────────┐
│ Redis / Valkey priority queue + events  │
└─────┬───────────────────────────────────┘
      │ dequeue / heartbeat / progress
┌─────▼───────────────────────────────────┐
│ Batch Processor                         │
│ cmd/batch-processor                     │
│ internal/processor/worker               │
│ - preprocess JSONL                      │
│ - split per model/system prompt         │
│ - adaptive endpoint semaphores          │
└─────┬───────────────────────────────────┘
      │ OpenAI-compatible inference calls
┌─────▼───────────────────────────────────┐
│ llm-d Router / model serving endpoints  │
└─────────────────────────────────────────┘

┌──────────────────────┐
│ Batch GC             │
│ cmd/batch-gc         │
│ reconciler/collector │
└──────────┬───────────┘
           │ expire files/jobs and reconcile leaked state
           ▼
     PostgreSQL + Redis + S3/filesystem
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| API 入口 | 提供 OpenAI-compatible batch/file API，校验请求，写入 job/file 元数据，提交队列事件。 |
| 任务状态与队列 | PostgreSQL 保存 job/file 元数据，Redis/Valkey 保存优先级队列、事件、heartbeat 和进度。 |
| 文件存储 | 管理 input/output/error JSONL 对象，支持本地 filesystem 和 S3/Object storage。 |
| Processor 控制循环 | 拉取 job、预处理输入、执行推理、写结果、处理取消/过期/停机恢复。 |
| 推理客户端 | 对下游 [[llm-d]] Router / model endpoint 发 OpenAI-compatible 推理请求。 |
| 垃圾回收 | 清理过期 job/file，修复 DB/queue/object store 状态漂移。 |

## 关键数据流

```
用户上传 input JSONL
        │
        ▼
API Server 创建 file metadata + object storage record
        │
        ▼
用户创建 batch job
        │
        ▼
API Server 写 PostgreSQL job + Redis priority queue
        │
        ▼
Batch Processor dequeue job
        │
        ▼
Preprocessor 下载 input JSONL
        │
        ├── 校验 JSONL / request schema
        ├── 解析 model id / system prompt
        ├── 拒绝未注册 model
        └── 生成 per-model execution plan
        │
        ▼
Executor 并发调用 llm-d Router / endpoint
        │
        ├── 全局 worker semaphore
        ├── per-endpoint adaptive semaphore
        ├── heartbeat / cancellation watcher
        └── progress throttling via Redis
        │
        ▼
写 output.jsonl / error.jsonl
        │
        ▼
上传对象存储 + 更新 PostgreSQL final status
```

## 设计决策与哲学

- **Batch job 是持久化控制面，不是一次 HTTP proxy**：API server、processor、GC 都以 PostgreSQL/Redis/Object Store 为边界，目标是长时可恢复任务。
- **按 model/system prompt 预处理而不是盲目逐行转发**：输入 JSONL 会被解析并生成 per-model 执行计划，让 batch workload 更接近 [[llm-d]] 的 model-aware serving。
- **processor 内部用多层并发阀门保护下游**：global semaphore、worker token 和 per-endpoint adaptive semaphore 让 batch throughput 受控，而不是无限 fan-out。
- **文件、状态、队列分离**：大对象走 S3/filesystem，元数据走 PostgreSQL，调度和事件走 Redis/Valkey。

## 相关页面

- [[llm-d-batch-gateway]]
- [[batch-inference]]
- [[llm-d]]
- [[llm-inference]]
- [[model-serving-operator]]
