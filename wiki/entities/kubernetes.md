---
title: Kubernetes
tags: [kubernetes, container-orchestration, cncf]
date: 2026-07-06
sources: [k8s-v1.36-sneak-peek.md, holmesgpt-k8s-alert-diagnosis.md, k3s-gitops-k0rdent.md, ai-vulnerability-discovery.md, src-kubernetes-keps-design-tracking.md]
related: ["[[argocd]]", "[[gateway-api]]", "[[opentelemetry]]", "[[ebpf]]", "[[gitops]]", "[[kubernetes-keps-design-tracking]]", "[[kubernetes-dra]]", "[[kubernetes-workload-automation]]"]
---

# Kubernetes

容器编排平台，CNCF 毕业项目，云原生基础设施的核心。

## 最新动态

### v1.36（2026-04 即将发布）
- 弃用 `Service.spec.externalIPs`（安全风险）
- 移除 `gitRepo` Volume Driver
- SELinux 卷标签加速 GA
- [[ingress-nginx]] 退役
- 详见 [[src-k8s-v1.36-sneak-peek]]

## 生态工具
- **GitOps 交付**: [[argocd]]、Flux
- **轻量发行版**: K3s（适合 on-prem 和边缘场景，见 [[src-k3s-gitops-k0rdent]]）
- **可观测性**: [[opentelemetry]]、Prometheus、Grafana
- **AI 运维**: HolmesGPT 自动告警诊断（见 [[src-holmesgpt-k8s-alerts]]）
- **安全**: AI 漏洞发现带来新挑战（见 [[src-ai-vulnerability-discovery]]）

## KEP 设计追踪

[[src-kubernetes-keps-design-tracking]] 把本地 Kubernetes enhancements 中 `sig-scheduling`、`sig-autoscaling`、`sig-node` 三个 SIG 的 KEP 整理成 [[kubernetes-keps-design-tracking]]，用于持续追踪不同 SIG 的设计方案，而不是只按单一“资源编排”概念归档。

当前追踪模型按 SIG、设计分类、status、stage、latest milestone、优先级和跨 SIG 依赖组织：

- **SIG Scheduling** — scheduler framework/config、queue/requeue、topology/affinity、preemption、workload/gang、DRA/device-aware scheduling。
- **SIG Autoscaling** — HPA API/behavior、tolerance、metrics specificity、container metrics、scale from zero、external metrics failure handling 和 cluster autoscaler integration。
- **SIG Node** — kubelet/CRI、CPU/Memory/Topology Manager、in-place resource resize、device plugin/DRA/CDI、pod lifecycle、security/isolation 和 node health。

第一批 P0 追踪线包括 DRA device taints 与 partitionable devices、queueing hint / scheduler async preemption、HPA configurable tolerance / container resource metrics / scale-to-zero、in-place pod resize 与 sidecar containers。后续应优先补 `kep.yaml` / `prod-readiness.yaml` 中的 feature gates、metrics、rollback、scalability 和 upgrade/downgrade 信息。

## 相关概念
- [[gitops]] — 声明式交付模式
- [[ebpf]] — 内核级可观测和网络
- [[cloud-native-security]] — 云原生安全
- [[kubernetes-keps-design-tracking]] — 按 SIG 分类追踪 Kubernetes KEP 设计方案
