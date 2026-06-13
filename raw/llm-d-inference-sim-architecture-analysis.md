# llm-d Inference Sim 架构与设计思路分析

> 仓库：https://github.com/llm-d/llm-d-inference-sim · 分析日期：2026-06-13 · 版本：HEAD `6fb66f3`（2026-06-11）

## 一句话定位

llm-d Inference Sim 是一个轻量 vLLM 行为模拟器，用 Go 实现 OpenAI-compatible HTTP API、vLLM-compatible gRPC/API、KV cache 事件、LoRA 生命周期、延迟模型和 metrics，而不需要 GPU 或真实大模型。它的价值是让 router、scheduler、benchmark、autoscaler 和 P/D/KV cache 策略能在便宜、可控、可注入故障的环境中被验证。

## 核心架构图

```
┌───────────────────────────────────────────────┐
│ Clients / Routers / Benchmark Harnesses       │
│ OpenAI HTTP, vLLM gRPC, llm-d Router, tests   │
└───────────────────┬───────────────────────────┘
                    │ same port, cmux
┌───────────────────▼───────────────────────────┐
│ Communication Layer                           │
│ pkg/communication                             │
│ HTTP routes + gRPC server + graceful drain    │
└──────────────┬───────────────────────┬────────┘
               │ request               │ metrics/admin
               ▼                       ▼
┌──────────────────────────┐   ┌────────────────────────┐
│ OpenAI / vLLM API layer  │   │ /metrics /fake_metrics │
│ pkg/openai-server-api    │   │ health/ready/admin     │
└──────────────┬───────────┘   └────────────────────────┘
               │ normalized request
               ▼
┌───────────────────────────────────────────────┐
│ Simulator Core                               │
│ pkg/llm-d-inference-sim                      │
│ - DP rank simulators                         │
│ - worker pool                                │
│ - latency calculators                        │
│ - streaming/non-streaming response           │
└───────┬───────────────┬───────────────┬───────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐ ┌──────────────┐ ┌────────────────┐
│ Tokenizer   │ │ Dataset      │ │ KV Cache       │
│ HF/regex    │ │ prompts/data │ │ block keys     │
└─────────────┘ └──────────────┘ │ events/stats   │
                                 └───────┬────────┘
                                         │ ZMQ / metrics
                                         ▼
                                llm-d KV-aware routing tests
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 入口命令 | `cmd/llm-d-inference-sim`, `cmd/dataset-tool` | 读取配置、初始化 simulator、启动 HTTP/gRPC 通信层和数据集工具。 |
| 通信层 | `pkg/communication/{communication.go,http.go}` | 同端口 cmux HTTP/gRPC，OpenAI/vLLM/admin/metrics/health routes，graceful drain。 |
| API 适配 | `pkg/openai-server-api`, `pkg/vllm-api` | OpenAI-compatible completion/chat/responses/embeddings 和 vLLM-compatible 协议对象。 |
| 模拟核心 | `pkg/llm-d-inference-sim/{simulator.go,worker.go,latencies.go}` | 创建 DP rank simulator、worker pool、处理请求、模拟 TTFT/ITL/streaming。 |
| Token / Dataset | `pkg/tokenizer`, `pkg/dataset` | 支持 HuggingFace tokenizer、regex/simulated tokenizer、dataset-backed response。 |
| KV cache | `pkg/kv-cache` | 计算 llm-d kv block key，维护 block cache，生成 PrefixCacheStats 和事件。 |
| 部署 | `manifests`, `helm`, `deploy` | Kubernetes/Helm 部署，方便接入 llm-d stack 和 benchmark。 |

分层目标是让 simulator 同时像“vLLM 服务端”和“可控实验对象”：外部协议尽量兼容，内部行为则由配置驱动，便于复现实验。

## 关键数据流

```
OpenAI / vLLM 请求进入同一监听端口
        │
        ▼
cmux 分流 HTTP 或 gRPC
        │
        ▼
HTTP route / gRPC handler 解析请求
        │
        ▼
