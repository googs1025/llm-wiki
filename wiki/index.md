---
title: Wiki 索引
date: 2026-05-12
---

# 知识库索引

## 实体 (Entities)

### 云原生
- [[kubernetes]] — 容器编排平台，云原生核心（5 篇源文件）
- [[argocd]] — Kubernetes GitOps 持续交付工具

### AI Agent / LLM Infra
- [[claude-code]] — Anthropic 出品的 CLI AI Agent，提供 Lifecycle Hook 插件机制
- [[claude-mem]] — 给 Claude Code 装上长期记忆的开源插件
- [[claude-agent-sdk]] — `@anthropic-ai/claude-agent-sdk`，Agent 编程 SDK

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

## 源文件摘要 (Sources)

- [[src-k8s-v1.36-sneak-peek]] — K8s v1.36 新特性预览（弃用 externalIPs、SELinux GA）
- [[src-holmesgpt-k8s-alerts]] — HolmesGPT 自动诊断 K8s 告警（Runbook > 模型选择）
- [[src-k3s-gitops-k0rdent]] — K3s + k0rdent GitOps 部署 On-Prem 集群
- [[src-ai-vulnerability-discovery]] — AI 驱动的漏洞发现变革与应对策略
- [[src-argocd-overview]] — Argo CD 核心功能与架构概览
- [[src-claude-mem-architecture]] — claude-mem 架构与设计思路（v13.1.0，跨会话记忆插件）

## 分析 (Analysis)

_暂无条目_

---

## 待建页面

以下实体/概念在文章中被提及但尚未建页：

### 云原生
- opentelemetry — 可观测性框架
- ebpf — 内核级可编程技术
- gateway-api — K8s 新一代入口 API
- ingress-nginx — 已退役的 K8s 入口控制器
- service-mesh — 服务网格（Istio/Cilium/Envoy）
- containerd — 容器运行时
- prometheus — 监控系统
- serverless-wasm — Serverless 与 WebAssembly
- platform-engineering — 平台工程

### AI Agent / LLM Infra
- bullmq — Node.js 任务队列（claude-mem 后台压缩调度）
- chroma — 开源向量数据库
- mcp — Model Context Protocol
- fts5 — SQLite 全文索引扩展
- outbox-pattern — 事务性消息发布模式
