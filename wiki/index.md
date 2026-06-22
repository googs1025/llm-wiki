---
title: Wiki 索引
date: 2026-05-12
---

# 知识库索引

## 实体 (Entities)

### 云原生
- [[kubernetes]] — 容器编排平台，云原生核心（5 篇源文件）
- [[argocd]] — Kubernetes GitOps 持续交付工具
- [[gateway-api]] — K8s SIG-Network 新一代入口 API（agentgateway 控制面 API 基础）
- [[kubectl-ai]] — kubectl 入口的 Kubernetes AI assistant（CLI + built-in tools + MCP server mode）
- [[k8m]] — 轻量 K8s AI dashboard（Go backend + UI + plugins/MCP）
- [[kubewall]] — single-binary Kubernetes dashboard，AI integration 的 dashboard 形态对照
- [[kueue]] — Kubernetes-native Job Queueing，用 ClusterQueue/LocalQueue/Workload/ResourceFlavor 把 batch、AI/HPC 和多租户资源配额做成 admission control。
- [[karpenter]] — Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。
- [[metrics-server]] — Kubernetes 资源指标管道，把 kubelet summary/metrics 暴露成 `metrics.k8s.io`，供 HPA/VPA/kubectl top 使用。
- [[prometheus-adapter]] — Prometheus 到 Kubernetes custom/external metrics API 的适配层，让 HPA 能基于 QPS、队列长度、业务指标或推理指标扩缩。
- [[lws]] — LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。
- [[jobset]] — JobSet 是 K8s native API for distributed ML training and HPC workloads，用多个 replicated jobs 表达一个整体作业。
- [[controller-runtime]] — controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。
- [[kubebuilder]] — Kubebuilder 是构建 Kubernetes APIs using CRDs 的 SDK，把 API type、marker、controller-runtime manager、webhook、RBAC 和 manifests 生成流程标准化。
- [[controller-tools]] — controller-tools 提供 controller-gen，用 Go marker 生成 CRD、RBAC、webhook、deepcopy 等 Kubernetes API 工程资产。
- [[cluster-api]] — Cluster API 用声明式 API 管理 Kubernetes 集群生命周期，把 Cluster/Machine/MachineDeployment 和 provider infra/bootstrap/control-plane 拆成可组合控制器。
- [[external-dns]] — ExternalDNS 从 Service、Ingress、Gateway 等 Kubernetes 对象动态维护外部 DNS records，是声明式网络控制器代表。
- [[secrets-store-csi-driver]] — Secrets Store CSI Driver 通过 CSI volume 把外部 secret store 注入 Pod，并支持 provider、rotation 和可选 Kubernetes Secret 同步。
- [[kind]] — kind 是 Kubernetes IN Docker，用 Docker/Podman 容器模拟节点并用 kubeadm 拉起本地测试集群。
- [[scheduler-plugins]] — scheduler-plugins 是基于 kube-scheduler framework 的 out-of-tree 插件集合，用于研究和生产化调度扩展。
- [[kubespray]] — Kubespray 用 Ansible inventory/roles 部署生产可用 Kubernetes 集群，覆盖 kubeadm、network plugin、etcd、HA 和云/裸金属差异。
- [[cri-tools]] — CRI Tools 提供 crictl 和 critest，用于操作与验证 kubelet Container Runtime Interface。
- [[ingress2gateway]] — ingress2gateway 把 Kubernetes Ingress resources 转换成 Gateway API resources，帮助从 annotation-heavy Ingress 迁移到 Gateway/HTTPRoute。
- [[apiserver-network-proxy]] — apiserver-network-proxy 通过 konnectivity server/agent 建立 apiserver 到节点网络的反向隧道，适合托管集群或私有节点网络。
- [[kube-agentic-networking]] — kube-agentic-networking 为 Kubernetes 中 agents/tools 提供 agentic networking policies and governance，面向 AI Agent 出口、工具调用和网络权限边界。
- [[nfs-subdir-external-provisioner]] — NFS Subdir External Provisioner 在远端 NFS server 上为 PVC 动态创建子目录，是轻量实验/中小集群常见 storage class。
- [[sig-storage-local-static-provisioner]] — Local Static Provisioner 发现节点本地磁盘/目录并创建 local PersistentVolume，配合调度绑定把数据固定到节点。
- [[sig-storage-lib-external-provisioner]] — sig-storage-lib-external-provisioner 是 Kubernetes dynamic volume provisioner 的库，抽象 PVC watch、PV 创建、reclaim 和 controller lifecycle。
- [[descheduler]] — Descheduler 根据策略驱逐已经运行的 Pods，让 kube-scheduler 有机会重新放置，修复节点漂移、拓扑不均、约束变化等问题。
- [[kwok]] — KWOK 是 Kubernetes WithOut Kubelet，用 fake nodes/pods 模拟大规模集群，适合调度、控制器和 scalability 测试。
- [[node-feature-discovery]] — Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。
- [[kube-scheduler-simulator]] — kube-scheduler-simulator 提供 Kubernetes scheduler 行为模拟和可视化，用于理解 filter/score、调度失败原因和策略效果。
- [[headlamp]] — Headlamp 是可扩展 Kubernetes web UI，面向 dashboard、debugging、monitoring 和插件扩展。
- [[security-profiles-operator]] — Security Profiles Operator 管理 seccomp/AppArmor/SELinux profiles，并可通过 recording 把运行时行为转成可部署 profile。
- [[kustomize]] — Kustomize 用 overlay/patch/transformer 管理 Kubernetes YAML 差异，是 kubectl 原生支持的配置定制工具链。
- [[kro]] — KRO（Kube Resource Orchestrator）用 ResourceGraphDefinition 把多个 Kubernetes resources 组合成更高层 API。
- [[openkruise-kruise]] — OpenKruise 主仓，Kubernetes workload enhancement（CloneSet / Advanced StatefulSet / SidecarSet / WorkloadSpread / ImagePullJob 等）。
- [[openkruise-rollouts]] — OpenKruise 渐进式发布控制面，面向分批发布、灰度/金丝雀、暂停推进和回滚。
- [[kruise-game]] — OpenKruise game server management 专用 workload operator，用 Kubernetes API 表达游戏服务器生命周期。
- [[kruise-state-metrics]] — OpenKruise CRD metrics addon，把增强 workload 状态转成 Prometheus 可观测指标。
- [[kruise-tools]] — OpenKruise libraries/tools 支撑项目，作为主仓工具链和运维辅助材料。
- [[kruise-dashboard]] — OpenKruise workload 运维 UI，面向 CloneSet / Advanced StatefulSet / Advanced DaemonSet 等资源。
- [[controllermesh]] — OpenKruise controller/operator isolation 设计参考，关注控制器权限、运行和故障边界。

