---
title: SkyPilot
tags: [entity, ai-infra, gpu, kubernetes, serving]
date: 2026-06-13
sources: [skypilot-architecture-analysis.md]
related: [[kubernetes]], [[llm-inference]], [[llm-inference-serving-project-map]], [[vllm]], [[sglang]], [[dynamo]], [[k8s-gpu-device-stack]]
---

# SkyPilot

SkyPilot 是面向 AI/ML 工作负载的多云算力控制平面。用户通过 YAML / Python API 声明 `Task`、`Dag`、`Resources`，SkyPilot 负责选择可用且便宜的 GPU/CPU/TPU 资源，完成 provisioning、文件同步、setup、run、日志流和自动回收。详见 [[src-skypilot-architecture]]。

## 架构边界

SkyPilot 不优化 LLM 推理内核，也不直接管理 KV cache。它位于 [[llm-inference]] 更上层：决定 workload 应该跑在哪个云、哪个区域、哪种实例、哪个集群，以及失败时如何 failover。

## 关键设计

- Client/SDK 把 YAML、CLI override、env/secrets、workdir 转成 Task/Dag。
- API server 负责鉴权、RBAC、request queue、blob storage 和日志流。
- Optimizer 按资源、价格、容量和失败 blocklist 选择 cloud/region/instance。
- CloudVmRayBackend 把资源选择落到 Ray cluster、Kubernetes、Slurm 或云 VM。
- Managed jobs / SkyServe / pools 在 launch/run 之上提供作业恢复和服务控制器。

## 选型判断

需要跨云 GPU 资源经济、failover 和 AI job/serve 控制时看 SkyPilot。需要单机推理引擎看 [[vllm]] / [[sglang]]；需要多节点 LLM serving 编排看 [[dynamo]] / [[llm-d]]；需要 Kubernetes GPU 设备层看 [[k8s-gpu-device-stack]]。

