---
title: Kubernetes Workload Automation
tags: [concept, kubernetes, workload, operator, platform-engineering]
date: 2026-06-16
sources: [openkruise-projects-current-state.md, kueue-architecture-analysis.md, karpenter-architecture-analysis.md, lws-architecture-analysis.md, jobset-architecture-analysis.md]
related: [[openkruise-kruise]], [[openkruise-rollouts]], [[kruise-game]], [[kruise-state-metrics]], [[controllermesh]], [[kueue]], [[karpenter]], [[lws]], [[jobset]], [[model-serving-operator]], [[gitops]], [[gateway-api]], [[cloud-native-security]], [[k8s-core-controller-map]]
---

# Kubernetes Workload Automation

Kubernetes workload automation 指在原生 Pod/Deployment/StatefulSet 之上，用 CRD/controller、队列、弹性、分布式 workload API、发布治理、可观测和控制器运行边界，把应用生命周期从“创建 Pod”提升到“表达业务 workload 意图”。

这个概念页是整体框架，不按单个项目或单个 OpenKruise 维度拆概念。[[openkruise-kruise]]、[[openkruise-rollouts]]、[[kruise-game]]、[[kueue]]、[[karpenter]]、[[lws]]、[[jobset]] 和 [[model-serving-operator]] 都只是它在不同 workload 场景里的实现样本。

## 主要层次

| 层次 | 代表 | 关注点 |
|---|---|---|
| Workload enhancement | [[openkruise-kruise]] | CloneSet、Advanced StatefulSet、SidecarSet、WorkloadSpread、ImagePullJob。 |
| Release governance | [[openkruise-rollouts]], [[gitops]], [[gateway-api]] | 分批、暂停、推进、回滚、流量切分和发布状态机。 |
| Specialized workload | [[kruise-game]], [[lws]], [[jobset]] | 游戏服务器、leader/worker、分布式 ML/HPC job 等业务语义。 |
| Queueing / admission | [[kueue]] | 多租户资源配额、入队、抢占和 workload admission。 |
| Capacity automation | [[karpenter]] | pending pods 到节点容量的弹性补充和 consolidation。 |
| Model serving | [[model-serving-operator]] | Model/InferenceService/LLMISvc 等 AI workload 生命周期。 |
| Observability | [[kruise-state-metrics]], [[metrics-server]], [[prometheus-adapter]] | workload/API 对象状态、资源指标和 custom metrics。 |
| Controller operation boundary | [[controllermesh]], [[controller-runtime]], [[cloud-native-security]] | 控制器权限、运行实例、对象范围、故障影响面和审计。 |

## 为什么重要

AI Infra、游戏服务器、大规模在线服务和批处理平台都不只是“跑一个 Deployment”。它们需要表达批次、队列、角色、容量、镜像预热、拓扑、回滚、指标、成本和控制器边界。把这些能力放进 Kubernetes API 后，平台才能复用 RBAC、watch、status、events、GitOps 和 controller 模型。

## 和项目实体的关系

| 项目类别 | 实体 | 在整体概念中的位置 |
|---|---|---|
| OpenKruise workload enhancement | [[openkruise-kruise]] | 把原生 workload 扩展成更贴近生产运维的 API。 |
| OpenKruise release governance | [[openkruise-rollouts]] | 把上线过程拆成可推进、可暂停、可回滚的控制状态。 |
| Specialized workload | [[kruise-game]], [[lws]], [[jobset]] | 把游戏服务器、leader/worker、分布式 job 这类业务结构变成 Kubernetes API。 |
| Resource admission / capacity | [[kueue]], [[karpenter]] | 一个管 workload 能否入场，一个管节点容量如何补足。 |
| Model workload | [[model-serving-operator]], [[llm-d]] | 把模型、runtime、endpoint、batch、autoscaling 放进集群控制面。 |
| Operations / reliability | [[kruise-state-metrics]], [[controllermesh]] | 一个补状态可观测，一个补控制器运行边界。 |

## 选型提示

先判断你要自动化的是哪一层：

- workload 对象本身不够表达业务：看 [[openkruise-kruise]]、[[kruise-game]]、[[lws]]、[[jobset]]。
- 发布过程需要受控推进：看 [[openkruise-rollouts]]，并放到 [[gitops]] 和 [[gateway-api]] 的发布/流量治理链路中评估。
- 多租户 batch/AI/HPC 需要排队入场：看 [[kueue]]。
- 节点容量和成本是瓶颈：看 [[karpenter]]。
- 模型服务生命周期是主问题：看 [[model-serving-operator]]。
- 控制器权限、故障半径或多 operator 管理是主问题：看 [[controllermesh]]，并结合 [[cloud-native-security]] 与 [[k8s-core-controller-map]] 判断运行边界。