### Coding Agent / Agent 生态
- [[claude-code]] — Anthropic 出品的 CLI AI Agent，提供 Lifecycle Hook 插件机制
- [[claude-agent-sdk]] — `@anthropic-ai/claude-agent-sdk`，Agent 编程 SDK
- [[codex]] — OpenAI Codex CLI，Rust terminal coding agent（approval/sandbox/AGENTS.md/patch 工具链）
- [[pi]] — TypeScript agent harness monorepo（统一 LLM provider API + agent core + coding CLI + TUI）
- [[oh-my-pi]] — Pi fork 的强工具 coding-agent 产品（LSP/DAP/hashline/browser/subagents/memory）
- [[multica]] — managed agents platform，把 Claude Code/Codex/Pi 等 CLI 包成 agent teammate
- [[codex-plugin-cc]] — Claude Code 插件形式接入 Codex 的 broker/review gate
- [[open-cowork]] — Electron desktop agent host（Skills/MCP + WSL2/Lima sandbox + GUI/IM control）
- [[claude-tap]] — 本地 AI coding agent trace proxy/viewer
- [[cc-connect]] — 把本地 coding agent 接入飞书/Slack/Telegram 等消息平台的 Go bridge
- [[tokscale]] — Rust 本地 token usage analytics
- [[loongsuite-pilot]] — Alibaba 多 Agent AI coding telemetry collector（hooks/SQLite/session/trace → JSONL/SLS/HTTP/OTLP）
- [[nanobot]] — HKUDS 出品的极简个人 AI Agent 框架（Python，事件驱动 8 态状态机 + 17 渠道 + 7 厂商 + MCP）

### Agent Runtime / Memory
- [[claude-mem]] — 给 Claude Code 装上长期记忆的开源插件
- [[claude-context]] — Zilliz 出品的 MCP 插件，把代码库语义检索接入 AI Agent
- [[mcp]] — Model Context Protocol，AI Agent 工具/资源接入协议
- [[HiClaw]] — 阿里 Higress 系出品的 K8s 原生多 Agent 协作平台
- [[agent-sandbox]] — K8s SIG Apps 孵化的 Sandbox CRD，给 AI Agent 提供安全隔离的有状态容器原语
- [[openkruise-agents]] — OpenKruise 的 K8s 原生 Agent sandbox lifecycle platform（SandboxSet/Claim + E2B API + Envoy route + agent-runtime/CSI/identity）
- [[agentcube]] — Volcano 社区 AI Agent / Code Interpreter 会话编排层（基于 agent-sandbox 的 Router + WorkloadManager + WarmPool）
- [[substrate]] — K8s 上的高密度 agent-like workload substrate（WorkerPool/ActorTemplate + gVisor snapshot/restore）
- [[openshell]] — NVIDIA AI Agent 安全运行时（Gateway + sandbox supervisor + OPA/Z3 policy + inference.local）
- [[nemoclaw]] — OpenShell sandbox 内 always-on Agent 的 host-side CLI 编排层
- [[agentgateway]] — Solo.io / Istio 系出品的 AI-native L7 网关（LLM + MCP + A2A 三协议统一）
- [[agentscope]] — AgentScope 2.0 多 Agent 应用框架（事件流 ReAct + Toolkit/MCP/Skill + Workspace/offload）
- [[agentscope-runtime]] — AgentScope Runtime，生产化 Agent-as-a-Service 运行时（FastAPI AgentApp + Runner + sandbox/deployers）
- [[reme]] — AgentScope 生态 memory toolkit（ReMeLight 文件记忆 + personal/task/tool/working memory pipeline）
- [[oceanbase]] — PowerMem 优先集成的分布式数据库/检索后端
- [[powermem]] — OceanBase 出品的 LLM 持久化记忆中间件（向量+全文+稀疏+图四路混合 + 艾宾浩斯衰减）
- [[mem0]] — 通用 AI memory layer（SDK/server/OpenMemory/MCP/agent plugins）
- [[agent-recall]] — 本地优先的 MCP-native Agent 记忆库（SQLite + scope hierarchy + AI briefing）
- [[memsearch]] — Zilliz 出品的跨平台 AI coding agent 语义记忆系统（Markdown source-of-truth + Milvus hybrid search + progressive recall）
- [[tencentdb-agent-memory]] — 腾讯云出品的 OpenClaw / Hermes Agent 记忆插件（L0→L3 分层长期记忆 + Mermaid context offload + SQLite/TCVDB hybrid search）
- [[agentmemory]] — Rohit Ghumare 出品的本地化跨 Agent 记忆服务（TS + iii-engine + SQLite，三流 RRF + 零 LLM 默认）
- [[mcp-lifecycle-operator]] — MCP Lifecycle Operator 用声明式 API 部署、管理和安全滚动 MCP Servers，把 Agent tool server 生命周期放进 Kubernetes control plane。

### LLM Serving / AI Gateway
- [[dynamo]] — NVIDIA 开源的数据中心级 LLM 推理编排层（Rust + Python + Go，分离式 P/D + KV 感知路由 + 四级 KV 缓存 + SLA 自动扩缩）
- [[vllm]] — UC Berkeley 出品的高吞吐 LLM 推理引擎（PagedAttention 创始者，Dynamo backend 之一）
- [[sglang]] — LMSYS 出品的高性能 LLM 推理引擎（RadixAttention 创始者，Dynamo backend 之一）
- [[aibrix]] — vLLM 生态 K8s GenAI inference infrastructure（gateway/routing/autoscaling/LoRA/KV events）
- [[llm-d]] — CNCF Sandbox 分布式 LLM inference serving stack（Router/EPP + InferencePool + KV/P-D/autoscaling）
- [[llm-d-router]] — llm-d 智能入口层，用 EPP filters/scorers/scrapers 对 InferencePool endpoints 做选择。
- [[llm-d-kv-cache]] — llm-d KV locality index / scorer，把 vLLM/SGLang KV events 转成 cache-hit routing signal。
- [[llm-d-batch-gateway]] — llm-d OpenAI Batch API / 离线推理控制面（API server + PostgreSQL/Redis/Object Store + processor/GC）
- [[llm-d-benchmark]] — llm-d benchmark 实验编排器（scenario/spec 渲染 + K8s lifecycle + harness/result workspace）
- [[llm-d-workload-variant-autoscaler]] — llm-d 多 serving variant 全局 autoscaler（VariantAutoscaling CRD + Prometheus + HPA/KEDA metrics）
- [[llm-d-inference-sim]] — 无 GPU vLLM 行为模拟器（OpenAI/vLLM API + KV events + latency/failure/metrics simulation）
- [[inference-perf]] — GenAI inference performance benchmarking tool，用于对 OpenAI-compatible/serving endpoint 做负载、延迟和吞吐测量。
- [[llm-d-latency-predictor]] — llm-d Latency Predictor 是给 llm-d inference scheduler 的 ML-based latency scoring service，用预测延迟信号增强 endpoint picking。
- [[llm-d-prism]] — llm-d Prism 是分布式推理性能分析 dashboard，把 benchmark 和运行数据做交互式分析，用于理解 P/D、路由和资源配置的效果。
- [[llm-d-pd-utils]] — llm-d P/D Utils 是面向 Prefill/Decode 分离部署的 skills/scripts 工具集，用于 preflight、GPU topology、RDMA/NCCL/network/NIXL 等诊断。
- [[skypilot]] — AI/ML 多云算力控制平面（Task/Dag/Resources + Optimizer + CloudVmRayBackend）
- [[kagent]] — Cloud Native agentic AI 操作层（Go control plane + Python/ADK packages + Kubernetes/DevOps tools）
- [[gateway-api-inference-extension]] — Kubernetes Gateway API 推理扩展（InferencePool + Endpoint Picker）
- [[envoy-ai-gateway]] — Envoy Gateway 生态 GenAI gateway（CRD/controller + extproc + provider translators）
- [[kgateway]] — Gateway API 原生通用 API/AI Gateway（controller + Envoy xDS + plugins/policies）
- [[higress]] — 阿里系 AI Native API Gateway（Envoy/Istio + WASM plugins + model-router/MCP）
- [[plano]] — AI-native Rust proxy/data plane（LLM gateway + prompt gateway + CLI/config/skills）
- [[semantic-router]] — vLLM Semantic Router，system-level intelligent router（Go/Rust bindings + dashboard/operator）
- [[routellm]] — 成本/质量 LLM routing 的算法与评测基线
- [[kserve]] — Kubernetes 标准化 model serving 平台（InferenceService + LLMISvc/LocalModel/controllers/webhooks/router）
- [[gpustack]] — GPU cluster manager / model serving platform（server/worker/scheduler/gateway）
- [[ome]] — Open Model Engine，K8s model serving operator（CRD/controller + runtime selector + accelerator configs）
- [[kubeai]] — Kubernetes AI inference operator（Model CRD + OpenAI-compatible proxy/autoscaler/loader）

