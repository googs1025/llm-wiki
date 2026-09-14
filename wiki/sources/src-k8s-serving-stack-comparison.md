---
title: Kubernetes Serving Stack 对比：llm-d、AIBrix、KServe、KubeAI、OME、GPUStack、RBG、Kthena
tags: [architecture, kubernetes, llm-serving, model-serving, inference-routing, gpu]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[llm-inference]], [[model-serving-operator]], [[inference-routing]], [[dynamo]], [[llm-d]], [[aibrix]], [[kserve]], [[kubeai]], [[ome]], [[gpustack]], [[rbg]], [[kthena]]
---

# Kubernetes Serving Stack 对比

> 原文：`raw/k8s-serving-stack-comparison-2026-09-13.md` · 资料范围：各项目当前 README 与官方文档

## 核心判断

这八个项目不在同一个抽象层：llm-d、AIBrix、Kthena 偏分布式推理 serving；KServe、OME、KubeAI 偏模型服务 control plane；GPUStack 偏 GPU/MaaS 平台；RBG 偏多角色、有状态 workload 原语。

```
                         应用 / OpenAI-compatible API
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        │                         入口与路由                          │
        │ Kthena Router · AIBrix Gateway · llm-d EPP · KServe Router │
        └─────────────────────────────┬─────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │             推理 workload 编排                  │
              │ llm-d · Kthena ModelServing · RBG RoleBasedGroup│
              └───────────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │           模型生命周期与 runtime 抽象             │
              │ KServe · OME · KubeAI · Kthena ModelBooster      │
              └───────────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │          GPU 集群 / 多云 / MaaS 资源平台          │
              │ GPUStack · Kubernetes · Volcano · GPU Operator  │
              └─────────────────────────────────────────────────┘
```

## 对比结论

| 项目 | 最适合 | 不要误解成 |
|---|---|---|
| [[llm-d]] | Gateway API + InferencePool + 分布式 LLM | 一个新的推理 engine |
| [[aibrix]] | vLLM fleet、LoRA、KV、企业 serving 组件 | 通用模型 API 标准 |
| [[kserve]] | predictive + generative AI 的统一 K8s 平台 | 只针对 LLM 的专用 router |
| [[kubeai]] | 快速部署 OpenAI-compatible 模型服务 | 复杂 P/D topology controller |
| [[ome]] | model/runtime/accelerator 生命周期抽象 | KV-aware traffic plane |
| [[gpustack]] | GPU 集群、多云、MaaS、计量运维 | 轻量 K8s CRD 库 |
| [[rbg]] | 多角色、有状态、协调式 inference workload | 完整 API gateway |
| [[kthena]] | K8s 原生 LLM serving、路由、P/D、Volcano | 只负责模型生命周期的 operator |

## 选型路径

```
你首先需要什么？
        │
        ├─ 传统 ML + GenAI 统一 API / Kubeflow 生态？ ──► KServe
        │
        ├─ 轻量快速把模型变成 OpenAI API？ ───────────► KubeAI
        │
        ├─ runtime / accelerator / model lifecycle 抽象？ ─► OME
        │
        ├─ GPU 集群、多云、MaaS、计量与运维一体化？ ───► GPUStack
        │
        ├─ Gateway API + InferencePool + 分布式 LLM？ ───► llm-d
        │
        ├─ vLLM fleet + LoRA/KV/企业组件？ ───────────► AIBrix
        │
        ├─ 多角色、有状态、P/D workload 协调原语？ ────► RBG
        │
        └─ K8s 原生完整 LLM serving + Volcano 拓扑？ ──► Kthena
```

这组比较补充了 [[llm-inference]] 的 K8s serving stack 层，也把 [[model-serving-operator]] 与 [[inference-routing]] 的边界拆开：有的项目管模型生命周期，有的管在线请求选择，有的管 GPU 资源，有的提供多角色 workload 原语。
