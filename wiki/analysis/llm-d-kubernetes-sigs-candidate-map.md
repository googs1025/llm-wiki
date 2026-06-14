---
title: llm-d / Kubernetes SIGs 候选项目地图
tags: [kubernetes, llm-serving, project-map, backlog, ai-infra]
date: 2026-06-13
sources: [src-k8s-core-controllers-stars, src-llm-d-architecture, src-llm-d-router-architecture, src-llm-d-kv-cache-architecture, src-llm-d-batch-gateway-architecture, src-llm-d-benchmark-architecture, src-llm-d-workload-variant-autoscaler-architecture, src-llm-d-inference-sim-architecture]
related: [[llm-d]], [[kubernetes]], [[k8s-core-controller-map]], [[k8s-gpu-device-stack]], [[llm-inference-serving-project-map]], [[model-serving-operator]], [[inference-routing]], [[llm-d-batch-gateway]], [[llm-d-benchmark]], [[llm-d-workload-variant-autoscaler]], [[llm-d-inference-sim]]
---

# llm-d / Kubernetes SIGs 候选项目地图

这页把 `llm-d` 组织和 `kubernetes-sigs` 组织里值得继续加入 wiki 的项目，按工程维度拆成候选清单。它不是 star 排行榜，而是服务于当前知识库的补全路线：哪些项目能帮助理解 [[llm-inference]]、[[model-serving-operator]]、[[kubernetes-dra]]、[[inference-routing]]、[[cloud-native-security]] 和 Kubernetes 控制器生态。

本次核验基于 GitHub API 当前公开仓库元数据（2026-06-13）。当前已收录的同域项目包括 [[llm-d]]、[[llm-d-batch-gateway]]、[[llm-d-benchmark]]、[[llm-d-workload-variant-autoscaler]]、[[llm-d-inference-sim]]、[[gateway-api]]、[[gateway-api-inference-extension]]、[[agent-sandbox]]、[[dra-driver-nvidia-gpu]]。

## 总体优先级

```
P0: 直接补当前 AI Infra / LLM serving / K8s control plane 选型缺口
P1: 强相关，但更偏评测、诊断、迁移、配套或特定场景
P2: 后续补充，先进入 backlog，不急于做完整源码架构页
```

| 优先级 | 项目 | 维度 | 加入价值 |
|---|---|---|---|
| P0 已完成 | [[llm-d-batch-gateway]] | LLM batch serving | 已补正式源码架构页，把 [[llm-d]] 从在线 inference 扩展到 OpenAI Batch API / 离线 batch workload。 |
| P0 已完成 | [[llm-d-benchmark]] | LLM serving benchmark | 已补正式源码架构页，作为 [[llm-inference-serving-project-map]] 的性能评测入口。 |
| P0 已完成 | [[llm-d-workload-variant-autoscaler]] | serving autoscaling | 已补正式源码架构页，补齐 variant / workload autoscaling 和资源经济链路。 |
| P0 已完成 | [[llm-d-inference-sim]] | inference simulator | 已补正式源码架构页，无 GPU 模拟 vLLM 行为，适合研究调度、benchmark 和路由策略。 |
| P0 已完成 | [[kueue]] | 调度 / 队列 | K8s 原生 Job queueing，是 AI/HPC/batch workload 控制面的核心项目。 |
| P0 已完成 | [[karpenter]] | 节点弹性 / 成本 | Node autoscaler，连接 serving SLO、GPU 成本和容量弹性。 |
| P0 已完成 | [[controller-runtime]] | Operator SDK | 现代 K8s controller 的通用抽象层，当前大量实体页都依赖它。 |
| P0 已完成 | [[kubebuilder]] | CRD / controller 脚手架 | 和 controller-runtime 一起构成 Operator 工程主线。 |
| P0 已完成 | [[metrics-server]] | 可观测 / autoscaling | HPA/VPA 基础指标源，解释 autoscaling 体系必需。 |
| P0 已完成 | [[external-dns]] | 网络 / DNS | K8s service/ingress/gateway 到 DNS record 的控制器代表。 |
| P0 已完成 | [[secrets-store-csi-driver]] | 存储 / 凭据 | CSI 方式注入外部 secret，连接凭据治理和 runtime security。 |
| P0 已完成 | [[kind]] | 计算 / 测试集群 | 本地 K8s 测试底座，很多 controller/operator 项目的开发环境基线。 |
| 排除 | `aws-load-balancer-controller` / `aws-ebs-csi-driver` / `aws-efs-csi-driver` | AWS 专项 | 用户明确本轮不需要。 |