### Kubernetes GPU / Device
- [[hami]] — Kubernetes 异构 GPU sharing/vGPU 项目（webhook + scheduler extender + device plugin + 多厂商抽象）
- [[dra-driver-nvidia-gpu]] — NVIDIA Kubernetes DRA driver（ResourceClaim/ResourceSlice + dynamic MIG/VFIO）
- [[gpu-operator]] — NVIDIA GPU 软件栈 Kubernetes Operator（ClusterPolicy/NVIDIADriver + operands lifecycle）
- [[k8s-device-plugin]] — NVIDIA 官方 GPU device plugin（NVML/CUDA discovery + kubelet gRPC + CDI Allocate）

### GPU Learning / CUDA-MUSA
- [[musa-learning-notes]] — MUSA SDK / CUDA→MUSA GPU 编程学习日志（6 周路线 + 38 个 `.mu`/C++/Python 示例）

### Code Intelligence / Repo Wiki
- [[milvus]] — Zilliz 主导的开源向量数据库，支撑代码/记忆的 dense + sparse hybrid retrieval
- [[code-review-graph]] — local-first code intelligence graph（Python package + CLI/MCP + VSCode extension）
- [[gitnexus]] — browser-side repo knowledge graph / Graph RAG / static analysis 项目
- [[deepwiki-open]] — open-source DeepWiki/repo wiki generator（Next.js UI + Python API/tools + LiteLLM）
- [[llm-wiki]] — 当前个人知识库项目（raw/source/entity/concept/analysis 可链接知识图谱）

## 概念 (Concepts)

### Kubernetes 控制面 / 工作负载
- [[gitops]] — 以 Git 为单一事实来源的运维方法论
- [[kubernetes-workload-automation]] — Kubernetes workload 自动化整体概念：workload enhancement、release governance、specialized workload、queueing、capacity、observability 和 controller operation boundary。
- [[model-serving-operator]] — Kubernetes 上声明式管理模型服务的 operator 模式

### Kubernetes 资源 / 设备 / GPU
- [[kubernetes-dra]] — Kubernetes Dynamic Resource Allocation，新一代设备资源声明/调度路径
- [[cdi]] — Container Device Interface，把设备注入从 runtime-specific flags 转成声明式 spec
- [[device-plugin]] — Kubernetes 设备插件模型，GPU/NIC/FPGA 等专用资源向 kubelet 注册的基础机制
- [[gpu-sharing]] — GPU sharing/vGPU/MIG/time-slicing 等多租户复用模式
- [[gpu-programming-learning]] — GPU / CUDA / MUSA kernel 学习路径，从 Runtime/Stream/Graph 到访存、GEMM 与推理性能理解

### LLM Serving 执行层
- [[llm-inference]] — LLM 推理系统从引擎、路由、缓存、网关到 K8s serving 的总体概念
- [[paged-attention]] — KV cache 分块管理基础理念（vLLM 起源，Dynamo KVBM 沿用）
- [[radix-attention]] — KV-aware 路由的算法基础（SGLang 起源，Dynamo router 沿用）
- [[disaggregated-serving]] — Prefill/Decode 分离式服务（Dynamo 默认架构）
- [[kv-cache-offload]] — KV 多级缓存方法论（GPU→CPU→SSD→远端，Dynamo KVBM 实现）

### LLM Serving 流量 / 网关 / 批处理
- [[ai-gateway]] — 面向 LLM/MCP/A2A 的 API gateway / AI gateway 能力面
- [[inference-routing]] — 按 KV cache、语义、成本、模型质量、负载做推理请求路由
- [[batch-inference]] — 大量 LLM 请求异步执行的 job/file/queue/output 控制面模式

### Agent 运行时 / 编排 / 扩展
- [[agent-runtime-substrate]] — 高密度 agent-like workload substrate（worker pool / actor / sandbox / wake routing）
- [[declarative-agent-management]] — 用 K8s CRD 声明式管理 AI Agent 集群（HiClaw 模式）
- [[agent-delegation]] — 把本地 coding agent 委派给插件、消息平台或托管平台的任务分发模式
- [[ai-agent-plugin-patterns]] — AI Agent 外挂的 9 条设计原则（迁移检查表）

### Agent Memory / Context 管理
- [[agent-memory]] — Agent 长期记忆领域综述
- [[event-driven-memory-pipeline]] — 事件采集 → AI 压缩 → 双索引 → 反向注入闭环
- [[three-tier-search-protocol]] — 三层搜索协议（防上下文爆炸）
- [[ai-as-compressor]] — AI 作为压缩器的设计哲学
- [[ebbinghaus-forgetting-curve]] — `R = e^(-t/S)` 数学模型驱动 working/short/long 三层记忆衰减与晋升（PowerMem 核心）

