---
title: Kubernetes
tags: [kubernetes, container-orchestration, cncf]
date: 2026-07-06
sources: [k8s-v1.36-sneak-peek.md, holmesgpt-k8s-alert-diagnosis.md, k3s-gitops-k0rdent.md, ai-vulnerability-discovery.md, src-kubernetes-resource-orchestration-keps.md]
related: ["[[argocd]]", "[[gateway-api]]", "[[opentelemetry]]", "[[ebpf]]", "[[gitops]]", "[[kubernetes-resource-orchestration]]", "[[kubernetes-scheduling-design]]", "[[kubernetes-autoscaling-design]]", "[[kubernetes-node-design]]"]
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

## 资源编排设计

[[src-kubernetes-resource-orchestration-keps]] 把 Kubernetes enhancements 中 `sig-scheduling`、`sig-autoscaling`、`sig-node` 三个 SIG 的 KEP 整理成新的业务域 [[kubernetes-resource-orchestration]]。

这个业务域将 Kubernetes 核心资源路径拆成三条线：

- [[kubernetes-scheduling-design]] — scheduler framework、队列、抢占、workload/gang、DRA 调度语义。
- [[kubernetes-autoscaling-design]] — HPA behavior、tolerance、metrics specificity、container metrics、scale from zero 和外部指标容错。
- [[kubernetes-node-design]] — kubelet、CRI、CPU/Memory/Topology Manager、device plugin、DRA、cgroup、安全和节点健康反馈。

## 相关概念
- [[gitops]] — 声明式交付模式
- [[ebpf]] — 内核级可观测和网络
- [[cloud-native-security]] — 云原生安全
- [[kubernetes-resource-orchestration]] — Kubernetes 调度、伸缩和节点执行的资源编排设计域
