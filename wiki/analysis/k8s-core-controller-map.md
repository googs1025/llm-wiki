---
title: Kubernetes Core / Controller 项目地图
tags: [kubernetes, controller, operator, crd, project-map]
date: 2026-06-13
sources: [src-k8s-core-controllers-stars]
related: [[kubernetes]], [[gateway-api]], [[gitops]], [[ai-ops]], [[declarative-agent-management]], [[agent-sandbox]], [[agentcube]]
---

# Kubernetes Core / Controller 项目地图

这页把 [[src-k8s-core-controllers-stars]] 从 359 个 star 项目整理成 Kubernetes controller/operator 学习与选型地图。核心结论：K8s 平台工程的主线不是“会写一个 reconcile”，而是理解 API machinery、client/cache/workqueue、CRD/webhook、controller-runtime/kubebuilder、调度/多集群/安全/可观测这些层如何组合。

```
User / platform workflows
  Argo CD · KEDA · Kueue · Karmada · KubeVela · AI Ops tools
        ↓
Controller / Operator framework
  client-go · controller-runtime · kubebuilder · operator-sdk · kube-rs
        ↓
Kubernetes API machinery
  apiserver · CRD · webhook · informer · cache · workqueue · finalizer
        ↓
Control plane extensions
  scheduler plugins · autoscaler · gateway-api · admission · aggregated API
        ↓
Cluster substrate
  CNI · CSI · CRI · etcd · observability · policy · diagnostics
```

## 学习路径

| 阶段 | 关键项目 | 应该掌握什么 |
|---|---|---|
| API 基础 | kubernetes, kubectl, apimachinery | object meta、GVK/GVR、watch、resourceVersion、server-side apply |
| Client 基座 | client-go, sample-controller | informer、lister、workqueue、rate limit、reconcile 幂等 |
| Operator 框架 | controller-runtime, kubebuilder | manager、cache、client、scheme、webhook、envtest、CRD 生成 |
| 生产控制器 | KEDA, autoscaler, kueue, gateway-api | 状态机、finalizer、条件、扩缩、队列、跨 namespace 引用 |
| 平台组合 | Argo CD, Karmada, vcluster, kcp | GitOps、多集群、虚拟集群、控制面复用 |
| 诊断与观测 | prometheus-operator, kube-state-metrics, k8sgpt | metrics、events、health、AI Ops 解释层 |

## 核心工具链边界

### client-go

client-go 是 Kubernetes API client 与 informer/workqueue 基座。学习它能理解控制器的底层机制：watch 如何变成本地 cache，事件如何进 queue，reconcile 为什么必须幂等，rate limiter 如何避免失败风暴。

### controller-runtime

controller-runtime 把 client-go 常用模式抽成 Manager、Controller、Reconciler、Cache、Client、Scheme、Webhook、Predicate 和 envtest。大多数现代 Operator 项目不直接手写底层 informer，而是通过 controller-runtime 组织 reconcile。

### kubebuilder

kubebuilder 是 CRD/controller 项目脚手架和代码生成路径：API type、marker、CRD YAML、webhook、RBAC、manager main、测试环境都从这里组织。它解决“项目怎样标准化”，不是替代 controller-runtime。

## 和当前 AI Infra 页面的关系

当前 wiki 中很多项目本质上都是 controller/operator：

- [[agent-sandbox]] 和 [[agentcube]] 用 CRD 管理 sandbox/session。
- [[gateway-api]]、[[agentgateway]]、[[kgateway]]、[[envoy-ai-gateway]] 都依赖 Gateway API / CRD / controller 语义。
- [[llm-d]]、[[kserve]]、[[ome]]、[[kubeai]]、[[aibrix]] 把 model serving 变成 Kubernetes control plane。
- [[gpu-operator]]、[[dra-driver-nvidia-gpu]]、[[hami]] 把 GPU 生命周期、DRA 和 sharing 策略放进 K8s。

因此理解 controller-runtime / kubebuilder / client-go，是理解这些 AI Infra 项目的共同底座。

## 选型提示

- 想理解控制器底层：读 client-go 和 sample-controller。
- 想写生产 Operator：用 kubebuilder + controller-runtime。
- 想理解平台控制面：对比 KEDA、Kueue、autoscaler、gateway-api、prometheus-operator。
- 想理解 AI Infra on K8s：把 model serving operator、GPU operator、agent sandbox operator 放到同一个 reconcile 模型下看。

