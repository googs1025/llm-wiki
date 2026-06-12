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

### AI Agent / LLM Infra
- [[claude-code]] — Anthropic 出品的 CLI AI Agent，提供 Lifecycle Hook 插件机制
- [[claude-mem]] — 给 Claude Code 装上长期记忆的开源插件
- [[claude-agent-sdk]] — `@anthropic-ai/claude-agent-sdk`，Agent 编程 SDK
- [[claude-context]] — Zilliz 出品的 MCP 插件，把代码库语义检索接入 AI Agent
- [[milvus]] — Zilliz 主导的开源向量数据库，支撑代码/记忆的 dense + sparse hybrid retrieval
- [[mcp]] — Model Context Protocol，AI Agent 工具/资源接入协议
- [[HiClaw]] — 阿里 Higress 系出品的 K8s 原生多 Agent 协作平台
- [[agent-sandbox]] — K8s SIG Apps 孵化的 Sandbox CRD，给 AI Agent 提供安全隔离的有状态容器原语
- [[agentcube]] — Volcano 社区 AI Agent / Code Interpreter 会话编排层（基于 agent-sandbox 的 Router + WorkloadManager + WarmPool）
- [[agentgateway]] — Solo.io / Istio 系出品的 AI-native L7 网关（LLM + MCP + A2A 三协议统一）
- [[powermem]] — OceanBase 出品的 LLM 持久化记忆中间件（向量+全文+稀疏+图四路混合 + 艾宾浩斯衰减）
- [[agent-recall]] — 本地优先的 MCP-native Agent 记忆库（SQLite + scope hierarchy + AI briefing）
- [[memsearch]] — Zilliz 出品的跨平台 AI coding agent 语义记忆系统（Markdown source-of-truth + Milvus hybrid search + progressive recall）
- [[tencentdb-agent-memory]] — 腾讯云出品的 OpenClaw / Hermes Agent 记忆插件（L0→L3 分层长期记忆 + Mermaid context offload + SQLite/TCVDB hybrid search）
- [[dynamo]] — NVIDIA 开源的数据中心级 LLM 推理编排层（Rust + Python + Go，分离式 P/D + KV 感知路由 + 四级 KV 缓存 + SLA 自动扩缩）
- [[vllm]] — UC Berkeley 出品的高吞吐 LLM 推理引擎（PagedAttention 创始者，Dynamo backend 之一）
- [[sglang]] — LMSYS 出品的高性能 LLM 推理引擎（RadixAttention 创始者，Dynamo backend 之一）
- [[nanobot]] — HKUDS 出品的极简个人 AI Agent 框架（Python，事件驱动 8 态状态机 + 17 渠道 + 7 厂商 + MCP）
- [[agentmemory]] — Rohit Ghumare 出品的本地化跨 Agent 记忆服务（TS + iii-engine + SQLite，三流 RRF + 零 LLM 默认 + 12 hooks + 53 MCP tools + 实时 viewer）

## 概念 (Concepts)

### 云原生
- [[gitops]] — 以 Git 为单一事实来源的运维方法论
- [[ai-ops]] — AI/LLM 增强运维（告警分诊、根因分析）
- [[cloud-native-security]] — 云原生安全实践与趋势

### Agent 记忆 / 设计模式
- [[agent-memory]] — Agent 长期记忆领域综述
- [[event-driven-memory-pipeline]] — 事件采集 → AI 压缩 → 双索引 → 反向注入闭环
- [[three-tier-search-protocol]] — 三层搜索协议（防上下文爆炸）
- [[ai-as-compressor]] — AI 作为压缩器的设计哲学
- [[ebbinghaus-forgetting-curve]] — `R = e^(-t/S)` 数学模型驱动 working/short/long 三层记忆衰减与晋升（PowerMem 核心）

### 检索 / RAG
- [[code-semantic-search]] — 代码语义检索方法论
- [[hybrid-search-rrf]] — Dense + Sparse + RRF 重排混合检索
- [[merkle-dag-fingerprint]] — 内容指纹做增量同步

### Agent 工程
- [[ai-agent-plugin-patterns]] — AI Agent 外挂的 9 条设计原则（迁移检查表）
- [[declarative-agent-management]] — 用 K8s CRD 声明式管理 AI Agent 集群（HiClaw 模式）
- [[agent-credential-isolation]] — Agent 凭据零暴露：网关托管真凭据，Agent 只持 consumer key

