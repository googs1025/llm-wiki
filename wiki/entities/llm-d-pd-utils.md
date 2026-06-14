---
title: llm-d P/D Utils
tags: [entity, llm-serving, diagnostics, gpu]
date: 2026-06-14
sources: [llm-d-pd-utils-architecture-analysis.md]
related: ["[[llm-d-pd-utils]]", "[[kubernetes]]", "[[llm-d]]", "[[disaggregated-serving]]"]
---

# llm-d P/D Utils

llm-d P/D Utils 是面向 Prefill/Decode 分离部署的 skills/scripts 工具集，用于 preflight、GPU topology、RDMA/NCCL/network/NIXL 等诊断。 详见 [[src-llm-d-pd-utils-architecture]]。

## 架构边界

它不是 serving controller，而是 P/D 部署前后的诊断工具箱。

## 什么时候用

| 场景 | 判断 |
|---|---|
| 需要 `P/D diagnostics` 能力 | 适合，llm-d P/D Utils 正是这一层的代表项目。 |
| 需要和 Kubernetes API / controller / runtime 集成 | 适合，它的主要价值来自 Kubernetes-native 工作流。 |
| 需要替代相邻层全部职责 | 不适合，应和 [[llm-d]], [[disaggregated-serving]] 组合。 |

## 核心组件

- Preflight scripts: cluster and runtime checks
- GPU topology checks
- Network/RDMA/NCCL diagnostics
- Agentic skills/workflows for P/D deployment

## 选型提示

把 llm-d P/D Utils 放在 `P/D diagnostics` 维度评估：先看它输入什么对象、输出什么对象，再看它是否会进入请求路径、调度路径、节点路径或 CI/实验路径。这个边界比 star 数更能决定它是否适合当前平台。
