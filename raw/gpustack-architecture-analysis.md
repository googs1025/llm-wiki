# GPUStack 架构与设计思路分析

> 仓库：https://github.com/gpustack/gpustack · 分析日期：2026-06-12 · 版本：HEAD `05d56cd`（2026-06-12，docs: envvars）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`gpustack/gpustack` 是 GPU cluster manager 和 model serving platform，偏“把 GPU/模型服务统一管理起来”，而不是单一 inference engine。源码分为 API/server、scheduler、worker、gateway、GPU detectors、cloud providers、K8s integration、migrations 和 charts。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `gpustack/gpustack` 是 GPU cluster manager 和 model serving platform，偏“把 G… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `gpustack/server`, `api`, `routes` · `gpustack/scheduler`, `policies`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `gpustack/worker`, `detectors`, `gpu_instances`                     │  │ `gpustack/gateway`, `websocket_proxy`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `gpustack/server`, `api`, `routes` | 服务端 API 和路由。 |
| `gpustack/scheduler`, `policies` | 模型部署和 GPU 调度策略。 |
| `gpustack/worker`, `detectors`, `gpu_instances` | 节点/worker 和 GPU 检测。 |
| `gpustack/gateway`, `websocket_proxy` | 请求入口和代理。 |
| `charts`, `docker-compose`, `docs` | 部署与文档。 |

## 关键数据流

1. 用户注册 workers/GPU 和模型。
2. server/scheduler 选择 worker/GPU 并启动 vLLM/SGLang/Ollama 等服务。
3. gateway 暴露统一 endpoint 并转发请求。

## 设计决策与哲学

- 把 GPU 发现、调度、模型生命周期和 endpoint 放到一个平台。
- Python 实现利于快速集成模型生态。
- 适合中小团队自管 GPU serving，不是 Gateway API 标准路线。

## 与已有项目的对比

和 KServe/OME/KubeAI 相比，GPUStack 更产品化 cluster manager；和 AIBrix/llm-d 相比，它更偏平台管理，不是专门研究高级 KV/P-D 路由。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
