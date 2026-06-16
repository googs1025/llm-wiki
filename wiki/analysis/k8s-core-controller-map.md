---
title: Kubernetes Core / Controller 项目地图
tags: [kubernetes, controller, operator, crd, project-map]
date: 2026-06-13
sources: [src-k8s-core-controllers-stars]
related: [[kubernetes]], [[gateway-api]], [[gitops]], [[ai-ops]], [[declarative-agent-management]], [[agent-sandbox]], [[agentcube]], [[llm-d-kubernetes-sigs-candidate-map]], [[kubernetes-workload-automation]], [[openkruise-kruise]], [[cloud-native-security]]
---

# Kubernetes Core / Controller 项目地图

这页把 [[src-k8s-core-controllers-stars]] 从 359 个 star 项目整理成 Kubernetes controller/operator 学习与选型地图。核心结论：K8s 平台工程的主线不是“会写一个 reconcile”，而是理解 API machinery、client/cache/workqueue、CRD/webhook、controller-runtime/kubebuilder、调度/多集群/安全/可观测这些层如何组合。

```
User / platform workflows
  Argo CD · KEDA · [[kueue]] · [[openkruise-kruise]] · Karmada · KubeVela · AI Ops tools
        ↓
Controller / Operator framework
  client-go · [[controller-runtime]] · [[kubebuilder]] · operator-sdk · kube-rs
        ↓
Kubernetes API machinery
  apiserver · CRD · webhook · informer · cache · workqueue · finalizer
        ↓
Control plane extensions
  [[scheduler-plugins]] · autoscaler · gateway-api · admission · aggregated API
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
- [[openkruise-kruise]]、[[openkruise-rollouts]]、[[kruise-game]] 说明 workload controller 可以扩展到 [[kubernetes-workload-automation]] 下的 workload enhancement、release governance 和 specialized workload。
- [[gateway-api]]、[[agentgateway]]、[[kgateway]]、[[envoy-ai-gateway]] 都依赖 Gateway API / CRD / controller 语义。
- [[llm-d]]、[[kserve]]、[[ome]]、[[kubeai]]、[[aibrix]] 把 model serving 变成 Kubernetes control plane。
- [[gpu-operator]]、[[dra-driver-nvidia-gpu]]、[[hami]] 把 GPU 生命周期、DRA 和 sharing 策略放进 K8s。

因此理解 controller-runtime / kubebuilder / client-go，是理解这些 AI Infra 项目的共同底座。

## Kubernetes SIGs 维度拆分

更完整的候选清单见 [[llm-d-kubernetes-sigs-candidate-map]]。如果按工程维度而不是 SIG 名称拆，下一批最有价值的是：

| 维度 | P0 项目 | 和当前 wiki 的关系 |
|---|---|---|
| 网络 | [[external-dns]] | 补 [[gateway-api]] 之外的 DNS/LB/Ingress 控制器实战。 |
| 存储 / Secret | [[secrets-store-csi-driver]] | 补 [[cloud-native-security]]、凭据注入和 CSI 侧的工程边界。 |
| 调度 / 资源 | [[kueue]], [[karpenter]], [[scheduler-plugins]] | 补 AI/HPC/batch workload queueing、节点弹性和 scheduler 扩展。 |
| 可观测 / 性能 | [[metrics-server]], [[prometheus-adapter]], [[inference-perf]] | 补 HPA/custom metrics 和 GenAI benchmark。 |
| 计算 / Runtime | [[kind]], [[kubespray]], [[cri-tools]] | 补本地测试集群、生产集群部署和 kubelet/CRI 边界。 |
| API / Operator | [[controller-runtime]], [[kubebuilder]], [[controller-tools]], [[cluster-api]] | 把当前 controller 学习路径升级为正式架构页候选。 |
| AI Infra 交叉 | [[mcp-lifecycle-operator]], [[kube-agentic-networking]], [[lws]], [[jobset]] | 连接 [[mcp]]、Agent runtime、LLM serving 和分布式 workload API。 |

## OpenKruise 补充视角

[[openkruise-project-candidate-map]] 把 OpenKruise 生态拆成 workload enhancement、release governance、specialized workload、observability 和 controller operation boundary。概念层统一放入 [[kubernetes-workload-automation]]，避免按项目维度散出太多概念页。这条线补的是“业务 workload API 如何比原生 Deployment/StatefulSet 更贴近生产语义”，和 controller-runtime/kubebuilder 的“如何写 controller”是互补关系。

## 选型提示

- 想理解控制器底层：读 client-go 和 sample-controller。
- 想写生产 Operator：用 kubebuilder + controller-runtime。
- 想理解平台控制面：对比 KEDA、Kueue、autoscaler、gateway-api、prometheus-operator。
- 想理解 AI Infra on K8s：把 model serving operator、GPU operator、agent sandbox operator 放到同一个 reconcile 模型下看。