## llm-d 组织候选

| 项目 | 优先级 | 当前定位 | 应放入的 wiki 主题 |
|---|---|---|---|
| [[llm-d-batch-gateway]] | P0 已完成 | OpenAI-compatible `/v1/batches` 和 `/v1/files`，把 batch job 分成 API server、processor、queue、storage、GC 等组件。 | [[llm-inference-serving-project-map]]、[[batch-inference]]、[[model-serving-operator]] |
| [[llm-d-benchmark]] | P0 已完成 | llm-d benchmark lifecycle/workspace/harness 编排。 | LLM serving benchmark、[[llm-inference]] |
| [[llm-d-workload-variant-autoscaler]] | P0 已完成 | distributed inference workload variant autoscaler。 | autoscaling、K8s resource economics、[[model-serving-operator]] |
| [[llm-d-inference-sim]] | P0 已完成 | 轻量模拟 vLLM 行为，不需要 GPU 或真实大模型。 | simulator、scheduler、benchmark |
| [[llm-d-latency-predictor]] | P1 已完成 | 给 inference scheduler 的 ML-based latency scoring service。 | latency predictor、[[inference-routing]] |
| [[llm-d-prism]] | P1 已完成 | 分布式推理性能分析 dashboard，把 benchmark 数据做交互式分析。 | observability、performance analysis |
| [[llm-d-pd-utils]] | P1 已完成 | Agentic Skills + scripts，用于 P/D 部署 preflight、GPU topology、RDMA/NCCL/network tests。 | P/D diagnostics、GPU/network validation |
| `llm-d-batch-gateway` 组件拆分 | P2 | API server / batch processor / GC / storage backend 可后续拆成细页。 | batch serving internals |
| `llm-d-inference-payload-processor` | P2 | inference payload processor，目前公开说明较薄。 | router/batch 辅助组件 |
| `llm-d-infra` / templates / `.github` | 暂缓 | 组织 CI、模板和治理基础设施。 | 不建议单独建架构页 |
| archived `deployer` / `model-service` / `routing-sidecar` | 暂缓 | 旧组件或已归档项目。 | 仅在追溯历史设计时引用 |

### llm-d 的知识结构缺口

当前 wiki 已经覆盖 [[llm-d]] 总入口、Router/EPP、KV cache 和 P0 四类外围能力：

- **Batch inference**：[[llm-d-batch-gateway]] 让在线 serving 与离线 batch workload 可以共享下游 router/model server，但 SLO、队列、存储和计费边界不同。
- **Performance evaluation**：[[llm-d-benchmark]] / `llm-d-prism` / [[llm-d-inference-sim]] 可以把“架构上可行”推进到“如何测、如何复现、如何调参”。
- **Autoscaling/resource economics**：[[llm-d-workload-variant-autoscaler]] 可连接 `Kueue`、`Karpenter`、GPU 资源层。
- **P/D deployment diagnostics**：`llm-d-pd-utils` 把 GPU topology、RDMA、NCCL、NIXL 等实际部署问题显性化。

## Kubernetes SIGs 候选：按工程维度

### 网络

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[external-dns]] | P0 已完成 | 从 Service/Ingress/Gateway 等 K8s 对象动态维护外部 DNS，是典型“声明式网络控制器”。 |
| `aws-load-balancer-controller` | 排除 | AWS LB / Ingress / Gateway API 的生产代表，适合和 [[gateway-api]] 放在同一条网络入口路线。 |
| [[gateway-api]] | 已有 | 已收录，作为新一代流量入口 API 基础。 |
| [[gateway-api-inference-extension]] | 已有 | 已收录，作为 LLM inference endpoint picking 标准层。 |
| [[ingress2gateway]] | P1 已完成 | 从 Ingress 迁移到 Gateway API 的工具，适合补迁移路线。 |
| [[apiserver-network-proxy]] | P1 已完成 | control plane 到节点网络代理，适合理解托管 K8s / 私有网络控制面连接。 |
| [[kube-agentic-networking]] | P1 已完成 | Agent/tool networking policy governance，和 [[agent-sandbox]]、[[agentgateway]] 方向高度相关。 |
| `dranet` / `cni-dra-driver` | P2 | DRA 和高性能网络结合，适合后续连接 GPU/RDMA/AI workload。 |

