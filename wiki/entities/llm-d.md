---
title: llm-d
tags: [entity, llm-serving, kubernetes, gateway-api, inference-routing, distributed-inference]
date: 2026-09-13
sources: [k8s-serving-stack-comparison-2026-09-13.md]
related: [[llm-inference]], [[inference-routing]], [[model-serving-operator]], [[gateway-api]], [[kserve]], [[aibrix]], [[dynamo]], [[vllm]], [[sglang]]
---

# llm-d

llm-d 是 Kubernetes-native distributed inference stack，围绕 Gateway API/Inference Extension、EPP、InferencePool 和 model server 组织，并扩展 KV cache、P/D、autoscaling、benchmark、batch 与 simulator。

## 解决的问题

它把单机 vLLM/SGLang engine 提升为可在 Kubernetes 上运行的分布式 LLM 服务：请求要按 endpoint 状态、KV locality 和推理负载选择，P/D worker 要能协同，多个 serving variant 要能做容量分配。

## 核心边界

llm-d 是 serving ecosystem，不是新的推理 engine，也不是单一 operator。Gateway/EPP 负责入口和 endpoint picking，InferencePool 表达后端集合，KV/P/D/variant autoscaling 等项目补充性能关键路径。

## 适用场景

适合已经采用 Gateway API、希望标准化多模型/多 endpoint 入口，并需要分布式推理性能的 Kubernetes 平台。若只需单模型快速部署，[[kubeai]] 更轻；若需要更深的 engine runtime/P-D/KV 一体化，可比较 [[dynamo]]；若需要 GPU 集群 MaaS，可比较 [[gpustack]]。

详见 [[src-llm-d-architecture]] 与 [[src-k8s-serving-stack-comparison]]。
