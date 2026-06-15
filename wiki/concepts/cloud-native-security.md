---
title: 云原生安全
tags: [security, kubernetes, cloud-native, ai]
date: 2026-06-15
sources: [ai-vulnerability-discovery.md, k8s-v1.36-sneak-peek.md, openkruise-agents-architecture-analysis.md]
related: [[kubernetes]], [[gateway-api]], [[agentgateway]], [[agent-sandbox]], [[openkruise-agents]], [[agent-credential-isolation]]
---

# 云原生安全

云原生环境下的安全实践、威胁模型和工具链。

## 当前趋势

### AI 与漏洞发现
AI 模型同时加速漏洞发现和低质量报告泛滥。核心应对：
- 维护者：公开威胁模型 + 最低报告标准 + AI 辅助分诊
- 发现者：完整 PoC + 修复 PR，禁止批量提交
- 详见 [[src-ai-vulnerability-discovery]]

### K8s v1.36 安全强化
- 弃用 `externalIPs`（中间人攻击风险）
- 移除 `gitRepo` Volume（root 提权风险）
- 详见 [[src-k8s-v1.36-sneak-peek]]

## Service Mesh / Gateway 安全

Service Mesh 和 Gateway 安全的核心是把身份、流量策略和凭据边界从应用代码里抽出来：

- mTLS 让服务间调用绑定 workload identity，而不是只依赖网络位置；
- L7 policy 能按 host/path/header/JWT claims 做授权；
- [[gateway-api]] 提供更明确的入口角色分层，减少 Ingress annotation 漂移；
- [[agentgateway]] 这类 AI Gateway 把 LLM/MCP/A2A 出口流量纳入统一鉴权、限流、审计和 [[agent-credential-isolation]]。

AI Agent 场景下，mesh/gateway 的价值更高：Agent prompt 和工具调用不可完全信任，凭据、出口路由和 tool permission 应由网关策略兜住。

## 供应链安全

云原生供应链安全关注“镜像、依赖、构建和部署声明是否可信”：

- SBOM 记录镜像/包内依赖，方便漏洞影响面分析；
- 签名和 provenance 证明镜像来自可信构建流程；
- admission policy 在部署前检查镜像签名、基础镜像、capabilities、root 用户、hostPath 等；
- GitOps 环境下，集群实际状态应能回溯到 Git commit 和审计记录。

对 AI infra 来说，还要额外关注模型权重、adapter、prompt/skill 包、MCP server 包的来源。Agent 能动态加载技能或工具时，供应链边界不只在容器镜像，也在工具市场和技能市场。

## Runtime Security

运行时安全解决“已经跑起来后发生了什么”：

- syscall / eBPF 监控用于发现异常进程、文件、网络行为；
- gVisor / Kata / microVM 提供更强隔离，适合运行不可信 Agent 代码；
- [[agent-sandbox]] 把 gVisor、Kata、NetworkPolicy 等隔离机制委托给 PodTemplate，让用户按风险选择运行时；
- [[openkruise-agents]] 在 sandbox lifecycle 上继续补 E2B API key storage、identity token propagation、dynamic CSI mount 和 Envoy route registry，因此要同时审计 API 身份、运行时 token、存储挂载和路由表 stale/fail-close 行为；
- Falco/Tetragon 这类工具适合做 runtime detection，但需要和 workload identity、namespace、owner reference 关联，才知道异常来自哪个 Agent 或任务。

## Agent 特有风险

AI Agent 把云原生安全问题放大了：

- prompt injection 可能诱导 Agent 调用高危工具；
- MCP / skill 市场扩大了供应链和权限面；
- 长期运行的 Agent 有状态、有凭据、有文件系统，不能当作普通短任务；
- 观测日志可能包含 prompt、tool result、代码片段和 secret，需要 content policy 与 mask。

因此 Agent workload 推荐组合：[[agent-sandbox]] 做运行隔离，[[agentgateway]] / Gateway 做出口和凭据，[[loongsuite-pilot]] / trace 工具做审计与脱敏观测。


## Secrets Store / Security Profiles / Agent Networking

[[secrets-store-csi-driver]] 把外部 secret store 通过 CSI volume 注入 Pod，适合把真凭据留在 Vault、云 secret manager 或专用 provider 中。[[security-profiles-operator]] 把 seccomp/AppArmor/SELinux profiles 变成可声明、可分发、可录制的 runtime security 对象。[[kube-agentic-networking]] 则把 Agent/tool 的网络访问策略纳入 Kubernetes governance。三者分别补凭据、syscall/LSM 和网络出口三条安全线。
