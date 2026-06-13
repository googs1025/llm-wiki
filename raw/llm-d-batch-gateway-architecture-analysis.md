# llm-d Batch Gateway 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-batch-gateway · 分析日期：2026-06-13 · 版本：HEAD `66fae7e`（2026-06-11）

## 一句话定位

llm-d Batch Gateway 是 llm-d 生态里实现 OpenAI Batch API 的离线推理入口，把 `/v1/batches` 和 `/v1/files` 这类长时任务拆成 API server、持久化数据层、Redis/Valkey 队列、batch processor 和 GC。它不替代 llm-d Router 或 vLLM，而是在它们前面补上 batch job 生命周期、文件存储、重试、取消、进度、输出归档和 per-model 执行计划。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| API 入口 | `cmd/apiserver`, `internal/apiserver/{batch,file,server,middleware}` | 提供 OpenAI-compatible batch/file API，校验请求，写入 job/file 元数据，提交队列事件。 |
| 任务状态与队列 | `internal/database/{api,postgresql,redis}`, Redis/Valkey | PostgreSQL 保存 job/file 元数据，Redis/Valkey 保存优先级队列、事件、heartbeat 和进度。 |
| 文件存储 | `internal/files_store/{api,fs,s3,obj,retryclient}` | 管理 input/output/error JSONL 对象，支持本地 filesystem 和 S3/Object storage。 |
| Processor 控制循环 | `cmd/batch-processor`, `internal/processor/worker` | 拉取 job、预处理输入、执行推理、写结果、处理取消/过期/停机恢复。 |
| 推理客户端 | `pkg/clients/{http,inference}` | 对下游 llm-d Router / model endpoint 发 OpenAI-compatible 推理请求。 |
| 垃圾回收 | `cmd/batch-gc`, `internal/gc/{collector,reconciler}` | 清理过期 job/file，修复 DB/queue/object store 状态漂移。 |
| 部署 | `charts/batch-gateway` | Helm 部署 API server、processor、GC、存储和运行时参数。 |

这个分层的核心边界是：API server 不执行推理，processor 不暴露用户 API，GC 不参与正常调度。三者通过数据库、队列和对象存储形成可恢复的 batch control plane。

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

异常路径集中在 processor：`job_runner.go` 会处理 panic、取消、过期、SIGTERM 和系统错误；如果收到关闭信号，会尽量上传 partial result 并把 job 重新入队，避免 batch job 因 processor 实例退出而丢失。

## 设计决策与哲学

- **Batch job 是持久化控制面，不是一次 HTTP proxy**：API server、processor、GC 都以 PostgreSQL/Redis/Object Store 为边界，说明设计目标是长时可恢复任务，而不是把请求直接透传给 router。
- **按 model/system prompt 预处理而不是盲目逐行转发**：`internal/processor/worker/preprocessor.go` 会解析 model id、system prompt 并生成 per-model 计划，让后续执行可以更好地利用 model-aware scheduling。
- **processor 内部用多层并发阀门保护下游**：`internal/processor/worker/worker.go` 和 `executor.go` 同时使用 global semaphore、worker token 和 per-endpoint adaptive semaphore，说明它把 batch throughput 放在受控背压下，而不是简单 goroutine fan-out。
- **文件、状态、队列分离**：大对象走 S3/filesystem，元数据走 PostgreSQL，临时调度和事件走 Redis/Valkey，避免把 JSONL 输入输出塞进数据库。
- **运行态可观测和恢复优先**：`cmd/batch-processor/main.go` 启动 metrics、health、ready 和可选 pprof；processor 的 heartbeat、progress 和 stale job recovery 是一等路径。

## 关键组件深入解读

### Batch Processor（`internal/processor/worker`）

Processor 的 `Run()` 先做配置准备和 stale job recovery，再创建全局、worker 级、endpoint 级的并发控制器，最后进入 polling loop。`poller.go` 从 Redis priority queue 拉 job id，再到 DB 取 job；`job_runner.go` 是真正的生命周期编排器，负责启动 heartbeat、cancel watcher、preprocess、execute、finalize，并把 panic、取消、过期、关停统一映射到 job status 和重试语义。

### Preprocessor / Executor

`preprocessor.go` 把用户输入 JSONL 下载到本地，校验请求结构，解析模型和 system prompt，生成 output/error 文件和 per-model plan。`executor.go` 再按计划并发调用下游 inference endpoint，并持续把进度写回 Redis。这个拆分让“输入规范化”和“真正推理调用”解耦，也让 batch gateway 可以在不理解每个模型 runtime 细节的情况下做调度和恢复。

## 与同类对比

| 维度 | llm-d Batch Gateway | llm-d Router | KServe / KubeAI |
|------|---------------------|--------------|-----------------|
| 核心对象 | batch job、file、output/error JSONL | request、InferencePool、endpoint | model / inference service CRD |
| 主要职责 | 离线 batch 生命周期和文件语义 | 在线请求路由与 endpoint picking | 模型服务声明式部署 |
| 状态持久化 | PostgreSQL + Redis + object store | 多为 runtime/config/metrics state | Kubernetes API + controller status |
| 失败恢复 | stale job、heartbeat、partial output、requeue | endpoint health / retry / routing | reconcile loop / pod lifecycle |

## 性能 / 资源开销

仓库 README 明确以单个 job 最多 50,000 requests 为目标。实际吞吐受三层限制共同决定：processor worker 数、per-endpoint adaptive concurrency、下游 llm-d Router/model server 容量。源码里没有可直接引用的 benchmark 数字，生产选型需要用 `llm-d-benchmark` 或真实 workload 补测。

## 安全模型

API server 是 batch/file API 的鉴权入口；processor 只需要访问数据库、队列、对象存储和下游 router。部署侧强调 TLS、非 root、只读文件系统，以及 processor 到 router 的 HTTPS/mTLS。主要信任边界是：用户上传的 JSONL 不能直接影响 processor 本地路径或对象 key；下游 router 仍需独立处理 model inference 的鉴权和租户隔离。