Simulator 根据 DP rank / worker pool 接收任务
        │
        ├── tokenizer 估算 prompt tokens
        ├── dataset 或 echo/random 生成候选输出
        ├── KV cache 计算 block keys / cached tokens
        ├── latency calculator 模拟 TTFT、ITL、remote prefill
        ├── failure injection / sleep / wake_up 可改变行为
        └── metrics / KV events 持续输出
        │
        ▼
Streaming 或 non-streaming response 返回给调用方
```

关闭路径也被显式建模：communication layer 在 drain 时先停止接新 HTTP 请求，再等待 open requests，最后停止 gRPC，避免 benchmark 或 router 测试误把“强杀连接”当成模型行为。

## 设计决策与哲学

- **协议兼容优先于真实模型计算**：它实现 OpenAI HTTP、vLLM/gRPC 和多种 admin/metrics endpoint，目标是让上游 router/autoscaler/benchmark 无需知道自己面对的是 simulator。
- **延迟是可配置模型，不是固定 sleep**：`latencies.go` 把 TTFT、inter-token、load factor、remote prefill/KV transfer 拆开，便于构造 P/D 和 cache locality 实验。
- **KV cache 行为是一等模拟对象**：`pkg/kv-cache/kv_cache.go` 计算 llm-d KV block key、cached prompt tokens 和 PrefixCacheStats，可测试 KV-aware routing，而不是只返回假文本。
- **同端口 HTTP/gRPC 更贴近 vLLM 部署形态**：`pkg/communication/communication.go` 使用 cmux，在一个 listener 上同时服务 HTTP 和 gRPC，减少测试环境与真实 vLLM server 的差异。
- **无 GPU 可运行降低系统实验门槛**：它把昂贵的 model runtime 替换为行为模拟，让 llm-d benchmark、router、WVA、Gateway API 相关测试能在 Kind 或普通集群中先跑通。

## 关键组件深入解读

### Communication Layer（`pkg/communication`）

`communication.go` 管理 listener、cmux、HTTP server、gRPC server 和 drain 逻辑；`http.go` 注册 `/v1/chat/completions`、`/v1/completions`、`/v1/responses`、`/inference/v1/generate`、embedding、models、LoRA load/unload、metrics、fake metrics、health/ready、Mooncake `/query`、tokenize、sleep/wake_up 等端点。这个层是 simulator 能被多类上游系统无缝接入的关键。

### Simulator Core / KV Cache

`simulator.go` 创建 dataset、tokenizer、DP rank simulator 和 worker pool；`worker.go` 处理请求、生成响应并发 metrics；`latencies.go` 计算 TTFT 和 inter-token delay。`pkg/kv-cache` 把 prompt token 转成 block key，并维护 block cache 与事件，给 llm-d Router/KV cache 相关实验提供可观测信号。

## 与同类对比

| 维度 | llm-d Inference Sim | vLLM | mock HTTP server |
|------|---------------------|------|------------------|
| 是否真实推理 | 否，行为模拟 | 是 | 否 |
| 协议兼容 | OpenAI + vLLM-like + admin/metrics | OpenAI/vLLM runtime API | 通常只模拟少量 endpoint |
| KV/cache 语义 | 模拟 block/cache/events | 真实 KV cache | 通常无 |
| 适合问题 | 路由、benchmark、autoscaling、P/D/KV 实验 | 性能与生产推理 | API 客户端单元测试 |

## 性能 / 资源开销

Inference Sim 主要消耗 CPU、内存和网络，不需要 GPU。它适合验证控制面、路由和指标闭环，但不能替代真实 vLLM/SGLang 的 kernel、显存、batching 和 GPU 通信性能测试。

## 安全模型

它面向测试/实验环境，暴露 sleep/wake_up、admin config、LoRA lifecycle、fake metrics 等控制接口。若部署在共享集群中，应通过 namespace/RBAC/network policy/ingress 限制访问，避免被外部调用者改变模拟行为或污染 benchmark 结果。