### LLM 推理 / Serving
- [[paged-attention]] — KV cache 分块管理基础理念（vLLM 起源，Dynamo KVBM 沿用）
- [[radix-attention]] — KV-aware 路由的算法基础（SGLang 起源，Dynamo router 沿用）
- [[disaggregated-serving]] — Prefill/Decode 分离式服务（Dynamo 默认架构）
- [[kv-cache-offload]] — KV 多级缓存方法论（GPU→CPU→SSD→远端，Dynamo KVBM 实现）

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
- [[src-hami-architecture]] — HAMi 架构（HEAD `5dca58e`，Kubernetes 异构 GPU sharing/vGPU：webhook + scheduler extender + device plugin + 多厂商 device abstraction）
- [[src-dra-driver-nvidia-gpu-architecture]] — DRA Driver for NVIDIA GPUs 架构（HEAD `749a743`，Kubernetes DRA NVIDIA driver：ResourceClaim/ResourceSlice + NodePrepare + dynamic MIG/VFIO + ComputeDomain）
- [[src-gpu-operator-architecture]] — NVIDIA GPU Operator 架构（HEAD `0219120`，GPU 软件栈 Kubernetes Operator：ClusterPolicy/NVIDIADriver + state renderer + operands lifecycle）
- [[src-k8s-device-plugin-architecture]] — NVIDIA k8s-device-plugin 架构（HEAD `8688949`，官方 GPU device plugin：NVML/CUDA discovery + kubelet gRPC + env/volume/CDI Allocate）
- [[src-nemoclaw-architecture]] — NVIDIA NemoClaw 架构（HEAD `3c0340a`，OpenShell sandbox 内 always-on AI Agent 的 CLI 控制面，onboard FSM + gateway 托管凭证 + inference.local 路由 + policy/shields）
- [[src-openshell-architecture]] — NVIDIA OpenShell 架构（HEAD `97986d9`，AI Agent 安全运行时，Gateway 控制面 + sandbox Supervisor enforcement + OPA/Z3 policy + provider credential/inference.local 路由）
- [[src-ai-infra-learning-cn-stars]] — AI Infra Learning 中文 Star 项目清单（32 个项目，AI 系统/Infra → CUDA/GPU kernel → LLM 推理/部署 → Agent/Skills → 面试材料）

## 分析 (Analysis)

- [[agent-memory-project-map]] — Agent Memory 项目地图（claude-mem / agent-recall / agentmemory / powermem / memsearch / TencentDB-Agent-Memory 横向对比与选型）
- [[agent-runtime-sandbox-project-map]] — Agent Runtime / Sandbox 项目地图（agent-sandbox / AgentCube / OpenShell / NemoClaw / HiClaw / AgentScope / agentgateway 分层对比）
- [[llm-inference-serving-project-map]] — LLM Inference / Serving 项目地图（vLLM / SGLang / Dynamo / SkyPilot / K8s GPU stack 横向拆解）
- [[ai-agent-frameworks-map]] — AI Agent Frameworks 项目地图（coding agent / framework / MCP / skills / memory / runtime 分层）
- [[coding-agent-selection-map]] — Coding Agent / Personal Agent 选型地图（Claude Code / OpenCode / OpenClaude / NemoClaw / nanobot）
- [[agent-memory-selection-matrix]] — Agent Memory 细分选型矩阵（claude-mem / agent-recall / agentmemory / PowerMem / memsearch / TencentDB-Agent-Memory）
- [[agent-runtime-sandbox-selection-map]] — Agent Runtime / Sandbox 细分选型地图（agent-sandbox / AgentCube / OpenShell / NemoClaw / HiClaw / AgentScope / agentgateway）
- [[llm-serving-engine-selection-map]] — LLM Serving / 推理引擎选型地图（vLLM / SGLang / Dynamo / SkyPilot / K8s GPU stack）
- [[mcp-gateway-tooling-map]] — MCP Server / Tool Gateway 对比地图（FastMCP / GitHub MCP / Playwright MCP / kubectl MCP / agentgateway / Plano）
- [[agent-skills-plugin-system-map]] — Agent Skills / Plugin System 对比地图（plugin / skill / MCP tool 三种扩展形态）
- [[code-semantic-search-rag-map]] — Code Semantic Search / Code RAG 对比地图（Claude Context / memsearch / Milvus / tree-sitter）
- [[agent-framework-programming-model-map]] — Agent Framework 编程模型对比地图（LangGraph / LangChain / Dify / AgentScope / Eino / ADK / AutoGen / CrewAI）
- [[github-stars-ingest-candidates]] — GitHub Stars 下一批摄入候选清单（P0-P2：agent-substrate / AgentScope Runtime / mem0 / Codex / llm-d / AI Gateway / K8s GPU 等）
- [[github-stars-backlog-implementation-map]] — GitHub Stars P0-P2 实现地图（把 backlog 项目落到 runtime/memory/coding agent/serving/gateway/AI Ops/code graph/GPU 正式选型结构）
- [[ai-infra-learning-cn-map]] — AI Infra 中文学习项目地图（中文 AI Infra / LLM / CUDA / Agent 学习路线）

