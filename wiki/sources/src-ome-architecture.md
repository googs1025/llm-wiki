---
title: OME 架构与设计思路分析
tags: [architecture, model-serving, kubernetes, operator, llm-serving]
date: 2026-06-12
sources: [ome-architecture-analysis.md]
related: [[[llm-serving-engine-selection-map]], [[kubernetes]], [[vllm]], [[disaggregated-serving]], [[kv-cache-offload]]]
---

# OME 架构与设计思路分析

`ome-projects/ome` 是 Open Model Engine，Kubernetes operator 路线的 LLM/model serving 控制面。仓库包含 manager、model-agent、ome-agent、CRD/config/webhook、runtime selector、accelerator class selector、storage/model download、OEP proposals。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `ome-projects/ome` 是 Open Model Engine，Kubernetes operator 路线的 LLM/model… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/manager`, `pkg/controller` · `cmd/model-agent`, `pkg/modelagent`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `cmd/ome-agent`, `internal/ome-agent`                     │  │ `pkg/runtimeselector`, `acceleratorclassselector`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/manager`, `pkg/controller` | operator manager 和 controllers。 |
| `cmd/model-agent`, `pkg/modelagent` | 模型拉取/管理 agent。 |
| `cmd/ome-agent`, `internal/ome-agent` | 运行时 sidecar/agent。 |
| `pkg/runtimeselector`, `acceleratorclassselector` | runtime/accelerator 选择。 |

## 关键数据流

1. 用户提交 OME model/workload CR。
2. controller 选择 runtime/accelerator/storage 并创建 K8s workload。
3. model-agent/ome-agent 处理模型下载、探测和运行时协作。

## 设计决策

- operator-first，强调模型生命周期和硬件适配。
- accelerator configs 的 data parallel override 是活跃问题。
- OEP 展示路线图比当前实现更宽。

## 对比定位

和 KServe 相比，OME 更 LLM/accelerator-aware；和 KubeAI 相比更偏 operator 基座和扩展提案。

## 相关链接

- GitHub 当前状态底稿：[[src-github-stars-backlog-current-state]]
- 选型地图：[[github-stars-backlog-implementation-map]]