### 存储 / Secret / 数据面挂载

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[secrets-store-csi-driver]] | P0 已完成 | 把外部 secret store 通过 CSI volume 注入 Pod，连接 [[agent-credential-isolation]] 和 [[cloud-native-security]]。 |
| `aws-ebs-csi-driver` | 排除 | 块存储 CSI driver 的云厂商代表。 |
| `aws-efs-csi-driver` | 排除 | 文件存储 CSI driver 的云厂商代表，适合与 EBS 对比。 |
| [[nfs-subdir-external-provisioner]] | P1 已完成 | 轻量 NFS 动态 PV，适合本地/实验集群。 |
| [[sig-storage-local-static-provisioner]] | P1 已完成 | local PV 静态 provisioner，适合理解本地盘和调度绑定。 |
| [[sig-storage-lib-external-provisioner]] | P1 已完成 | CSI/external provisioner 的库和控制器抽象。 |
| `vsphere-csi-driver` / `gcp-*` / `azure*` / `alibaba-cloud-csi-driver` | P2 | 云厂商矩阵补充，按需要选择代表，不必全量展开。 |

### 调度 / 资源 / 队列

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[kueue]] | P0 已完成 | K8s-native Job queueing，是 AI/HPC/batch workload 多租户队列核心。 |
| [[karpenter]] | P0 已完成 | 节点级弹性和容量经济，适合接 LLM serving 的成本与 SLO。 |
| [[scheduler-plugins]] | P0 已完成 | kube-scheduler framework 的 out-of-tree 插件集合，理解调度扩展必读。 |
| [[descheduler]] | P1 已完成 | 通过策略触发重调度，补“调度后优化”维度。 |
| [[kwok]] | P1 已完成 | 无 kubelet 模拟大量节点/集群，适合调度和控制面扩展测试。 |
| [[node-feature-discovery]] | P1 已完成 | 发现节点硬件能力，连接 GPU、NUMA、加速器调度。 |
| [[kube-scheduler-simulator]] | P1 已完成 | 可视化/模拟 scheduler 行为。 |
| [[dra-driver-nvidia-gpu]] | 已有 | 已收录，作为 DRA + GPU 设备分配代表。 |

### 可观测 / 性能 / 诊断

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[metrics-server]] | P0 已完成 | HPA/VPA 的基础资源指标源，K8s autoscaling 入口。 |
| [[prometheus-adapter]] | P0 已完成 | 把 Prometheus 指标暴露为 custom/external metrics API，连接高级 autoscaling。 |
| [[inference-perf]] | P1 已完成 | GenAI inference performance benchmarking tool，可与 `llm-d-benchmark` 对比。 |
| [[headlamp]] | P1 已完成 | K8s UI / debugging / monitoring，可和 [[kubewall]]、`k8m` 对比。 |
| `usage-metrics-collector` | P2 | 容量和使用率指标收集，适合补平台容量管理。 |
| `resource-state-metrics` / `logtools` / `instrumentation-tools` | P2 | 作为 SIG Instrumentation 工具链补充。 |

### 计算 / Runtime / 节点

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[kind]] | P0 已完成 | 本地 Kubernetes in Docker，是 controller/operator 开发和 CI 的事实基线。 |
| [[kubespray]] | P0 已完成 | 生产集群部署自动化，适合理解集群生命周期和裸金属/on-prem。 |
| [[cri-tools]] | P0 已完成 | CRI CLI + validation，理解 kubelet/runtime 边界。 |
| [[security-profiles-operator]] | P1 已完成 | seccomp/AppArmor/SELinux profile operator，连接 runtime security。 |
| [[agent-sandbox]] | 已有 | 已收录，AI Agent runtime 的 sandbox CRD。 |
| [[lws]] | P1 已完成 | LeaderWorkerSet，用一组 Pod 表达 leader/worker 分布式 workload。 |
| [[jobset]] | P1 已完成 | 分布式 ML/HPC workload API，和 `Kueue`、batch serving 强相关。 |

### API / Operator / 控制器开发

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[controller-runtime]] | P0 已完成 | Manager、cache、client、reconcile、webhook、envtest 的现代 controller 抽象层。 |
| [[kubebuilder]] | P0 已完成 | CRD/controller 项目脚手架和代码生成路径。 |
| [[controller-tools]] | P0 已完成 | CRD、RBAC、webhook、object deepcopy 等生成工具链。 |
| [[cluster-api]] | P0 已完成 | 声明式集群生命周期管理，适合接多集群和平台工程。 |
| [[kustomize]] | P1 已完成 | Kubernetes YAML 定制工具链，GitOps/配置管理基础。 |
| [[kro]] | P1 已完成 | Kube Resource Orchestrator，适合与 Crossplane Composition / higher-level API 对比。 |
| `apiserver-builder-alpha` | P2 | aggregated apiserver/controller 旧路线，可作为历史参考。 |

