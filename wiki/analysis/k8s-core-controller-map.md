---
title: Kubernetes Core / Controller 项目地图
tags: [kubernetes, controller, operator, crd, project-map]
date: 2026-09-22
sources: [src-k8s-core-controllers-stars, src-controller-runtime-architecture, src-kubebuilder-architecture, src-controller-tools-architecture]
related: ["[[kubernetes]]", "[[gateway-api]]", "[[gitops]]", "[[ai-ops]]", "[[declarative-agent-management]]", "[[agent-sandbox]]", "[[agentcube]]", "[[llm-d-kubernetes-sigs-candidate-map]]", "[[kubernetes-workload-automation]]", "[[openkruise-kruise]]", "[[cloud-native-security]]", "[[controller-runtime]]", "[[kubebuilder]]", "[[controller-tools]]"]
---

# Kubernetes Core / Controller 项目地图

## 当前上游核验（2026-09-22）

本节是对官方仓库默认分支的当前观察；[[src-controller-runtime-architecture]]、[[src-kubebuilder-architecture]] 与 [[src-controller-tools-architecture]] 则是 2026-06-14 摄入的 raw-backed Source 快照，保留当时的代码结构与设计语境。

| 项目 | 当前证据 | 稳定职责边界 | M5-A 位置 |
|---|---|---|---|
| [[controller-runtime]] | [`6ab2188a1fb1`](https://github.com/kubernetes-sigs/controller-runtime/commit/6ab2188a1fb14a8c4837b418bc0a20049682cde4) | 组合 Manager、Cache、Client、Controller/Reconciler、Scheme、Webhook 与 envtest；不负责项目脚手架 | controller runtime composition |
| [[kubebuilder]] | [`5f31d1f3c075`](https://github.com/kubernetes-sigs/kubebuilder/commit/5f31d1f3c075507fb99c432babeb1469a07f0cb6) | 面向作者的 Kubernetes API/CRD/controller/webhook 脚手架、插件与开发工作流，建立在 controller-runtime 和 controller-tools 之上 | author workflow / scaffolding |
| [[controller-tools]] | [`030a93937cbb`](https://github.com/kubernetes-sigs/controller-tools/commit/030a93937cbbd72cc02cc2fe943f1df6e4b1f115) | 用 marker 驱动 `controller-gen` 生成 CRD、RBAC、webhook、deepcopy/object 与 apply-configuration 等资产 | marker / type generation |
| client-go | Kubernetes staged 基座（本次不单独锚定 HEAD） | 提供 clientset、discovery/dynamic client、transport 与 controller 所需 cache/informer/workqueue 机制；必须按 Kubernetes minor 版本选择匹配的 `client-go` / `k8s.io/*` 依赖 | client foundation |

上表的三个 commit 是本次执行时默认分支锚点，不代表 release；生产项目应按 controller-runtime / controller-tools / Kubebuilder 与 `client-go` / Kubernetes 的兼容矩阵锁定版本。官方入口：[controller-runtime repo](https://github.com/kubernetes-sigs/controller-runtime)、[Kubebuilder repo](https://github.com/kubernetes-sigs/kubebuilder)、[Kubebuilder Book](https://book.kubebuilder.io/)、[controller-tools repo](https://github.com/kubernetes-sigs/controller-tools)、[client-go docs](https://github.com/kubernetes/client-go#readme)。

这页把 [[src-k8s-core-controllers-stars]] 从 359 个 star 项目整理成 Kubernetes controller/operator 学习与选型地图。核心结论：K8s 平台工程的主线不是“会写一个 reconcile”，而是理解 API machinery、client/cache/workqueue、CRD/webhook、controller-runtime/kubebuilder、调度/多集群/安全/可观测这些层如何组合。

## D1 · Controller 工具链职责图

```text
BUILD-TIME（作者与生成链）
Kubebuilder CLI ── scaffold ──> Go API types / markers / project layout
                                   controller / webhook / test 骨架
Go API types / markers ── parse ──> controller-tools / controller-gen
controller-gen ── generate ──> CRD / RBAC / webhook manifests
               ── generate ──> deepcopy（object generator）/ applyconfiguration
作者补齐业务逻辑，构建 controller 镜像并安装生成的 manifests

RUNTIME（控制器执行链）
controller 二进制使用 controller-runtime 的组合层
  Manager：管理 Cache / Client / Controller-Reconciler / Webhook 生命周期
  Scheme：Go types 与 GVK 映射；供 Client 等组件使用
  client-go 基座：REST client / watch / informer / cache / workqueue
  Client ── write / uncached read ──> Kubernetes API server
  Kubernetes API server ── admission request ──> Webhook（同步响应）

测试支持（不属于生产 reconcile 路径）：controller-runtime / envtest
```

图例：实线 `── label ──>` 表示顺序生成或同步调用/API 写入；虚线 `- - label - ->` 专指下图的异步 watch、入队和重试反馈，标签说明触发原因。缩进表示组件组合，不表示一次调用。[[kubebuilder]] 组织作者工作流，[[controller-tools]] 解析 marker/type 并生成资产，[[controller-runtime]] 组合 client-go 的基础机制；这些项目分层组合，不能相互替代。Webhook 处理同步 admission 请求；envtest 为测试启动 API server 等控制面进程，不是生产集群的控制器。

## D3 · Reconcile 控制循环

```text
Manager 管理 Cache 与 Controller，Controller 消费自己的 workqueue
Kubernetes API server - - watch / observed-state feedback - -> Cache / informer
Cache / informer - - event handler: enqueue root object key - -> workqueue
workqueue ── worker 取 key 并调用 ──> Reconciler
Reconciler
  ├── Client.Get/List（默认缓存读）──> Cache：期望状态 + 已观测状态
  ├── Client.Create/Update/Patch/Delete ──> API server
  │                                        metadata/finalizer / owned resources
  ├── Client.Status().Update/Patch ──> API server
  │                                    status / conditions / observedGeneration
  └── return Result / error ──> Controller

Controller - - 可重试 error: rate-limited retry - -> workqueue
Controller - - RequeueAfter: delayed requeue - -> workqueue
API 写入后的变化 - - 经上述 watch/cache/enqueue 路径 - -> 后续 reconcile
```

Reconcile 是 level-based、幂等、异步收敛的控制循环，不是一次 event 对应一次必须完成的 request handler。事件可能合并；handler 把本对象或关联对象的变化映射为待处理 key，Reconciler 重新读取期望状态与可观测状态并计算差异。API 调用返回成功只确认该次写入成功，不代表 cache 已更新或依赖资源已经就绪；后续 watch 或显式 requeue 推进收敛。返回空 Result 且无 error 时，不主动安排重试。参见 [controller-runtime FAQ](https://github.com/kubernetes-sigs/controller-runtime/blob/6ab2188a1fb14a8c4837b418bc0a20049682cde4/FAQ.md) 与 [[src-controller-runtime-architecture]]。

## D4 · 状态与一致性

| 状态/机制 | Owner / operation | 陈旧或失败风险 | 恢复/收敛方式 |
|---|---|---|---|
| Cached read / direct write | Manager 默认 Client 对已缓存类型读 cache，写请求直达 API server；可配置直读 | 写成功后立即读 cache 仍可能是旧值；重复创建或错误判断缺失 | 确定性命名、幂等操作与后续 watch/requeue 再评估；必要时 APIReader 直读，但仍需处理读写间的并发 |
| `resourceVersion` conflict | API server 对 Update 或带版本前提的 Patch 做乐观并发检查 | 旧版本写入被拒绝；无版本前提的 Patch 不自动提供同等保护 | 重读、重算再提交；按更新策略显式选择版本前提，避免盲目覆盖竞争字段 |
| `spec` / `status` / conditions / `observedGeneration` | 用户或上游 controller 写 `spec`；本 controller 按 API 约定写 status/condition | status 对应旧 generation，或把“已观察”误解成“已成功” | `observedGeneration` 记录实际处理的 generation；condition 表达处理结果，仅在内容变化时写入；`lastTransitionTime` 随 condition 状态转换更新 |
| `ownerReference` / GC | controller 设置 owner UID/作用域；garbage collector 按引用与删除策略处理依赖资源 | 错 UID、跨作用域引用或错误接管导致泄漏/误删；ownerReference 本身不配置 watch | 校验 owner 与 controller 归属，显式设置 owned-resource watch；缺失资源且仍被期望时重建，错误归属需修正代码/对象 |
| Finalizer / `deletionTimestamp` | controller 在删除前完成外部清理，成功后移除 finalizer | 外部系统不可用、权限变化或旧 controller 消失导致删除卡住 | 可重试的清理 + backoff；无法恢复时由人工核实外部状态后审慎移除 finalizer |
| Requeue / rate limit / idempotency | Controller 根据 Result/error 安排队列；业务代码负责副作用幂等 | 高频事件、自触发 status write 或非幂等副作用形成 hot loop；队列不提供 exactly-once | 差异写入、幂等键和可恢复清理；错误重试使用 backoff，定时检查用 `RequeueAfter`，不假设它等同错误退避 |

API 一致性与删除机制分别参见 [Kubernetes API Concepts](https://kubernetes.io/docs/reference/using-api/api-concepts/) 和 [Kubebuilder Finalizers](https://book.kubebuilder.io/reference/using-finalizers.html)。

## D5 · 失败边界

| 起因 | 直接影响 / 因果链 | 自动恢复边界 | 需要人工修复的情况 |
|---|---|---|---|
| Stale cache | 旧观测值 → 旧决策或写冲突 | watch 恢复与缓存追上后可收敛；显式定时 requeue 可补充检查，不能替代失效的 watch | cache 长期不同步、watch/RBAC 错误或业务逻辑把旧值当不变量 |
| Write conflict | 并发变更 → API server 拒绝旧 `resourceVersion` 写入 | 重读、重算、requeue；幂等 reconcile 通常可自恢复 | 持续字段所有权争用或错误的 patch 策略 |
| Hot reconcile | 自触发写入/永久错误 → queue、API server 与日志压力 | backoff 限制错误重试；普通 watch 入队不会统一受错误退避保护，不能靠重试机制消除热循环 | 修正非幂等逻辑、无差异 status patch 或永久错误分类；谨慎配置 predicate，避免过滤必要事件 |
| Webhook / certificate unavailable | admission 调用失败 → `failurePolicy: Fail` 时写入失败，`Ignore` 时可能跳过失败调用继续 | 已配置的 Pod 重启/证书轮换恢复服务后，调用方重试才可继续；框架不自动修复证书配置 | 错误 CA bundle、Service/DNS、证书轮换配置或 webhook 逻辑；显式拒绝请求不因 `Ignore` 而放行 |
| Leader switch | 启用 leader election 时旧 leader 失租 → 可用副本获得租约并接管 | 依赖正确的选主配置与健康副本；缓存同步和初始/后续事件重建待处理工作，队列并非持久化交接 | 非幂等外部副作用已部分执行，或新 leader 因配置/权限无法启动；选主不保证外部操作 exactly-once |
| Stuck finalizer | `deletionTimestamp` 已设 → 清理失败 → 对象长期 Terminating | 外部依赖恢复且清理幂等时可重试收敛 | controller 已移除、外部资源不可查或永久失败；需核实后再人工处理 finalizer |
| Wrong ownership / status | 错 ownerReference → 泄漏/误 GC；错 status/condition → 上游误判 | 只有当 reconcile 逻辑能识别并重建/更正时才可自恢复 | 修正 controller 逻辑和现有对象，评估误删/外部副作用后重新 reconcile |

## 学习路径

| 阶段 | 关键项目 | 应该掌握什么 |
|---|---|---|
| API 基础 | kubernetes, kubectl, apimachinery | object meta、GVK/GVR、watch、resourceVersion、server-side apply |
| Client 基座 | client-go, sample-controller | informer、lister、workqueue、rate limit、reconcile 幂等 |
| Operator 工具链 | controller-runtime, kubebuilder, controller-tools | 区分脚手架、marker/type 生成与运行时；掌握 manager、cache、client、scheme、webhook、envtest |
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

### controller-tools

controller-tools 提供 marker 解析与 `controller-gen` 生成器，把 Go API types/markers 转换成 CRD、RBAC、webhook、deepcopy/object 和 apply-configuration 等资产。它既不负责项目脚手架，也不运行 reconcile loop。

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
- 想写生产 Operator：用 kubebuilder 组织项目、controller-tools 生成资产、controller-runtime 实现控制循环；已有工程可直接组合后两者，无需重建脚手架。
- 想理解平台控制面：对比 KEDA、Kueue、autoscaler、gateway-api、prometheus-operator。
- 想理解 AI Infra on K8s：把 model serving operator、GPU operator、agent sandbox operator 放到同一个 reconcile 模型下看。
