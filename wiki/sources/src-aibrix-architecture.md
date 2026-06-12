---
title: AIBrix 架构与设计思路分析
tags: [architecture, llm-serving, kubernetes, vllm, ai-infra]
date: 2026-06-12
sources: [aibrix-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[llm-inference-serving-project-map]], [[dynamo]], [[vllm]], [[kubernetes]], [[kv-cache-offload]], [[disaggregated-serving]]]
---

# AIBrix 架构与设计思路分析

`vllm-project/aibrix` 是 vLLM 生态的 Kubernetes GenAI inference infrastructure，而不是推理引擎。仓库包含 controller-manager、gateway plugins、KV cache watcher、CRD、webhook、metrics、cache、PodAutoscaler、ModelAdapter/RayCluster/Roleset 等模块，目标是把 vLLM 大规模部署、路由、扩缩容、LoRA、分布式推理和 KV cache 管理做成云原生控制面。

## 核心架构图

```text
┌──────────────────────────── OpenAI-compatible traffic ───────────────────────┐
│ HTTPRoute / Envoy Gateway / AIBrix gateway plugins                            │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ AIBrix control plane                                                          │
│ controllers · webhooks · metrics · routing cache · KV event manager           │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ CRDs                          │  │ runtime/data plane                          │
│ PodAutoscaler · ModelAdapter   │  │ vLLM pods · RayClusterFleet · KV cache sync │
│ StormService · KVCache         │  │ LoRA adapters · GPU optimizer/failure detect│
└───────────────────────────────┘  └────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/controllers`, `pkg/controller/**` | controller-runtime 控制面，PodAutoscaler 等 reconciler。 |
| `api/autoscaling`, `api/orchestration`, `api/model` | CRD API：PodAutoscaler、StormService、RayClusterFleet、Roleset、KVCache、ModelAdapter。 |
| `pkg/plugins/gateway/**` | gateway/routing 插件，包含 P/D disaggregation 路由逻辑。 |
| `pkg/cache`, `pkg/kvevent` | KV event manager、cache snapshot、pod/model cache、ZMQ 事件。 |

## 关键数据流

1. 用户通过 Gateway 访问模型，gateway plugin 根据 model labels、pod metrics、KV/cache 状态选择后端。
2. controller 监听 AIBrix CRD 和 K8s workload，创建/调整 vLLM/RayCluster/RoleSet 等资源。
3. PodAutoscaler 支持 HPA/KPA/APA，不同 metric source 包括 pod/resource/custom/external/domain。

## 设计决策

- AIBrix 把 vLLM 从单 engine 运维提升到 K8s control plane。
- 它比 llm-d 更像一体化发行：gateway、autoscaler、LoRA、KV cache、GPU failure detection 都在一个 repo。
- CRD + controller-runtime 是主线，Gateway API/Envoy 是流量入口。

## 对比定位

和 [[dynamo]] 相比，AIBrix 更 Kubernetes/controller-first；Dynamo 更强调推理系统运行时和分离式 P/D/KV 数据路径。和 llm-d 相比，AIBrix 更一体化，llm-d 更生态拆分（router、kv-cache、guides）。和 [[skypilot]] 相比，AIBrix 管集群内 inference，不管多云资源采购。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
