---
title: SGLang
tags: [entity, ai-infra, llm-inference, llm-serving, kv-cache, oss]
date: 2026-10-03
sources: [src-sglang-architecture, src-kvcached-architecture]
related: ["[[vllm]]", "[[kvcached]]", "[[elastic-kv-cache]]", "[[radix-attention]]", "[[paged-attention]]", "[[continuous-batching]]", "[[disaggregated-serving]]", "[[llm-serving-performance]]", "[[llm-serving-reliability]]", "[[llm-inference-serving-project-map]]", "[[llm-serving-engine-selection-map]]"]
---

# SGLang

SGLang 是以 Scheduler、ModelRunner 和前缀 KV 复用为核心的 LLM 推理与 serving 引擎；[[radix-attention]] 描述其前缀组织思路。

## 当前核验（2026-10-03）

核验 release 为 [v0.5.21](https://github.com/sgl-project/sglang/releases/tag/v0.5.21)，发布于 2026-10-02（GitHub UTC 日期）。固定 tag 中可直接核验 [Scheduler](https://github.com/sgl-project/sglang/blob/v0.5.21/python/sglang/srt/managers/scheduler.py)、[ModelRunner](https://github.com/sgl-project/sglang/blob/v0.5.21/python/sglang/srt/model_executor/model_runner.py) 和 [RadixCache](https://github.com/sgl-project/sglang/blob/v0.5.21/python/sglang/srt/mem_cache/radix_cache.py)。

[[src-sglang-architecture]] 保留 2026-09-14 本地 HEAD `2fd835b9c1` 的架构分析。其算法数量、进程数量、默认 backend 和性能数字只反映该快照，不作为当前所有部署的共同特性。

## 架构与状态边界

| 组件 | 责任与状态 |
|---|---|
| Tokenizer / API 层 | 协议入口、输入预处理、提交请求和响应处理 |
| Scheduler | waiting/running 请求、执行预算与批次组织，协调 cache 和 worker |
| RadixCache / KV pool | 前缀身份、命中、引用与淘汰，以及实际 KV 槽位 |
| ModelRunner | 模型前向、attention backend、设备执行及引擎并行配置 |

[[continuous-batching]] 与 chunked prefill 决定不同请求如何共享执行窗口；[[radix-attention]] 减少可复用前缀的计算。v0.5.21 的 RadixKey 匹配按 `page_size` 对齐，因此任意 token 粒度并非通用保证。radix 节点和 [[vllm]] / [[paged-attention]] 的 block table 也不是同一对象。[v0.5.21 RadixCache](https://github.com/sgl-project/sglang/blob/v0.5.21/python/sglang/srt/mem_cache/radix_cache.py)

Engine 仍拥有本地 KV 布局、有效性与生命周期。外部 router 的 locality index 只提供选点线索，TP/PP/EP/DP 是引擎执行并行方式，平台 prefill/decode 角色划分与副本扩缩则是另一层职责。

## P/D 与缓存集成的版本范围

[v0.5.21 P/D 指南](https://github.com/sgl-project/sglang/blob/v0.5.21/docs/docs/advanced_features/pd_disaggregation.mdx)描述 Mooncake、NIXL 等传输集成及硬件约束，并列出有状态 Responses 工作流的限制。不能由存在 transfer backend 推出所有模型、cache layout、协议功能和并行方式都能任意组合；见 [[disaggregated-serving]]。

分层缓存、offload 与外部 runtime 还各有版本契约。例如 [[dynamo]] 的发行版固定了自己的 SGLang 依赖，独立 engine 的最新版不能自动替换进去。缓存恢复、请求取消和传输失败的验证应纳入 [[llm-serving-reliability]]。

## 适用与采用成本

- 适合：目标模型和硬件已获支持、前缀复用或调度优化有明确收益空间，并能持续做版本回归的推理团队。
- 不适合：希望把 engine 安装本身当成 Kubernetes 多模型治理、完整 fleet 路由和扩缩方案，或无法验证所需 backend 组合的场景。
- 下一步核验：固定模型、量化、attention/transfer backend、cache layout 与并行配置，对目标请求长度和前缀分布测 TTFT/ITL、goodput 和内存压力。比较方法见 [[llm-serving-performance]]，避免套用历史论文倍数。

## 与 KVCacheD 的集成关系

[[kvcached]] 保留 Scheduler、ScheduleBatch、[[radix-attention]] 和 attention backend，接入底层 token/page allocator 与 KV pool buffer allocation。RadixCache node 仍引用 KV indices；只有上层释放引用并让页中所有槽位空闲后，物理 backing 才能归还。

上述集成限定于 [[src-kvcached-architecture]] 的 KVCacheD `884108704f44` / SGLang `44ef8fecfe69` 快照：每个 TP worker 本地拥有自己的 KVCacheD pool，与 vLLM 的 Engine Core→worker fan-out 模式不同。它不构成对 v0.5.21 的兼容承诺；升级需核验 layout、allocator、cache events、P/D 与 worker 生命周期。详见 [[kvcached-sglang-vllm-knowledge-system]] 和 [[elastic-kv-cache]]。

## 在 M4 模块地图中的位置

SGLang 位于 engine/runtime 层，负责请求调度、前缀缓存与模型执行，通过版本化接口连接分布式 serving 层。职责见 [[llm-inference-serving-project-map]]，与 [[vllm]] 及外围平台的组合选择见 [[llm-serving-engine-selection-map]]。
