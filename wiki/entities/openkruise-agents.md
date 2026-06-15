---
title: OpenKruise Agents
tags: [ai-agent, agent-runtime, sandbox, kubernetes, openkruise, e2b]
date: 2026-06-15
sources: [openkruise-agents-architecture-analysis.md]
related: ["[[src-openkruise-agents-architecture]]", "[[agent-sandbox]]", "[[agentcube]]", "[[agent-runtime-substrate]]", "[[declarative-agent-management]]", "[[agent-credential-isolation]]", "[[cloud-native-security]]"]
---

# OpenKruise Agents

OpenKruise Agents 是 OpenKruise 面向 AI Agent sandbox lifecycle management 的 Kubernetes 原生平台。它把 `Sandbox` / `SandboxSet` / `SandboxClaim` / `SandboxTemplate` CRD、E2B-compatible API、Envoy 路由扩展、agent-runtime sidecar、identity token 和动态 CSI mount 组合成一套“在 K8s 上运营 Agent sandbox”的控制面。

详细架构见 [[src-openkruise-agents-architecture]]。

## 关键事实

- 仓库：[openkruise/agents](https://github.com/openkruise/agents)
- 当前核验：GitHub API 显示默认分支 `master`，最近 push `2026-06-12`，约 202 stars / 78 forks，Apache-2.0，主语言 Go
- 本 wiki 分析版本：HEAD `0e58df8`（2026-06-12）
- 核心入口：`agent-sandbox-controller`、`sandbox-manager`、`traffic-extension`、`sandbox-gateway`
- 关键 API：`Sandbox`、`SandboxSet`、`SandboxClaim`、`SandboxTemplate`
- 产品入口：E2B-compatible `/sandboxes`、`/snapshots`、pause/resume/connect/timeout/debug 等 API
- 典型场景：code interpreter、cloud desktop、Claude Code / OpenClaw sandbox、RL/HITL/open-world training、长寿命 workspace

## 架构定位

OpenKruise Agents 处在 [[agent-sandbox]] 和 [[agentcube]] 中间偏平台化的一层：

- 比 [[agent-sandbox]] 更完整：不仅有 sandbox lifecycle primitive，还把 warm pool、claim、E2B API、路由、identity、CSI 和 runtime sidecar 接起来。
- 比 [[agentcube]] 更底层：不主打 AgentRuntime / CodeInterpreter invocation 产品抽象，而是提供更通用的 sandbox 管理、clone/checkpoint、route 和 E2B 兼容面。
- 比 [[substrate]] 更 K8s CRD 化：Substrate 聚焦 actor/worker multiplexing 和 wake routing；OpenKruise Agents 聚焦可声明、可预热、可暂停/恢复、可路由的 sandbox。
- 可作为 Agent framework 的远端 workspace backend：AgentScope、coding agent、browser/desktop agent 可以把它当作 E2B-like 执行环境。

## 核心组件

| 组件 | 作用 |
|------|------|
| `agent-sandbox-controller` | K8s controller-runtime 控制面，管理 Sandbox、SandboxSet、SandboxClaim、SandboxUpdateOps、SecurityTokenRefresh。 |
| `sandbox-manager` | E2B-compatible HTTP API 控制面，负责 claim/clone/pause/resume/delete checkpoint、API key storage、team permission 和 route sync。 |
| `traffic-extension` | Envoy external processing gRPC 服务，把 sandbox 请求改写为 original-dst 路由。 |
| `sandbox-gateway` | Envoy Go HTTP filter 版本的数据面扩展，解析 sandboxID/port 并写 dynamic metadata。 |
| `sandboxcr infra` | `Infrastructure` / `Sandbox` 抽象的 K8s CRD 实现，把 API 请求落到 SandboxClaim/Sandbox/PVC/Pod。 |
| `agent-runtime` / `identity` / `CSI` | sandbox 内 runtime 初始化、短期 token 传播、动态 volume mount 的扩展点。 |

## 关键判断

- **Warm pool 是控制面协议**：`SandboxSet` 保持可用库存，`SandboxClaim` 显式领取；这比简单 Pod pool 更适合并发、超时、失败保留和滚动更新。
- **E2B API 降低接入成本**：上层 SDK 可以用 familiar API 创建、暂停、恢复、连接 sandbox；平台侧仍保留 K8s CRD/GitOps/RBAC 能力。
- **路由不走 Service per sandbox**：Envoy ext_proc / Go filter 用 sandboxID 查 route registry，把流量导到 Pod IP:port，适合大量短会话/长会话混合的 sandbox。
- **安全边界要继续补齐**：identity provider、API key storage、token propagation、runtimeClass、NetworkPolicy 和 audit 是生产采用前必须验证的部分。

## 什么时候优先看它

- 需要在 K8s 上搭建 E2B-like sandbox service；
- 希望同时拥有 CRD 管理面和 SDK/API 产品面；
- 需要 warm pool 降低 Agent / Code Interpreter 冷启动；
- 需要 pause/resume、checkpoint/clone、动态存储挂载、路由和多租户 namespace/team；
- 想把 AI Agent workspace 从本地/Docker/E2B SaaS 迁到自有 Kubernetes。

## 什么时候不适合

- 只需要一个本地 Agent 框架或 Python workflow runtime；
- 只想学习最小 sandbox CRD，不想同时理解 manager/gateway/identity/CSI；
- 对强 runtime enforcement 的要求高于生命周期管理，此时还要叠加 [[cloud-native-security]]、OPA/egress gateway、gVisor/Kata/seccomp 等机制；
- 当前业务不能接受快速演进 API 和 roadmap 中尚未完成的 storage/network/runtime/scheduling/observability 能力。
