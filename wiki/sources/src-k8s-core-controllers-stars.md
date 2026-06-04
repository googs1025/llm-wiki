---
title: K8s Core & Controllers Star 项目清单整理
tags: [kubernetes, controller, operator, crd, kubectl, client-go]
date: 2026-06-04
sources: [k8s-core-controllers-stars-list.md]
related: ["[[kubernetes]]", "[[gateway-api]]", "[[gitops]]", "[[ai-ops]]", "[[declarative-agent-management]]", "[[agent-sandbox]]", "[[agentcube]]"]
---

# K8s Core & Controllers Star 项目清单整理

> 原文：`raw/k8s-core-controllers-stars-list.md` · 来源：[googs1025 的 K8s Core & Controllers Stars list](https://github.com/stars/googs1025/lists/k8s-core-controllers) · 抓取日期：2026-06-04 · 仓库数：359

## 一句话定位

这个 Star list 是一张 [[kubernetes]] 平台工程底座地图：主线 Kubernetes、kubectl/client-go/controller-runtime/kubebuilder/operator SDK、CRD/webhook/sample-apiserver、调度/autoscaling/multicluster、网络/存储/备份、安全/策略、可观测/诊断，以及大量中文 controller/operator 学习实践项目都在同一张图里。

## 分层地图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ User / platform workflows                                                    │
│ Argo CD · Argo Workflows · Rollouts · KubeVela · KubeSphere · KEDA · K8sGPT  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Controller / Operator development                                            │
│ client-go · controller-runtime · Kubebuilder · sample-controller · kube-rs   │
│ webhook samples · operator lessons · custom controllers                      │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Kubernetes control plane / API machinery                                     │
│ kubernetes · kubectl · apiserver samples · gateway-api · kro · kcp · etcd    │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Scheduling / autoscaling / multi-cluster                                     │
│ autoscaler · scheduler-plugins · descheduler · kueue · karpenter · karmada   │
│ virtual-kubelet · vcluster · clusternet · kubeadmiral                        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Cluster substrate                                                            │
│ CNI · CSI · CRI · storage · backup · policy · observability · diagnostics    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 观察

- 这个 list 的核心不是“控制器项目很多”，而是完整呈现了 Kubernetes 平台工程的学习路径：先看主线/kubectl/client-go，再看 controller-runtime/kubebuilder/sample-controller，之后扩展到调度、网络、存储、安全、可观测和多集群。
- Controller 开发有明显的分层：`client-go` 是 API client 基座，`controller-runtime` 抽象 informer/cache/reconcile，`kubebuilder` 提供脚手架和 CRD 生成，sample-controller/sample-apiserver 是理解底层机制的参照。
- 真实生产控制器已经远超 Operator CRUD：KEDA、autoscaler、descheduler、kueue、karpenter、Grove、Armada 都是“控制循环 + 调度/队列/资源经济”的组合。
- 多集群和虚拟集群是另一条主线：Karmada、vCluster、Virtual Kubelet、KubeEdge/OpenYurt、kcp/Clusternet/KubeAdmiral 代表了不同的 control plane 复用方式。
- 可观测和 AI Ops 已进入 Kubernetes controller 生态：metrics-server/kube-state-metrics/prometheus-operator 是传统指标层，k8sgpt/kubectl-ai/krr/kubewizard/kube-agent-helper 则把诊断和建议推向 AI 辅助。

## 优先深挖候选

| 优先级 | 项目 | 原因 |
|--------|------|------|
| 1 | kubernetes-sigs/controller-runtime | Operator/controller 开发的核心抽象层。 |
| 2 | kubernetes-sigs/kubebuilder | CRD/API 生成和 controller 项目结构的标准样板。 |
| 3 | kubernetes/sample-controller | 理解 informer/workqueue/reconcile 的最小官方参照。 |
| 4 | kubernetes-sigs/kueue | AI/Batch workload queueing 与调度控制面。 |
| 5 | kubernetes/autoscaler | HPA/VPA/cluster-autoscaler 等弹性控制器集合。 |
| 6 | loft-sh/vcluster | 虚拟集群是平台多租户的重要路线。 |
| 7 | karmada-io/karmada | 多云多集群编排代表项目。 |
| 8 | [[gateway-api]] | 新一代 Kubernetes 网络 API，和 agentgateway/AI gateway 相关。 |
| 9 | prometheus-operator/prometheus-operator | Operator 模式的经典生产级案例。 |
| 10 | k8sgpt-ai/k8sgpt | AI 辅助 Kubernetes 诊断代表项目。 |

## 相关页面

- [[kubernetes]]
- [[gateway-api]]
- [[gitops]]
- [[ai-ops]]
- [[declarative-agent-management]]
- [[agent-sandbox]]
- [[agentcube]]
