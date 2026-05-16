---
title: Wiki 索引
date: 2026-05-12
---

# 知识库索引

## 实体 (Entities)

### 云原生
- [[kubernetes]] — 容器编排平台，云原生核心（5 篇源文件）
- [[argocd]] — Kubernetes GitOps 持续交付工具
- [[gvisor]] — Google 出品的用户态内核容器隔离运行时
- [[kata-containers]] — OpenInfra 出品的轻量 microVM 容器运行时
- [[istio]] — CNCF 服务网格（agentgateway 复用其 KRT / xDS / HBONE 基建）
- [[gateway-api]] — K8s SIG-Network 新一代入口 API（agentgateway 控制面 API 基础）

### AI Agent / LLM Infra
- [[claude-code]] — Anthropic 出品的 CLI AI Agent，提供 Lifecycle Hook 插件机制
- [[claude-mem]] — 给 Claude Code 装上长期记忆的开源插件
- [[claude-agent-sdk]] — `@anthropic-ai/claude-agent-sdk`，Agent 编程 SDK
- [[claude-context]] — Zilliz 出品的 MCP 插件，把代码库语义检索接入 AI Agent
- [[mcp]] — Model Context Protocol，AI Agent 工具/资源接入协议
- [[milvus]] — 开源向量数据库（dense + sparse + RRF）
- [[HiClaw]] — 阿里 Higress 系出品的 K8s 原生多 Agent 协作平台
- [[agent-sandbox]] — K8s SIG Apps 孵化的 Sandbox CRD，给 AI Agent 提供安全隔离的有状态容器原语
- [[agentgateway]] — Solo.io / Istio 系出品的 AI-native L7 网关（LLM + MCP + A2A 三协议统一）
- [[powermem]] — OceanBase 出品的 LLM 持久化记忆中间件（向量+全文+稀疏+图四路混合 + 艾宾浩斯衰减）
- [[oceanbase]] — 蚂蚁集团开源的企业级分布式数据库（PowerMem 默认后端，原生向量 + FTS + 图）
- [[dynamo]] — NVIDIA 开源的数据中心级 LLM 推理编排层（Rust + Python + Go，分离式 P/D + KV 感知路由 + 四级 KV 缓存 + SLA 自动扩缩）
- [[vllm]] — UC Berkeley 出品的高吞吐 LLM 推理引擎（PagedAttention 创始者，Dynamo backend 之一）
- [[sglang]] — LMSYS 出品的高性能 LLM 推理引擎（RadixAttention 创始者，Dynamo backend 之一）

## 概念 (Concepts)

### 云原生
- [[gitops]] — 以 Git 为单一事实来源的运维方法论
- [[ai-ops]] — AI/LLM 增强运维（告警分诊、根因分析）
- [[cloud-native-security]] — 云原生安全实践与趋势
- [[k8s-operator]] — K8s Operator 模式（CRD + reconcile loop）
- [[k8s-crd]] — CustomResourceDefinition 扩展点
- [[network-policy]] — K8s NetworkPolicy（L3/L4 网络隔离）
- [[xds]] — Envoy/Istio 配置发现协议族（agentgateway 控制面分发协议）
- [[hbone]] — Istio mTLS over HTTP/2 CONNECT 隧道
- [[cel]] — Google Common Expression Language（agentgateway 策略 IR）

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
- [[src-agentgateway-architecture]] — agentgateway 架构（v1.2.0-alpha.2，Istio 系骨架 + Rust 数据面，LLM/MCP/A2A 三协议 AI Gateway）
- [[src-powermem-architecture]] — PowerMem 架构（v1.1.1，OceanBase 持久化记忆中间件，向量+全文+稀疏+图四路混合 + 艾宾浩斯衰减）
- [[src-dynamo-architecture]] — NVIDIA Dynamo 架构（v1.2.0，数据中心级 LLM 推理编排层，分离式 P/D + KV 感知路由 + 四级 KV 缓存 KVBM + SLA 自动扩缩）

## 分析 (Analysis)

_暂无条目_

---

## 待建页面

以下实体/概念在文章中被提及但尚未建页：

### 云原生
- opentelemetry — 可观测性框架
- ebpf — 内核级可编程技术
- ingress-nginx — 已退役的 K8s 入口控制器
- service-mesh — 服务网格（Istio/Cilium/Envoy，istio 已建页）
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