### Code Intelligence / Knowledge Graph
- [[code-semantic-search]] — 代码语义检索方法论
- [[hybrid-search-rrf]] — Dense + Sparse + RRF 重排混合检索
- [[merkle-dag-fingerprint]] — 内容指纹做增量同步
- [[code-graph]] — 从仓库构建符号/依赖/调用图并服务 review、Graph RAG、影响面分析
- [[repo-wiki-generation]] — 自动把代码仓库生成可问答 wiki 的 pipeline

### Observability / Security / Governance
- [[ai-ops]] — AI/LLM 增强运维（告警分诊、根因分析）
- [[coding-agent-observability]] — coding agent 请求、工具、session、trace、usage、成本和运行状态的可观测性
- [[token-usage-observability]] — 跨模型、client、workspace 汇总 token、cache、reasoning 和成本
- [[cloud-native-security]] — 云原生安全实践与趋势
- [[agent-credential-isolation]] — Agent 凭据零暴露：网关托管真凭据，Agent 只持 consumer key

## 源文件摘要 (Sources)

- [[src-k8s-v1.36-sneak-peek]] — K8s v1.36 新特性预览（弃用 externalIPs、SELinux GA）
- [[src-holmesgpt-k8s-alerts]] — HolmesGPT 自动诊断 K8s 告警（Runbook > 模型选择）
- [[src-k3s-gitops-k0rdent]] — K3s + k0rdent GitOps 部署 On-Prem 集群
- [[src-ai-vulnerability-discovery]] — AI 驱动的漏洞发现变革与应对策略
- [[src-argocd-overview]] — Argo CD 核心功能与架构概览
- [[src-claude-mem-architecture]] — claude-mem 架构与设计思路（v13.1.0，跨会话记忆插件）
- [[src-claude-context-architecture]] — Claude Context 架构（v0.1.13，MCP 代码语义检索）
- [[src-hiclaw-architecture]] — HiClaw 架构（v1.1.0，K8s 原生多 Agent 协作平台，Matrix IM + Higress 网关凭据托管）
- [[src-agent-sandbox-architecture]] — agent-sandbox 架构（v0.4.5，K8s SIG Apps 孵化的 Sandbox CRD，AI Agent 安全隔离运行时原语）
- [[src-openkruise-agents-architecture]] — OpenKruise Agents 架构（HEAD `0e58df8`，K8s 原生 Agent sandbox lifecycle platform：SandboxSet/Claim warm pool + E2B-compatible API + Envoy route + agent-runtime/CSI/identity）
- [[src-openkruise-projects-current-state]] — OpenKruise 组织项目当前状态核验（kruise / rollouts / kruise-game / agents / metrics / dashboard / controllermesh）
- [[src-agentcube-architecture]] — AgentCube 架构（HEAD `208da32`，Volcano 社区 AI Agent / Code Interpreter 会话编排层，基于 agent-sandbox 做 Router + WorkloadManager + WarmPool）
- [[src-agentgateway-architecture]] — agentgateway 架构（v1.2.0-alpha.2，Istio 系骨架 + Rust 数据面，LLM/MCP/A2A 三协议 AI Gateway）
- [[src-powermem-architecture]] — PowerMem 架构（v1.1.1，OceanBase 持久化记忆中间件，向量+全文+稀疏+图四路混合 + 艾宾浩斯衰减）
- [[src-dynamo-architecture]] — NVIDIA Dynamo 架构（v1.2.0，数据中心级 LLM 推理编排层，分离式 P/D + KV 感知路由 + 四级 KV 缓存 KVBM + SLA 自动扩缩）
- [[src-nanobot-architecture]] — nanobot 架构（v0.2.0，HKUDS 个人 AI Agent 框架，8 态状态机 + 17 渠道 + Fallback Provider + Mid-turn 注入）
- [[src-agentmemory-architecture]] — agentmemory 架构（v0.9.21，本地化跨 Agent 记忆服务，iii-engine 总线 + BM25+Vector+Graph 三流 RRF + 12 hooks + 53 MCP tools，零 LLM 压缩默认）
- [[src-agent-recall-architecture]] — agent-recall 架构（HEAD `dcf21b5`，本地优先 MCP-native Agent 记忆库，SQLite + scope hierarchy + bitemporal slots + AI briefing cache）
- [[src-memsearch-architecture]] — memsearch 架构（v0.4.6 / HEAD `018a85f`，跨平台 AI coding agent 语义记忆，Markdown source-of-truth + Milvus dense/BM25/RRF + search→expand→transcript）
- [[src-tencentdb-agent-memory-architecture]] — TencentDB-Agent-Memory 架构（v0.3.6 / HEAD `f92b102`，OpenClaw/Hermes 记忆插件，L0→L3 分层语义金字塔 + context offload + SQLite/TCVDB hybrid search）
- [[src-skypilot-architecture]] — SkyPilot 架构（HEAD `55b9185`，AI/ML 多云算力控制平面，YAML/SDK → API server → Optimizer → CloudVmRayBackend → provider/控制器）
- [[src-ai-agent-frameworks-stars]] — AI Agent Frameworks Star 项目清单（109 个项目，个人 Agent / coding agent → Agent framework → MCP/gateway → Skills/memory → cloud-native runtime）
- [[src-agentscope-architecture]] — AgentScope 架构（HEAD `e129177`，Python 多 Agent 应用框架，事件流 ReAct loop + Toolkit/MCP/Skill + Workspace/offload + FastAPI service）
- [[src-k8s-gpu-device-plugins-stars]] — K8s GPU & Device Plugins Star 项目清单（36 个项目，device plugin/GPU Operator → vGPU/GPU sharing → DRA/CDI → GPU observability/diagnostics）
- [[src-k8s-core-controllers-stars]] — K8s Core & Controllers Star 项目清单（359 个项目，K8s 主线/client-go/controller-runtime/kubebuilder → 调度/多集群/网络/存储/可观测）
- [[src-github-stars-backlog-current-state]] — GitHub Stars P0-P2 当前状态核验（39 个项目，runtime/memory/coding agent/serving/gateway/AI Ops/code graph/GPU）
- [[src-substrate-architecture]] — Agent Substrate 架构（HEAD `a3f4474`，K8s 上的高密度 agent-like workload substrate：WorkerPool/ActorTemplate + Redis/ValKey actor 状态 + Envoy 唤醒路由 + atelet/ateom gVisor snapshot）
- [[src-agentscope-runtime-architecture]] — AgentScope Runtime 架构（HEAD `22072fd`，生产化 Agent-as-a-Service：FastAPI AgentApp + Runner + protocol adapters + sandbox manager + K8s/serverless deployers；仓库 README 已标注能力并入 AgentScope 2.0，后续更多是迁移参考）
- [[src-mem0-architecture]] — mem0 架构（HEAD `2c796d1`，通用 AI memory layer：Python SDK + TS SDK + self-host server/OpenMemory + MCP/CLI/agent plugins；核心检索走 ADD-only fact extraction、entity linking、BM25/semantic/entity fusion）
- [[src-reme-architecture]] — ReMe 架构（HEAD `f458566`，AgentScope 生态 memory kit：ReMeLight 文件记忆 + vector/service pipeline + personal/task/tool/working memory summarization/retrieval）
- [[src-codex-architecture]] — OpenAI Codex CLI 架构（HEAD `bf667c7`，Rust terminal coding agent：CLI/TUI/app-server/MCP/core crates + approval/sandbox/AGENTS.md/context/patch 工具链）
- [[src-pi-architecture]] — Pi Agent Harness 架构（HEAD `3f44d3e`，TypeScript monorepo：unified LLM provider API + agent core/tool loop + coding-agent CLI + TUI；默认不提供强权限隔离，建议外部 sandbox）
- [[src-oh-my-pi-architecture]] — oh-my-pi 架构（HEAD `12290e0`，Pi fork 的重工具 coding-agent harness：32 tools、LSP/DAP、hashline edit、browser/web_search、subagents、memory、native Rust core）
- [[src-multica-architecture]] — Multica 架构（HEAD `99afb82`，managed agents platform：Next.js board + Go/Chi backend + PostgreSQL/pgvector + local daemon runtimes，把 Claude Code/Codex/Pi 等 CLI 包成可分配任务的 teammate）
- [[src-open-cowork-architecture]] — Open Cowork 架构（HEAD `8e60460`，Electron desktop agent host：Claude/OpenAI-compatible chat + Skills/MCP + WSL2/Lima sandbox + GUI automation + Feishu/Slack remote control）
- [[src-aibrix-architecture]] — AIBrix 架构（HEAD `ac2c161`，vLLM 生态 K8s GenAI inference infrastructure：gateway/routing、PodAutoscaler、ModelAdapter、KV cache/event sync、LoRA、distributed inference、GPU failure detection）
- [[src-llm-d-architecture]] — llm-d 架构（HEAD `2734681`，CNCF Sandbox 分布式 LLM inference serving stack：Router/EPP + InferencePool + model server + KV cache management + P/D disaggregation + autoscaling/batch guides）
- [[src-llm-d-router-architecture]] — llm-d Router 架构（HEAD `a0173a7`，LLM-aware inference entry point：Envoy/ext-proc + Endpoint Picker(EPP) + filters/scorers/scrapers + InferenceObjective/ModelRewrite + P/D sidecar）
- [[src-llm-d-kv-cache-architecture]] — llm-d KV Cache 架构（HEAD `26e2b6f`，KV-cache aware routing library/service：KVEvents ingestion + kvblock index + tokenizer service + scorer/indexer + Valkey/Redis/in-memory backends + vLLM connectors）
- [[src-llm-d-batch-gateway-architecture]] — llm-d Batch Gateway 架构（HEAD `66fae7e`，OpenAI Batch API / 离线推理：API server + PostgreSQL/Redis/Object Store + processor/GC + 下游 llm-d Router）
- [[src-llm-d-benchmark-architecture]] — llm-d Benchmark 架构（HEAD `bd8dc5e`，benchmark 实验编排：scenario/spec 渲染、K8s lifecycle、harness 适配、workspace/result collection）
- [[src-llm-d-workload-variant-autoscaler-architecture]] — llm-d WVA 架构（HEAD `526ce85`，VariantAutoscaling CRD + Prometheus/GPU inventory/capacity model + HPA/KEDA 指标驱动）
- [[src-llm-d-inference-sim-architecture]] — llm-d Inference Sim 架构（HEAD `6fb66f3`，无 GPU vLLM 行为模拟：OpenAI/vLLM API、KV cache events、latency/failure/metrics）
- [[src-kueue-architecture]] — Kueue 架构（P0，调度 / 队列：Kubernetes-native Job Queueing，用 ClusterQueue/LocalQueue/Workload/ResourceFlavor 把 batch、AI/HPC 和多租户资源配额做成 admission control。）
- [[src-karpenter-architecture]] — Karpenter 架构（P0，节点弹性 / 成本：Kubernetes node autoscaler，用 NodePool/NodeClaim/CloudProvider 把 pending pods 转换成最合适的节点容量，并做 consolidation 降本。）
- [[src-metrics-server-architecture]] — metrics-server 架构（P0，可观测 / autoscaling：Kubernetes 资源指标管道，把 kubelet summary/metrics 暴露成 `metrics.k8s.io`，供 HPA/VPA/kubectl top 使用。）
- [[src-prometheus-adapter-architecture]] — prometheus-adapter 架构（P0，custom/external metrics：Prometheus 到 Kubernetes custom/external metrics API 的适配层，让 HPA 能基于 QPS、队列长度、业务指标或推理指标扩缩。）
- [[src-inference-perf-architecture]] — inference-perf 架构（P1，GenAI benchmark：GenAI inference performance benchmarking tool，用于对 OpenAI-compatible/serving endpoint 做负载、延迟和吞吐测量。）
- [[src-lws-architecture]] — LeaderWorkerSet 架构（P1，分布式 workload API：LeaderWorkerSet 用一组 leader/worker Pods 表达一个复制单元，适合 LLM inference、分布式 serving 和需要稳定 group 语义的 workload。）
- [[src-jobset-architecture]] — JobSet 架构（P1，分布式 workload API：JobSet 是 K8s native API for distributed ML training and HPC workloads，用多个 replicated jobs 表达一个整体作业。）
- [[src-controller-runtime-architecture]] — controller-runtime 架构（P0，Operator SDK：controller-runtime 是现代 Kubernetes controller 的通用库，封装 Manager、cache、client、reconcile、webhook、envtest 等生产控制器骨架。）
- [[src-kubebuilder-architecture]] — Kubebuilder 架构（P0，CRD / controller 脚手架：Kubebuilder 是构建 Kubernetes APIs using CRDs 的 SDK，把 API type、marker、controller-runtime manager、webhook、RBAC 和 manifests 生成流程标准化。）
- [[src-controller-tools-architecture]] — controller-tools 架构（P0，API 生成工具：controller-tools 提供 controller-gen，用 Go marker 生成 CRD、RBAC、webhook、deepcopy 等 Kubernetes API 工程资产。）
- [[src-cluster-api-architecture]] — Cluster API 架构（P0，集群生命周期：Cluster API 用声明式 API 管理 Kubernetes 集群生命周期，把 Cluster/Machine/MachineDeployment 和 provider infra/bootstrap/control-plane 拆成可组合控制器。）
- [[src-external-dns-architecture]] — external-dns 架构（P0，网络 / DNS：ExternalDNS 从 Service、Ingress、Gateway 等 Kubernetes 对象动态维护外部 DNS records，是声明式网络控制器代表。）
- [[src-secrets-store-csi-driver-architecture]] — Secrets Store CSI Driver 架构（P0，存储 / 凭据：Secrets Store CSI Driver 通过 CSI volume 把外部 secret store 注入 Pod，并支持 provider、rotation 和可选 Kubernetes Secret 同步。）
- [[src-kind-architecture]] — kind 架构（P0，计算 / 测试集群：kind 是 Kubernetes IN Docker，用 Docker/Podman 容器模拟节点并用 kubeadm 拉起本地测试集群。）
- [[src-scheduler-plugins-architecture]] — scheduler-plugins 架构（P0，调度 / 资源：scheduler-plugins 是基于 kube-scheduler framework 的 out-of-tree 插件集合，用于研究和生产化调度扩展。）
- [[src-kubespray-architecture]] — Kubespray 架构（P0，计算 / 集群部署：Kubespray 用 Ansible inventory/roles 部署生产可用 Kubernetes 集群，覆盖 kubeadm、network plugin、etcd、HA 和云/裸金属差异。）
- [[src-cri-tools-architecture]] — CRI Tools 架构（P0，计算 / Runtime：CRI Tools 提供 crictl 和 critest，用于操作与验证 kubelet Container Runtime Interface。）
- [[src-llm-d-latency-predictor-architecture]] — llm-d Latency Predictor 架构（P1，latency predictor：llm-d Latency Predictor 是给 llm-d inference scheduler 的 ML-based latency scoring service，用预测延迟信号增强 endpoint picking。）
- [[src-llm-d-prism-architecture]] — llm-d Prism 架构（P1，performance analysis：llm-d Prism 是分布式推理性能分析 dashboard，把 benchmark 和运行数据做交互式分析，用于理解 P/D、路由和资源配置的效果。）
- [[src-llm-d-pd-utils-architecture]] — llm-d P/D Utils 架构（P1，P/D diagnostics：llm-d P/D Utils 是面向 Prefill/Decode 分离部署的 skills/scripts 工具集，用于 preflight、GPU topology、RDMA/NCCL/network/NIXL 等诊断。）
- [[src-ingress2gateway-architecture]] — ingress2gateway 架构（P1，Ingress -> Gateway API migration：ingress2gateway 把 Kubernetes Ingress resources 转换成 Gateway API resources，帮助从 annotation-heavy Ingress 迁移到 Gateway/HTTPRoute。）
- [[src-apiserver-network-proxy-architecture]] — apiserver-network-proxy 架构（P1，control plane network proxy：apiserver-network-proxy 通过 konnectivity server/agent 建立 apiserver 到节点网络的反向隧道，适合托管集群或私有节点网络。）
- [[src-kube-agentic-networking-architecture]] — kube-agentic-networking 架构（P1，Agent networking governance：kube-agentic-networking 为 Kubernetes 中 agents/tools 提供 agentic networking policies and governance，面向 AI Agent 出口、工具调用和网络权限边界。）
- [[src-nfs-subdir-external-provisioner-architecture]] — NFS Subdir External Provisioner 架构（P1，NFS dynamic provisioning：NFS Subdir External Provisioner 在远端 NFS server 上为 PVC 动态创建子目录，是轻量实验/中小集群常见 storage class。）
- [[src-sig-storage-local-static-provisioner-architecture]] — Local Static Provisioner 架构（P1，Local PV static provisioning：Local Static Provisioner 发现节点本地磁盘/目录并创建 local PersistentVolume，配合调度绑定把数据固定到节点。）
- [[src-sig-storage-lib-external-provisioner-architecture]] — sig-storage-lib-external-provisioner 架构（P1，external provisioner library：sig-storage-lib-external-provisioner 是 Kubernetes dynamic volume provisioner 的库，抽象 PVC watch、PV 创建、reclaim 和 controller lifecycle。）
- [[src-descheduler-architecture]] — Descheduler 架构（P1，调度后优化：Descheduler 根据策略驱逐已经运行的 Pods，让 kube-scheduler 有机会重新放置，修复节点漂移、拓扑不均、约束变化等问题。）
- [[src-kwok-architecture]] — KWOK 架构（P1，大规模集群模拟：KWOK 是 Kubernetes WithOut Kubelet，用 fake nodes/pods 模拟大规模集群，适合调度、控制器和 scalability 测试。）
- [[src-node-feature-discovery-architecture]] — Node Feature Discovery 架构（P1，节点能力发现：Node Feature Discovery 发现 CPU、内核、PCI、NUMA、GPU/加速器等硬件/系统能力，并写成 node labels/features 供调度使用。）
- [[src-kube-scheduler-simulator-architecture]] — kube-scheduler-simulator 架构（P1，scheduler 可视化模拟：kube-scheduler-simulator 提供 Kubernetes scheduler 行为模拟和可视化，用于理解 filter/score、调度失败原因和策略效果。）
- [[src-headlamp-architecture]] — Headlamp 架构（P1，Kubernetes UI：Headlamp 是可扩展 Kubernetes web UI，面向 dashboard、debugging、monitoring 和插件扩展。）
- [[src-security-profiles-operator-architecture]] — Security Profiles Operator 架构（P1，Runtime security：Security Profiles Operator 管理 seccomp/AppArmor/SELinux profiles，并可通过 recording 把运行时行为转成可部署 profile。）
- [[src-kustomize-architecture]] — Kustomize 架构（P1，配置管理：Kustomize 用 overlay/patch/transformer 管理 Kubernetes YAML 差异，是 kubectl 原生支持的配置定制工具链。）
- [[src-kro-architecture]] — KRO 架构（P1，higher-level API orchestration：KRO（Kube Resource Orchestrator）用 ResourceGraphDefinition 把多个 Kubernetes resources 组合成更高层 API。）
- [[src-mcp-lifecycle-operator-architecture]] — MCP Lifecycle Operator 架构（P1，MCP lifecycle：MCP Lifecycle Operator 用声明式 API 部署、管理和安全滚动 MCP Servers，把 Agent tool server 生命周期放进 Kubernetes control plane。）
- [[src-kagent-architecture]] — kagent 架构（HEAD `feb8cf9`，Cloud Native agentic AI：Go control plane + Python/ADK packages + Helm/UI/tools，把 Kubernetes/DevOps 工作流包装成 agentic 操作层）
- [[src-kubectl-ai-architecture]] — kubectl-ai 架构（HEAD `08cf256`，kubectl 入口的 Kubernetes AI assistant：Go CLI + agent/session/journal + built-in bash/kubectl tools + MCP server mode）
- [[src-k8m-architecture]] — k8m 架构（HEAD `718e894`，Mini Kubernetes AI Dashboard：Go backend + UI + plugins/MCP + 多集群/权限/异常检测入口）
- [[src-kubewall-architecture]] — kubewall 架构（HEAD `fd575ff`，single-binary Kubernetes dashboard：Go backend + client + charts，把 AI integration 作为 dashboard 增强而非主 agent loop）
- [[src-gateway-api-inference-extension-architecture]] — Gateway API Inference Extension 架构（HEAD `974d27c`，Kubernetes Gateway API 推理扩展：InferencePool API + EPP/LWEPP + conformance/benchmarking，标准化 inference endpoint picking）
- [[src-ai-gateway-architecture]] — Envoy AI Gateway 架构（HEAD `9a4b02c`，Envoy Gateway 上的 GenAI gateway：CRD/controller + extproc + provider translators + rate limit/auth/redaction/MCP proxy）
- [[src-kgateway-architecture]] — kgateway 架构（HEAD `1560573`，cloud-native API/AI Gateway：Gateway API controller + Envoy xDS + plugins/policies/SDS，AI Gateway 是其能力分支）
- [[src-higress-architecture]] — Higress 架构（HEAD `2897c1e`，AI Native API Gateway：Envoy/Istio/control plane + WASM plugins + model-router/MCP/credential governance，HiClaw 背景依赖）
- [[src-semantic-router-architecture]] — vLLM Semantic Router 架构（HEAD `9893c2c`，system-level intelligent router：Go/Rust bindings + semantic decision/config + dashboard/operator/deploy recipes；仓库 241MB，分析聚焦源码核心）
- [[src-routellm-architecture]] — RouteLLM 架构（HEAD `0b64fda`，成本/质量 LLM routing 基线：Python routers/evals/benchmarks；最近活跃停在 2024-08，适合作算法参考）
- [[src-plano-architecture]] — Plano 架构（HEAD `2e38f7f`，AI-native proxy/data plane：Rust crates + CLI + config + skills，面向 model routing、guardrails、agent orchestration）
- [[src-gpustack-architecture]] — GPUStack 架构（HEAD `05d56cd`，GPU cluster manager/model serving platform：Python server/worker/scheduler/gateway + vLLM/SGLang 编排 + observability/docs）
- [[src-ome-architecture]] — OME 架构（HEAD `e91ed23`，Open Model Engine：K8s operator for model serving，CRD/controller + model-agent/ome-agent + runtime selector + accelerator configs）
- [[src-kserve-architecture]] — KServe 架构（HEAD `ccf1d3d`，Kubernetes 标准化 model serving 平台：InferenceService + LLMISvc/LocalModel + controllers/webhooks/router；仓库 360MB，分析聚焦 control plane/API）
- [[src-kubeai-architecture]] — KubeAI 架构（HEAD `1fe298d`，AI inference operator：Model CRD + OpenAI server/model proxy + model autoscaler + loader，覆盖 LLM/VLM/embedding/speech）
- [[src-code-review-graph-architecture]] — code-review-graph 架构（HEAD `b72413c`，local-first code intelligence graph：Python package + CLI/MCP tools + VSCode extension + skills，面向 review/change understanding）
- [[src-gitnexus-architecture]] — GitNexus 架构（HEAD `14397dd`，browser-side repo knowledge graph + Graph RAG + taint analysis：web app/shared/core/plugins，偏交互式代码理解）
- [[src-deepwiki-open-architecture]] — deepwiki-open 架构（HEAD `16f35a0`，open-source DeepWiki/repo wiki generator：Next.js UI + Python API/tools + LiteLLM multi-provider routing，把 repo 自动生成可问答 wiki）
- [[src-codex-plugin-cc-architecture]] — Codex Plugin for Claude Code 架构（HEAD `807e03a`，Claude Code 插件形式接入 Codex：slash command + app-server broker + job state + review gate）
- [[src-claude-tap-architecture]] — claude-tap 架构（HEAD `a11231b`，本地 AI coding agent trace proxy/viewer：reverse/forward proxy + SQLite trace + live/export viewer）
- [[src-cc-connect-architecture]] — cc-connect 架构（HEAD `c53f545`，把 Claude Code/Codex/Gemini/Pi 等本地 coding agent 接到飞书/Slack/Telegram 等消息平台的 Go bridge）
- [[src-tokscale-architecture]] — Tokscale 架构（HEAD `aebe4ea`，Rust 本地 token usage analytics：session scanner + parser + rayon aggregation + multi-source pricing + TUI/JSON）
- [[src-loongsuite-pilot-architecture]] — LoongSuite Pilot 架构（HEAD `e936fb0`，Alibaba 多 Agent AI coding telemetry collector：hooks/SQLite/session/trace → JSONL/SLS/HTTP/OTLP）
- [[src-hami-architecture]] — HAMi 架构（HEAD `5dca58e`，Kubernetes 异构 GPU sharing/vGPU：webhook + scheduler extender + device plugin + 多厂商 device abstraction）
- [[src-dra-driver-nvidia-gpu-architecture]] — DRA Driver for NVIDIA GPUs 架构（HEAD `749a743`，Kubernetes DRA NVIDIA driver：ResourceClaim/ResourceSlice + NodePrepare + dynamic MIG/VFIO + ComputeDomain）
- [[src-gpu-operator-architecture]] — NVIDIA GPU Operator 架构（HEAD `0219120`，GPU 软件栈 Kubernetes Operator：ClusterPolicy/NVIDIADriver + state renderer + operands lifecycle）
- [[src-k8s-device-plugin-architecture]] — NVIDIA k8s-device-plugin 架构（HEAD `8688949`，官方 GPU device plugin：NVML/CUDA discovery + kubelet gRPC + env/volume/CDI Allocate）
- [[src-nemoclaw-architecture]] — NVIDIA NemoClaw 架构（HEAD `3c0340a`，OpenShell sandbox 内 always-on AI Agent 的 CLI 控制面，onboard FSM + gateway 托管凭证 + inference.local 路由 + policy/shields）
- [[src-openshell-architecture]] — NVIDIA OpenShell 架构（HEAD `97986d9`，AI Agent 安全运行时，Gateway 控制面 + sandbox Supervisor enforcement + OPA/Z3 policy + provider credential/inference.local 路由）
- [[src-ai-infra-learning-cn-stars]] — AI Infra Learning 中文 Star 项目清单（32 个项目，AI 系统/Infra → CUDA/GPU kernel → LLM 推理/部署 → Agent/Skills → 面试材料）
- [[src-musa-learning-notes-architecture]] — MUSA Learning Notes 架构（HEAD `b4042c3`，GPU / CUDA→MUSA 学习日志：6 周路线 + Runtime/Stream/Graph/访存/GEMM/调试多卡示例）

