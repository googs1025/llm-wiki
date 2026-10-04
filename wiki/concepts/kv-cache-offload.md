---
title: KV Cache Offload（KV 多级缓存）
tags: [concept, ai-infra, kv-cache, llm-inference, memory-hierarchy]
date: 2026-10-03
sources: [src-dynamo-architecture, src-llm-d-kv-cache-architecture]
related: ["[[dynamo]]", "[[llm-d-kv-cache]]", "[[llm-d-router]]", "[[paged-attention]]", "[[radix-attention]]", "[[disaggregated-serving]]", "[[vllm]]", "[[sglang]]", "[[llm-inference]]", "[[inference-routing]]", "[[elastic-kv-cache]]", "[[llm-serving-performance]]", "[[llm-serving-reliability]]"]
---

# KV Cache Offload（KV 多级缓存）

KV cache offload 将实际 KV 数据复制到 GPU 之外的存储层，在需要时恢复到 engine 可使用的位置。CPU 内存、SSD 或远端存储可以保存副本；层级数量、持久性和自动升降级策略取决于具体实现。保存历史前缀可减少重复 prefill，但不会自动增加模型支持的上下文长度，也不保证比重新计算更快。

## 先区分四种状态

| 层或机制 | 持有什么 | 负责的动作 |
|---|---|---|
| Engine 本地 KV | block/token 槽位、引用和有效 KV 内容 | 分配、attention 寻址、实际命中验证与回收 |
| Offload / storage tier | 可恢复的 KV 数据副本及 tier residency | 写入、读取、迁移、容量和副本生命周期 |
| Locality index / router | prefix/block → worker/tier 的元数据 | 提供可能命中的位置和路由评分，不保存等价的 KV 副本 |
| GPU physical backing | 虚拟地址到实际显存页的映射 | [[elastic-kv-cache]] 的 map/unmap，和 CPU/SSD 数据保存是不同动作 |

[[paged-attention]] / [[radix-attention]] 管理的本地 KV 与外部索引不能混为一谈。索引命中后，engine 仍须检查缓存身份、布局、模型/adapter 与数据完整性；传输失败、条目过期或源副本被淘汰时，需要按策略重试、回退重算或失败。跨组件责任见 [[llm-inference#F2 · KV Block 生命周期|F2 · KV Block 生命周期]] 与 [[inference-routing]]。

## 写入与恢复的边界

写入侧先选择允许保留或迁移的 KV，保证在复制完成前源数据不被覆盖，再发布可读取的副本状态。恢复侧先确认缓存身份和兼容性，预留目的空间，完成实际数据复制，并在 engine 接受后才将对应前缀视为可用。外部 locality event 可以晚到或丢失，不能替代上述完成与有效性条件。

Offload 成本包括传输、排队、存储读写与恢复占用的 GPU 空间。是否值得采用，取决于这些成本是否低于节省的 prefill，以及是否改善目标 TTFT、goodput 和成本；见 [[llm-serving-performance]]。超时、取消、重复操作和已写副本的清理见 [[llm-serving-reliability]]。

## 当前核验：Dynamo KVBM 已废弃

> [!warning] Conflict
> NVIDIA Dynamo v1.5.0 已将 KVBM 标记为 deprecated，目标在 v1.6.0 移除。官方建议 host/disk offload 转向 engine-native integrations；早期 KV Cache Runner（KVCR）面向跨节点 KV cache sharing，**不是 KVBM 的直接替代品**。参见 [Dynamo v1.5.0 release 的迁移说明](https://github.com/ai-dynamo/dynamo/releases/tag/v1.5.0)（2026-10-03 核验）。

[[src-dynamo-architecture]] 提供其分析时点的 Dynamo 整体架构快照，其中涉及缓存、传输与 offload 的职责和设计。本页保留它作为历史架构阅读入口；当前 KVBM 状态与迁移依据以上官方 release。具体 CPU/磁盘层支持、connector 与 engine 版本需重新核验。

## 与直接 P/D transfer 的区别

[[disaggregated-serving]] 中 prefill worker 把当前请求生成的 KV 交给 decode worker，是执行阶段之间的状态交接；它可以直接 GPU→GPU 传输，并不必然经过 CPU/SSD，也不必保留可复用的持久副本。Offload 关注 KV 副本的存储与恢复，两者可能复用传输库或借助存储层组合，但不能因此把直接 P/D transfer 等同于 offload。

## llm-d 索引的历史与当前位置

[[llm-d-kv-cache]] / [[src-llm-d-kv-cache-architecture]] 记录迁移前的 locality index / scorer 架构，主要把 cache events 转成位置与命中评分。llm-d v0.10.0 已将 llm-d-kv-cache 代码迁入 [[llm-d-router]]；旧仓库废弃在该 release 时仍未全部完成。该版本还记录旧文件系统 connector 已并入 vLLM `OffloadingConnector`，原独立 connector 被废弃。[llm-d v0.10.0 release](https://github.com/llm-d/llm-d/releases/tag/v0.10.0)

索引代码合并并没有消除 metadata 与数据副本的边界。部署时分别确认谁生产 KV event、谁保存副本、谁搬运内容、谁在 engine 内验证恢复结果；项目组合见 [[llm-inference-serving-project-map]] 与 [[llm-serving-engine-selection-map]]。