---

## 待建页面

以下实体/概念在文章中被提及但尚未建页：

### 云原生
- k8s-gpu-device-stack — Kubernetes GPU/异构设备资源层项目地图（device plugin、GPU Operator、vGPU/GPU sharing、DRA、CDI、DCGM/NVML、fake GPU）
- k8s-core-controller-map — Kubernetes controller/operator 项目地图（client-go、controller-runtime、kubebuilder、CRD/webhook、调度、多集群、可观测）
- controller-runtime / kubebuilder / client-go — Kubernetes controller/operator 开发核心工具链
- dra / cdi / gpu-sharing — Kubernetes 下一代设备资源分配、容器设备声明和 GPU sharing 方向
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
- nemoclaw / openshell / nvidia — NVIDIA OpenShell sandbox 与 NemoClaw host-side 编排层
- openclaw / opencode / openclaude / hermes-agent — 个人 Agent、coding agent 与 Agent OS 代表项目
- agent-skills — Agent 能力包模式（Markdown + scripts + workflow，可迁移到 Claude Code / Codex / OpenCode）
- langchain / langgraph / dify / agentscope / eino / adk — Agent framework 与 workflow runtime 代表项目
- fastmcp / playwright-mcp / github-mcp-server / plano — MCP server、browser automation、GitHub tools 与 Agentic proxy 代表项目
- agentscope — 阿里通义实验室 AgentScope 2.0 多 Agent 应用框架（事件流 ReAct、Toolkit/MCP/Skill、Workspace/offload、FastAPI 多租户服务）
- skypilot — AI/ML 多云算力控制平面（统一 YAML/SDK，跨 Kubernetes / Slurm / 公有云做 GPU 资源选择、failover、managed jobs、serve）
- bullmq — Node.js 任务队列（claude-mem 后台压缩调度）
- chroma — 开源向量数据库（claude-mem 使用）
- fts5 — SQLite 全文索引扩展
- outbox-pattern — 事务性消息发布模式
- tree-sitter — 多语言 AST 解析器（claude-context AST splitter 基础）
- rrf — Reciprocal Rank Fusion 重排算法（已并入 hybrid-search-rrf 概念页）
- higress — AI 网关（HiClaw 凭据托管核心，apig-20240327 SDK）
- matrix-protocol — 分布式 IM 协议（HiClaw 协作平面）
- k8s-operator — Kubernetes Operator 模式（HiClaw 控制平面骨架）
- kine — SQLite-backed etcd 协议层（HiClaw 嵌入式模式）
- autogen / langgraph / crewai — 多 Agent 框架同类对比项
- github-stars-ingest-candidates — 下一批 GitHub Stars 摄入候选项目：agent-substrate/substrate、agentscope-runtime、mem0、ReMe、Codex、Pi、oh-my-pi、multica、open-cowork、aibrix、llm-d、K8s AI assistant、AI Gateway、Code Graph、GPU/DRA 等（已实现为 [[github-stars-backlog-implementation-map]]，原候选清单见 [[github-stars-ingest-candidates]]）
- ai-infra-learning-cn — 中文 AI Infra 学习项目：AISystem / AIInfra / InfraTech / LeetCUDA / Awesome-LLM-Inference / self-llm / hello-agents / nanoclaw 等（详见 [[ai-infra-learning-cn-map]]）