## 分析 (Analysis)

- [[agent-memory-project-map]] — Agent Memory 项目地图（claude-mem / agent-recall / agentmemory / powermem / memsearch / TencentDB-Agent-Memory 横向对比与选型）
- [[agent-runtime-sandbox-project-map]] — Agent Runtime / Sandbox 项目地图（agent-sandbox / OpenKruise Agents / AgentCube / OpenShell / NemoClaw / HiClaw / AgentScope / agentgateway 分层对比）
- [[llm-inference-serving-project-map]] — LLM Inference / Serving 项目地图（vLLM / SGLang / Dynamo / SkyPilot / K8s GPU stack 横向拆解）
- [[ai-agent-frameworks-map]] — AI Agent Frameworks 项目地图（coding agent / framework / MCP / skills / memory / runtime 分层）
- [[coding-agent-selection-map]] — Coding Agent / Personal Agent 选型地图（Claude Code / OpenCode / OpenClaude / NemoClaw / nanobot）
- [[agent-memory-selection-matrix]] — Agent Memory 细分选型矩阵（claude-mem / agent-recall / agentmemory / PowerMem / memsearch / TencentDB-Agent-Memory）
- [[agent-runtime-sandbox-selection-map]] — Agent Runtime / Sandbox 细分选型地图（agent-sandbox / OpenKruise Agents / AgentCube / OpenShell / NemoClaw / HiClaw / AgentScope / agentgateway）
- [[llm-serving-engine-selection-map]] — LLM Serving / 推理引擎选型地图（vLLM / SGLang / Dynamo / SkyPilot / K8s GPU stack）
- [[mcp-gateway-tooling-map]] — MCP Server / Tool Gateway 对比地图（FastMCP / GitHub MCP / Playwright MCP / kubectl MCP / agentgateway / Plano）
- [[agent-skills-plugin-system-map]] — Agent Skills / Plugin System 对比地图（plugin / skill / MCP tool 三种扩展形态）
- [[code-semantic-search-rag-map]] — Code Semantic Search / Code RAG 对比地图（Claude Context / memsearch / Milvus / tree-sitter）
- [[agent-framework-programming-model-map]] — Agent Framework 编程模型对比地图（LangGraph / LangChain / Dify / AgentScope / Eino / ADK / AutoGen / CrewAI）
- [[github-stars-ingest-candidates]] — GitHub Stars 下一批摄入候选清单（P0-P2：agent-substrate / AgentScope Runtime / mem0 / Codex / llm-d / AI Gateway / K8s GPU 等）
- [[github-stars-backlog-implementation-map]] — GitHub Stars P0-P2 实现地图（把 backlog 项目落到 runtime/memory/coding agent/serving/gateway/AI Ops/code graph/GPU 正式选型结构）
- [[ai-infra-learning-cn-map]] — AI Infra 中文学习项目地图（中文 AI Infra / LLM / CUDA / Agent 学习路线）
- [[k8s-gpu-device-stack]] — Kubernetes GPU / Device Stack 项目地图（device plugin / GPU Operator / DRA / CDI / sharing / observability）
- [[k8s-core-controller-map]] — Kubernetes Core / Controller 项目地图（client-go / controller-runtime / kubebuilder / CRD / webhook / reconcile）
- [[llm-d-kubernetes-sigs-candidate-map]] — llm-d / Kubernetes SIGs 候选项目地图（按网络、存储、调度、可观测、计算、API/operator、AI Infra 交叉维度拆分 P0-P2）
- [[openkruise-project-candidate-map]] — OpenKruise 项目候选地图（kruise / rollouts / kruise-game / agents / observability / controller isolation）

