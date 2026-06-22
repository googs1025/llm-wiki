---
title: MUSA Learning Notes
tags: [entity, gpu, musa, cuda, ai-infra, learning]
date: 2026-06-21
sources: [musa-learning-notes-architecture-analysis.md]
related: ["[[gpu-programming-learning]]", "[[src-musa-learning-notes-architecture]]", "[[src-ai-infra-learning-cn-stars]]", "[[llm-inference]]", "[[k8s-gpu-device-stack]]"]
---

# MUSA Learning Notes

MUSA Learning Notes 是 `googs1025/musa-learning-notes` 的 GPU 编程学习日志，用 6 周路线和 38 个 MUSA 示例串起 MUSA SDK、CUDA→MUSA 迁移、Stream/Graph、访存、GEMM、调试、多卡和 torch_musa。详见 [[src-musa-learning-notes-architecture]]。

## 架构边界

它不是生产 SDK、推理引擎或 benchmark 平台，而是 [[gpu-programming-learning]] 系列中的实践入口。仓库把学习路线放在 `docs/roadmap.md`，把概念和迁移规则放在 `docs/concepts.md` / `docs/cuda-vs-musa.md`，把可运行实验放在 `code/week1` 到 `code/week6`，再用 notes 记录 MUSA SDK 实测差异。

## 适合 / 不适合

| 场景 | 判断 |
|------|------|
| 想从 CUDA 背景迁移到 MUSA | 适合，先看 CUDA→MUSA 映射，再按 week 跑示例 |
| 想补 GPU kernel 基础 | 适合，Runtime → Stream/Graph → Reduce/访存/GEMM 的路径清晰 |
| 想选型生产 LLM serving 平台 | 不适合，应看 [[llm-inference]], [[vllm]], [[sglang]], [[dynamo]], [[llm-d]] |
| 想管理 Kubernetes GPU 设备 | 不适合，应看 [[k8s-gpu-device-stack]], [[gpu-operator]], [[k8s-device-plugin]], [[gpu-sharing]] |

## 同类位置

与 CUDA_Freshman 相比，MUSA Learning Notes 更关注 MUSA SDK 和摩尔线程差异；与 LeetCUDA / LeetGPU 相比，它更像学习路径和迁移笔记，不只是题库。它可以作为 [[src-ai-infra-learning-cn-stars]] 中 GPU / CUDA / kernel 学习路线的本地实践补充。
