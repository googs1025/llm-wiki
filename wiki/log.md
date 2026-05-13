---
title: 操作日志
date: 2026-04-22
---

# 操作日志

## [2026-04-22] init | 知识库初始化

创建基础目录结构和 Schema（CLAUDE.md）。

## [2026-04-22] ingest | Kubernetes v1.36 Sneak Peek

来源：kubernetes.io blog。创建源摘要页，更新 kubernetes 实体页。关键：externalIPs 弃用、gitRepo 移除、SELinux GA、Ingress NGINX 退役。

## [2026-04-22] ingest | HolmesGPT 自动诊断 K8s 告警

来源：CNCF blog。创建源摘要页、ai-ops 概念页。关键发现：Runbook 比模型选择更重要。

## [2026-04-22] ingest | K3s + k0rdent GitOps On-Prem 部署

来源：CNCF blog。创建源摘要页、gitops 概念页。K3s + Proxmox + k0rdent 声明式集群管理。

## [2026-04-22] ingest | AI 驱动的漏洞发现变革

来源：CNCF blog (Greg Castle, Google)。创建源摘要页、cloud-native-security 概念页。AI 同时加速漏洞发现和噪声报告。

## [2026-04-22] ingest | Argo CD 概览

来源：argo-cd.readthedocs.io。创建源摘要页、argocd 实体页。K8s 声明式 GitOps CD 工具。

## [2026-05-12] ingest | claude-mem 架构与设计思路

来源：thedotmack/claude-mem v13.1.0 架构分析。新建源摘要页 + 3 实体页（claude-mem / claude-code / claude-agent-sdk）+ 4 概念页（agent-memory / event-driven-memory-pipeline / three-tier-search-protocol / ai-as-compressor）。核心洞察：AI 作为压缩器而非问答器，边缘轻量 + 后台异步，三层搜索防上下文爆炸。

## [2026-05-12] ingest | Claude Context 架构与 AI Agent 外挂设计原则

来源：zilliztech/claude-context v0.1.13 架构分析。新建源摘要页 + 3 实体页（claude-context / milvus / mcp）+ 4 概念页（code-semantic-search / hybrid-search-rrf / merkle-dag-fingerprint / ai-agent-plugin-patterns）。反向更新 claude-code（加 MCP 客户端能力）、claude-mem（链接 mcp）。核心洞察：9 条 AI Agent 外挂迁移原则（分层 / 接口化 / 降级链 / 内容指纹 / 协议通道纪律 / 协作式取消 / 流式批处理 / 快照自愈 / 混合检索）。
## [2026-05-13] ingest | HiClaw 架构

来源：agentscope-ai/HiClaw v1.1.0 架构分析（HEAD `e21ac83`）。**首次通过新建的 `ingest-codebase` skill 自动产出。** 新建 raw 文件（323 行）+ wiki source 页（226 行），ASCII 自查通过（raw 67 │ ↔ wiki 67 │ byte-identical）。核心洞察：K8s operator 模式套到 AI Agent 运维（CRD = Agent 声明，reconcile = 自愈）；Matrix IM 作协作平面（每个 Agent 是 IM 用户，人在回路天然成立）；Higress AI Gateway 托管真凭据（Worker 永远只持 consumer key 实现 prompt-injection 抗性）；OpenClaw/QwenPaw/Hermes 三 runtime 可插（最近默认从 OpenClaw 切到 QwenPaw）；嵌入式 K8s 走 kine SQLite 让"装上像 Docker，骨子里是 K8s"。

## [2026-05-13] ingest | agent-sandbox 架构

来源：kubernetes-sigs/agent-sandbox v0.4.5+11 架构分析（HEAD `e1d8898`）。`ingest-codebase` skill 第二次产出，整套流程稳定。新建 raw 文件（260+ 行）+ wiki source 页（200+ 行）+ 4 个实体页 stub（agent-sandbox / gvisor / kata-containers）+ 2 个概念页 stub（k8s-operator / k8s-crd / network-policy）。ASCII 自查 raw 86 │ ↔ wiki 81 │（94% 保留，差异来自"安全模型"信任边界图未带到 wiki）。核心洞察：(1) Sandbox CRD 把 "1 stable identity + 持久存储 + 可暂停 + 可调度销毁" 做成第一类 K8s 资源（不是 Deployment 也不是 StatefulSet），`replicas: 0|1` 强制约束承载暂停语义；(2) **隔离机制完全委托** K8s 原语——controller 不强制 gVisor/Kata/NetworkPolicy，全在用户填的 PodTemplate 里透传，最大化基座灵活性；(3) WarmPool + OwnerReference 热转移做出 ~0 启动延迟的 Claim 领养；(4) Template 级默认 NetworkPolicy = deny RFC1918 + deny 云元数据，把"AI Agent 跑用户代码的 SSRF 防御"做成系统约束；(5) 跟 [[HiClaw]] **互补不竞争**——前者基础设施层，后者应用层，HiClaw Worker 理论上可以跑在 agent-sandbox 上。
