---
title: agent-sandbox
tags: [k8s-operator, agent-runtime, ai-infra, sig-apps]
date: 2026-06-12
sources: [agent-sandbox-architecture-analysis.md]
related: [[HiClaw]], [[k8s-operator]], [[gvisor]], [[kata-containers]], [[declarative-agent-management]]
---

# agent-sandbox

`kubernetes-sigs/agent-sandbox` 是 **K8s SIG Apps 官方孵化**的 Sandbox CRD + controller。把 AI Agent runtime 那种"长寿命、有状态、单实例、可暂停、有稳定身份"的容器形态建模成第一类 K8s 资源——比 Deployment（无状态副本）和 StatefulSet（编号 Pod）都更精准。**隔离机制完全委托给标准 K8s 原语**（[[gvisor]] / [[kata-containers]] / [[network-policy]]），controller 只做生命周期编排。

详细架构见 [[src-agent-sandbox-architecture]]。

## 关键事实

- 仓库：[kubernetes-sigs/agent-sandbox](https://github.com/kubernetes-sigs/agent-sandbox)
- 当前核验：GitHub API 显示 main 最近 push `2026-06-11`，最新稳定 tag `v0.4.6`，另有 `v0.5.0rc1`
- 本 wiki 架构分析版本：v0.4.5+11（HEAD `e1d8898`，2026-04-23 左右）
- 主要语言：Go 1.26.2，模块 `sigs.k8s.io/agent-sandbox`
- 4 个 CRD：核心 `Sandbox` (agents.x-k8s.io) + 扩展 `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` (extensions.agents.x-k8s.io)
- 治理：K8s SIG Apps 孵化项目，遵循 [Kubernetes Resource Model](https://kubernetes.io/docs/concepts/overview/working-with-objects/) 范式
- SDK：Go + Python（codegen 生成） + 标准 K8s clientset/informer/lister
- examples 目录当前超过 20 个：quickstart / hello-world / kata-gke / openclaw / hermes / langchain / jupyter / vscode / chrome / HPA / Kueue / Cilium/NetworkPolicy / MCP / Ray / Python SDK 等

## 与 [[HiClaw]] 的关系

互补不竞争——agent-sandbox 是**基础设施层**（提供"安全运行 1 个有状态 Agent 容器"原语），HiClaw 是**应用层**（提供"管 N 个 Agent 协作 + IM 平面 + 凭据网关"）。理论上 HiClaw 的 Worker runtime 完全可以跑在 agent-sandbox 之上。

## 与 [[HiClaw]] 的完整对比

| 维度 | agent-sandbox | [[HiClaw]] |
|------|---------------|------------|
| 层级 | Runtime substrate / CRD 原语 | 多 Agent 协作平台 |
| 核心对象 | Sandbox、Claim、Template、WarmPool | Worker、Team、Human、Manager |
| 协作模型 | 不管 IM / team / manager | Matrix 房间 + Manager/Worker/Human |
| 凭据模型 | 由 PodTemplate / 用户环境决定 | Gateway consumer key + 真凭据托管 |
| 隔离模型 | 委托 gVisor/Kata/NetworkPolicy/PodTemplate | 依赖容器后端，可进一步叠 agent-sandbox |
| 启动优化 | WarmPool / Template / suspend-resume | Worker lifecycle + runtime package |
| 典型用户 | 平台工程师、runtime 基座维护者 | Agent 平台/协作产品维护者 |

## GKE Kata walkthrough 速记

1. 准备支持 Kata/gVisor 的 GKE 或兼容集群。
2. 安装 agent-sandbox CRD/controller。
3. 创建带 runtimeClass / securityContext / volume / network policy 的 `SandboxTemplate`。
4. 可选创建 `SandboxWarmPool`，预热若干 Pod。
5. 用户创建 `SandboxClaim`，controller 从 WarmPool 领取或新建 Sandbox。
6. Sandbox Ready 后，通过 service / SDK / router 访问容器内 agent 或工具。
7. 空闲后 scale to zero / suspend，保留 PVC 状态，后续 resume。

这个流程说明它的关键不是“创建 Pod”，而是把单实例、有状态、可暂停、可领取的 Agent 容器变成可声明和可复用的资源。

## v0.5 / beta 路线

roadmap 当前显示几条主线：

- API 与 runtime 解耦，走 portable backend / common proto；
- SandboxTemplate / WarmPool rolling update；
- router 成为 first-class 项目组件；
- auto suspend/resume、scale-to-zero、TFFI 延迟优化；
- 智能 WarmPool 选择和 claim latency 优化；
- alpha → beta API versioning；
- TypeScript SDK、MCP server、Ray / LangChain / CrewAI / kAgent 集成。

这意味着 v0.5 之后的重点会从“CRD 能跑”走向“多后端、低延迟、SDK、router、生产指标”。

## examples 导读

| 类别 | examples |
|------|----------|
| 入门 | `quickstart`, `hello-world-sandbox`, `python-sdk-quickstart` |
| 隔离 / runtime | `kata-gke-sandbox`, `chrome-sandbox`, `sandboxed-tools`, `sandbox-ksa`, `policy` |
| Agent / framework | `openclaw-sandbox`, `hermes-agent`, `langchain`, `gemini-cu-sandbox`, `code-interpreter-agent-on-adk` |
| 扩缩 / 调度 | `hpa-swp-scaling`, `kueue-agent-sandbox`, `manual-pdb` |
| 网络策略 | `composing-sandbox-nw-policies`, `mcp-server-sandbox` |
| 工具型环境 | `jupyterlab`, `vscode-sandbox`, `aio-sandbox`, `analytics-tool`, `python-runtime-sandbox`, `ray-integration` |