---

## 待建页面

以下实体/概念在文章中被提及但尚未建页：

### 云原生
- client-go — Kubernetes controller/operator 底层 client/informer/workqueue 基座（controller-runtime/kubebuilder/controller-tools 已建页）
- client-go / sample-controller — Kubernetes controller 底层学习材料（其余 P0/P1 controller/API 项目已建页）
- OpenKruise P2 支撑材料：charts / API definition repos / openkruise.io docs，可随主项目摄入时引用。
- aws-load-balancer-controller — 用户明确暂不需要；网络 P0/P1 其余候选已建页
- aws-ebs-csi-driver / aws-efs-csi-driver — 用户明确暂不需要；存储 P0/P1 其余候选已建页
- 调度/队列/弹性 P0/P1 候选已建页：[[kueue]] / [[karpenter]] / [[scheduler-plugins]] / [[descheduler]] / [[kwok]] / [[node-feature-discovery]]
- usage-metrics-collector — P2 容量/使用率指标候选；metrics-server/prometheus-adapter/inference-perf 已建页
- 计算/runtime/分布式 workload P0/P1 候选已建页：[[kind]] / [[kubespray]] / [[cri-tools]] / [[security-profiles-operator]] / [[lws]] / [[jobset]]
- opentelemetry — 可观测性框架
- ebpf — 内核级可编程技术
- ingress-nginx — 已退役的 K8s 入口控制器
- service-mesh — 服务网格（Istio/Cilium/Envoy）
- containerd — 容器运行时
- prometheus — 监控系统
- serverless-wasm — Serverless 与 WebAssembly
- platform-engineering — 平台工程
- kueue — K8s 多租户作业队列（agent-sandbox examples 用 v1beta2）
- cilium — eBPF CNI，扩展 NetworkPolicy 到 L7（agent-sandbox examples 用作 Unmanaged 模式后端）
- envoy — Istio / agentgateway 数据面对照（agentgateway 实现 Envoy xDS 协议但数据面是 Rust 自家实现）
- a2a-protocol — Google Agent-to-Agent 协议（agentgateway A2A gateway 代理对象）
- rego / opa — OPA 策略语言，对照 CEL 设计