### AI Infra / Agent 交叉

| 项目 | 优先级 | 为什么值得加入 |
|---|---|---|
| [[mcp-lifecycle-operator]] | P1 已完成 | 声明式管理 MCP Servers，和 [[mcp]]、[[agentgateway]]、[[declarative-agent-management]] 直接相关。 |
| [[kube-agentic-networking]] | P1 已完成 | Agent/tool 网络策略治理，适合补 Agent runtime 安全边界。 |
| `ai-conformance` | P2 | AI conformance definition/proposals/tests，待生态更稳定后再摄入。 |
| [[inference-perf]] | P1 已完成 | GenAI inference benchmark，与 [[llm-d]]、[[aibrix]]、[[kserve]] 有直接交集。 |

## 推荐实施顺序

### 第一批：直接补 AI Infra 选型缺口

1. [[llm-d-batch-gateway]]（已完成）
2. [[llm-d-benchmark]]（已完成）
3. [[llm-d-workload-variant-autoscaler]]（已完成）
4. [[llm-d-inference-sim]]（已完成）
5. [[kueue]]（已完成）
6. [[karpenter]]（已完成）
7. [[metrics-server]]（已完成）
8. [[prometheus-adapter]]（已完成）
9. [[inference-perf]]（已完成）
10. [[lws]]（已完成）
11. [[jobset]]（已完成）

这批可以让 [[llm-inference-serving-project-map]] 从“引擎/serving stack”扩展到 batch、benchmark、queueing、autoscaling、distributed workload API。

### 第二批：补 Kubernetes 控制器和平台工程底座

1. [[controller-runtime]]（已完成）
2. [[kubebuilder]]（已完成）
3. [[controller-tools]]（已完成）
4. [[cluster-api]]（已完成）
5. [[kind]]（已完成）
6. [[cri-tools]]（已完成）
7. [[external-dns]]（已完成）
8. [[secrets-store-csi-driver]]（已完成）
9. [[scheduler-plugins]]（已完成）
10. [[node-feature-discovery]]（已完成）

这批可以让 [[k8s-core-controller-map]] 从学习路径升级成更完整的平台工程架构图。

### 第三批：按专项补齐

- 网络专项：[[ingress2gateway]]、[[apiserver-network-proxy]]、[[kube-agentic-networking]] 已完成；`aws-load-balancer-controller` 按用户要求排除；`dranet` 留作 P2。
- 存储专项：[[nfs-subdir-external-provisioner]]、[[sig-storage-local-static-provisioner]]、[[sig-storage-lib-external-provisioner]] 已完成；`aws-ebs-csi-driver`、`aws-efs-csi-driver` 按用户要求排除。
- 安全专项：[[security-profiles-operator]]、[[secrets-store-csi-driver]]、[[kube-agentic-networking]] 已完成。
- 工具/测试专项：[[kustomize]]、[[kwok]]、[[kube-scheduler-simulator]]、[[headlamp]]、[[kro]]、[[mcp-lifecycle-operator]] 已完成；`krew`、`e2e-framework`、`kubetest2` 留作 P2。

## 和现有页面的关系

- 更新 [[llm-inference-serving-project-map]]：加入 batch gateway、benchmark、simulator、autoscaler、Kueue/Karpenter/LWS/JobSet 这条 serving control plane 扩展线。
- 更新 [[k8s-core-controller-map]]：从 controller-runtime/kubebuilder 学习路径，扩展成网络、存储、调度、可观测、计算、API/operator 的维度地图。
- 更新 [[k8s-gpu-device-stack]]：把 `node-feature-discovery`、`Kueue`、`Karpenter`、`JobSet`、`LWS` 放入 GPU/AI workload 的调度前置层。
- 更新 [[cloud-native-security]]：把 `secrets-store-csi-driver`、`security-profiles-operator`、`kube-agentic-networking` 作为 runtime/credential/network policy 三条线。
- 更新 [[model-serving-operator]]：把 [[llm-d]] 外围组件与 K8s SIG 的 queueing/autoscaling/distributed workload API 连起来。
