---
title: GPU Sharing
tags: [concept, gpu, kubernetes, sharing, scheduling]
date: 2026-10-02
sources: [hami-architecture-analysis.md, k8s-device-plugin-architecture-analysis.md, kvcached-architecture-analysis.md]
related: ["[[hami]]", "[[k8s-device-plugin]]", "[[gpu-operator]]", "[[kubernetes-dra]]", "[[device-plugin]]", "[[k8s-gpu-device-stack]]", "[[kubernetes-dra-design-deep-dive]]", "[[node-feature-discovery]]", "[[dra-driver-nvidia-gpu]]", "[[cdi]]", "[[kvcached]]", "[[elastic-kv-cache]]"]
---

# GPU Sharing

GPU sharing 指多个 workload 共享同一物理 GPU 或 MIG/MPS/time-slicing/vGPU 资源的调度与隔离方法。目标是在吞吐、隔离、成本和利用率之间取平衡。

## 在 M5-C Device / GPU 地图中的位置

共享方案要分别回答四件事：scheduler 如何选择设备并记账，allocator 如何交接设备，硬件是否分区，runtime 如何限制实际使用。[[node-feature-discovery]] 提供能力信号；[[k8s-device-plugin]]、[[dra-driver-nvidia-gpu]] 与 [[hami]] 采用的资源模型和隔离机制不同。[[cdi]] 只承载注入配置，不把记账额度自动变成隔离保证。完整分层见 [[k8s-gpu-device-stack]]，Claim 与节点准备的区别见 [[kubernetes-dra-design-deep-dive]]。

部署时须为同一物理设备和资源名明确分配所有权，尤其不能让 HAMi 与 NVIDIA 官方 plugin 在同一节点争用 `nvidia.com/gpu`。[[gpu-operator]] 可以管理软件组件，但需关闭冲突的 allocation operand；HAMi-DRA 改变分配路径，不等于改变 HAMi-core 的软件隔离边界。

## 主要路线

| 路线 | 代表 | 特点 |
|---|---|---|
| MIG | [[k8s-device-plugin]], [[gpu-operator]] | 硬件分区；plugin 可暴露预配置实例，分区配置由相应管理组件完成，粒度受硬件/profile 限制 |
| Time-slicing | [[k8s-device-plugin]] | 复用执行时间，不等于独立显存或硬件故障域隔离 |
| MPS | [[k8s-device-plugin]] | 通过 MPS 服务共享执行与配置资源限制；支持范围依版本，不等价于 MIG 硬件分区 |
| HAMi-core memory/core sharing | [[hami]] | 调度/记账配合容器内调用拦截，隔离效果取决于注入与兼容调用路径 |
| DRA device configuration | [[dra-driver-nvidia-gpu]] | 声明式 Claim 分配和设备配置；基础 API 稳定不意味着全部动态分区/共享扩展已稳定 |
| Application-aware elastic KV | [[kvcached]] | 只让接入的 vLLM/SGLang KV physical pages按需占用VRAM；不提供通用CUDA显存quota、执行隔离或K8s调度 |

## KVCacheD 在 GPU sharing 中的位置

[[kvcached]] 属于应用内、语义感知的内存复用：它知道哪些分配是KV block/token，因此可以在不停止模型的情况下按request生命周期map/unmap physical pages。MIG/MPS/time-slicing/HAMi则从设备或runtime层管理更广泛的GPU workload。

两者可以组合，但不能混为一谈：KVCacheD提高同卡多模型的KV利用率，外层方案仍需负责设备分配、记账、执行共享与租户隔离。详见 [[elastic-kv-cache]] 和 [[kvcached-sglang-vllm-knowledge-system]]。

## 和 GPU Operator 的关系

[[gpu-operator]] 管软件栈生命周期；GPU sharing 管 workload 如何共享设备。两者层级不同，但生产环境经常同时出现。
