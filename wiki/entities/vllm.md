---
title: vLLM
tags: [entity, ai-infra, llm-inference, llm-serving, kv-cache, oss]
date: 2026-10-03
sources: [src-vllm-architecture, src-kvcached-architecture]
related: ["[[sglang]]", "[[kvcached]]", "[[elastic-kv-cache]]", "[[paged-attention]]", "[[radix-attention]]", "[[continuous-batching]]", "[[llm-serving-performance]]", "[[disaggregated-serving]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# vLLM

vLLM 是 LLM 推理与 serving 引擎，拥有请求调度、模型执行和本地 KV 管理；[[paged-attention]] 是理解其 KV 分块寻址的重要入口。

## 当前核验（2026-10-03）

核验 release 为 [v0.30.0](https://github.com/vllm-project/vllm/releases/tag/v0.30.0)，发布于 2026-09-22（GitHub UTC 日期）。当日 [latest V1 架构文档](https://docs.vllm.ai/en/latest/design/arch_overview/#v1-process-architecture)将 API Server、Engine Core 与 GPU workers 分开；DP Coordinator 按部署方式启用，不能继续用“单进程主导”概括 V1。

[[src-vllm-architecture]] 是 2026-09-14 本地 HEAD `dc36fcce90` 的架构快照；下述当前核验与旧 Source 的类清单、默认值和性能数字分开解读。

## 架构与状态边界

| 组件 | 责任与状态 |
|---|---|
| API Server | HTTP/API、输入预处理、向 Engine Core 提交请求以及流式输出 |
| Engine Core | Scheduler、KV manager、请求状态和每轮执行协调 |
| GPU workers / ModelRunner | 权重加载、模型前向、attention backend 与设备 KV buffer |
| 条件启用的 DP Coordinator | 协调 DP ranks 的负载和执行；不是整个 Kubernetes fleet 的 autoscaler |

这些职责依据 [V1 process architecture](https://docs.vllm.ai/en/latest/design/arch_overview/#v1-process-architecture)。[[continuous-batching]] 决定每轮工作，[[paged-attention]] 和前缀缓存提供本地 KV 管理；外部 [[inference-routing]] 可以使用 cache events 做选点，但 KV 的布局、有效性与释放仍由 engine 管理。

TP/PP/EP/DP 属于引擎的执行并行方式，可以跨设备或节点；平台把实例分成 prefill/decode 角色池属于另一层的 [[disaggregated-serving]]。两层可以组合，不能把增加某种并行度等同于完成 P/D 编排。

## 分布式集成与选型

vLLM 通过 KV connector 接入 P/D、offload 或缓存系统；协议、attention layout、KV dtype、并行配置与依赖版本必须相容，不能仅凭“支持 vLLM”认定可用。官方提供独立的 [NIXL connector 兼容矩阵](https://docs.vllm.ai/en/latest/features/nixl_connector_compatibility/)；latest 文档中的支持项仍需对照实际安装 release。

- 适合：需要通用 engine 基线、OpenAI-compatible serving 或 Python 离线调用，并愿意按目标模型与硬件调优的团队。
- 不适合：目标模型、硬件或必需的 connector 组合不受部署版本支持，或期待 engine 单独提供多模型生命周期、fleet 路由与扩缩治理。只有单实例需求时，可先使用 engine，再按需要补外围平台。
- 下一步核验：固定模型、量化与 attention backend，测量 TTFT/ITL、goodput、KV 压力和抢占；需要分布式集成时，再检查 connector 与平台的 engine pins。指标定义见 [[llm-serving-performance]]。

与 [[sglang]] 的对照应使用同一 workload 和版本，不能用旧版算法数量、固定 block 大小或论文倍数给出通用排名。

## 与 KVCacheD 的集成关系

[[kvcached]] 位于 KV physical backing 下层，保留 Engine Core、Scheduler、[[paged-attention]] 和 attention backend。以下细节限定于 [[src-kvcached-architecture]] 记录的 KVCacheD `884108704f44` / vLLM `dc36fcce902a` 集成快照，不表示已验证 v0.30.0：

- ElasticBlockPool 承接 BlockPool 的 block/APC/ref-count 契约。
- GPUModelRunner 建立 VMM-backed KV tensor，并连接原生 KV buffer 使用路径。
- Engine Core 与 GPU workers 分进程时，通过 TP/PP worker 通信同步 map/unmap。
- 物理池耗尽转成分配失败，由 scheduler 处理 preempt/retry；async execution 下释放前需等待 worker barrier。

vLLM 管理请求所需逻辑 blocks，KVCacheD 管理这些 blocks 对应地址是否有实际 VRAM backing。完整关系见 [[kvcached-sglang-vllm-knowledge-system]] 与 [[elastic-kv-cache]]；升级必须回归 allocator、layout、connector 和 worker 生命周期的契约。

## 在 M4 模块地图中的位置

vLLM 位于 engine 层。本地 KV 与每轮执行的上方可以组合 router、分布式 runtime 和 Kubernetes 控制面，而不是将这些职责全部归入引擎。职责见 [[llm-inference-serving-project-map]]，组合与采用成本见 [[llm-serving-engine-selection-map]]。
