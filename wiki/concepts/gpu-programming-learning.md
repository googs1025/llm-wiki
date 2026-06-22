---
title: GPU 编程学习
tags: [concept, gpu, cuda, musa, ai-infra, learning]
date: 2026-06-21
sources: [musa-learning-notes-architecture-analysis.md, ai-infra-learning-cn-stars.md]
related: ["[[musa-learning-notes]]", "[[src-musa-learning-notes-architecture]]", "[[src-ai-infra-learning-cn-stars]]", "[[llm-inference]]", "[[k8s-gpu-device-stack]]", "[[paged-attention]]", "[[radix-attention]]"]
---

# GPU 编程学习

GPU 编程学习是从“会调用模型/框架”走向“能理解推理性能、显存瓶颈和 kernel 行为”的底层路径。当前 wiki 已有 [[src-ai-infra-learning-cn-stars]] 和 [[ai-infra-learning-cn-map]] 作为 AI Infra 学习路线，[[musa-learning-notes]] 则补上一个具体的 CUDA / MUSA 动手系列入口。

## 分层

| 层 | 目标 | 代表材料 |
|----|------|----------|
| 执行模型 | 理解 SIMT、warp、block、grid、同步和错误暴露 | [[musa-learning-notes]] Week 1/3 |
| Runtime API | 会写 host/device 内存管理、kernel launch、错误检查和计时 | [[musa-learning-notes]] Week 1/2 |
| 异步与吞吐 | 理解 pinned memory、Stream、Event、Graph 和 launch overhead | [[musa-learning-notes]] Week 2 |
| 访存与算子 | 理解 coalescing、shared memory、bank conflict、GEMM tiling | [[musa-learning-notes]] Week 4/5 |
| 迁移与生态 | 理解 CUDA→MUSA 的 API 高相似度和硬件/工具链差异 | [[src-musa-learning-notes-architecture]] |
| 系统连接 | 把 kernel 行为连接到 [[llm-inference]]、[[paged-attention]]、[[radix-attention]]、[[k8s-gpu-device-stack]] | wiki serving / GPU pages |

## 为什么要放进 AI Infra 路线

LLM serving 的瓶颈经常落在 GPU 侧：KV cache 布局、attention kernel、batching、P/D 分离、显存复用、launch overhead、通信和拓扑都会影响系统设计。只看 [[model-serving-operator]] 或 [[inference-routing]] 会理解控制面，但难以判断底层性能假设是否成立。

[[musa-learning-notes]] 的价值在于把学习问题缩小到可运行小实验：先跑 Runtime 骨架，再跑 Stream/Graph，再看 reduce、访存和 GEMM。它同时提醒 CUDA 经验不能直接等价迁移到 MUSA，尤其是 warp=128、`mcc` 工具链、muBLAS/MCCL 和 MUSA Graph 当前实现成熟度。

## 后续可扩展方向

- 为 [[gpu-programming-learning]] 继续摄入 CUDA_Freshman、LeetCUDA、LeetGPU 或 `a-hamdi/GPU`，形成 CUDA 与 MUSA 对照路线。
- 把 Week 3-5 的 Reduce、transpose、GEMM 实测补成性能表，再和 [[llm-inference]] 中的 kernel/attention 优化关联。
- 把 [[k8s-gpu-device-stack]] 的设备管理层与本页的 kernel 学习层区分清楚：前者回答“GPU 怎么分配给 workload”，后者回答“workload 在 GPU 上为什么快或慢”。