### AI Agent / LLM Infra
- openclaw / opencode / openclaude / hermes-agent — 个人 Agent、coding agent 与 Agent OS 代表项目
- agent-skills — Agent 能力包模式（Markdown + scripts + workflow，可迁移到 Claude Code / Codex / OpenCode）
- langchain / langgraph / dify / eino / adk — Agent framework 与 workflow runtime 代表项目
- fastmcp / playwright-mcp / github-mcp-server — MCP server、browser automation 与 GitHub tools 代表项目
- bullmq — Node.js 任务队列（claude-mem 后台压缩调度）
- chroma — 开源向量数据库（claude-mem 使用）
- fts5 — SQLite 全文索引扩展
- outbox-pattern — 事务性消息发布模式
- tree-sitter — 多语言 AST 解析器（claude-context AST splitter 基础）
- matrix-protocol — 分布式 IM 协议（HiClaw 协作平面）
- k8s-operator — Kubernetes Operator 模式（HiClaw 控制平面骨架）
- kine — SQLite-backed etcd 协议层（HiClaw 嵌入式模式）
- autogen / langgraph / crewai — 多 Agent 框架同类对比项
- ai-infra-learning-cn — 中文 AI Infra 学习项目：AISystem / AIInfra / InfraTech / LeetCUDA / Awesome-LLM-Inference / self-llm / hello-agents / nanoclaw 等（详见 [[ai-infra-learning-cn-map]]）
- llm-d-inference-payload-processor — llm-d P2 payload processor 后续候选；llm-d P1 latency/prism/pd-utils 已建页
- ai-conformance — Kubernetes SIGs AI conformance P2 候选；[[mcp-lifecycle-operator]] / [[kube-agentic-networking]] 已建页
