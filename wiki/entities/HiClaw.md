---
title: HiClaw
tags: [agent-platform, k8s-operator, multi-agent, ai-infra]
date: 2026-06-12
sources: [hiclaw-architecture-analysis.md]
related: [[claude-code]], [[higress]], [[matrix-protocol]], [[k8s-operator]], [[mcp]], [[declarative-agent-management]], [[agent-credential-isolation]]
---

# HiClaw

阿里 Higress 团队（agentscope-ai）出品的开源 **K8s 原生多 Agent 协作平台**。把"管 AI Agent 大军"问题完全套进 K8s 范式：4 个 CRD（`Worker` / `Team` / `Human` / `Manager`）声明 Agent，controller 把每个 Agent 落成"容器 + Matrix IM 用户 + Higress consumer"三位一体，人类与 Agent 在同一组 Matrix 房间里协作，真实 LLM 凭据托管在 Higress 网关，Worker 只持 consumer key 实现 [[agent-credential-isolation|凭据零暴露]]。

详细架构与设计哲学见 [[src-hiclaw-architecture]]。

## 关键事实

- 仓库：[agentscope-ai/HiClaw](https://github.com/agentscope-ai/HiClaw)
- 当前核验：GitHub API 显示 main 最近 push `2026-06-10`，最新 tag `v1.1.2`
- 本 wiki 架构分析版本：v1.1.0（2026-04-24，HEAD `e21ac83`）
- 主要语言：Go（controller，153 文件） + Python（worker runtimes：QwenPaw / Hermes）
- 同栈：[[higress|Higress AI Gateway]] · Tuwunel（[[matrix-protocol|Matrix]] 服务端） · MinIO · Element Web · `k3s-io/kine`（嵌入式 etcd）
- Worker runtime 三选一：OpenClaw（[[claude-code]] 系）/ QwenPaw（基于 Qwen Code）/ Hermes（autonomous coding agent）；当前默认 QwenPaw

## 从 0 到一个 Worker 跑起来

HiClaw 的最小闭环不是“启动一个 Python Agent”，而是创建一套协作身份和凭据边界：

1. 安装 HiClaw：本地 Docker 模式走 installer，K8s 模式走 Helm chart。
2. 准备 LLM 配置：`credentials.llmProvider`、`credentials.defaultModel`、`credentials.llmApiKey`、`credentials.llmBaseUrl`。
3. 启动控制面：controller 创建/管理 CRD，并连接 Matrix、gateway、storage。
4. 创建 `Human` / 管理员身份，进入 Element Web 或其他 Matrix client。
5. Manager Agent 通过 Matrix 收到“创建 Worker”的请求。
6. Manager 调 `hiclaw worker create ...`，controller 写入 `Worker` CR。
7. Worker reconciler 创建 Matrix user/room、gateway consumer key、对象存储权限和 Worker 容器。
8. Worker 容器启动后进入 Matrix 房间，后续人类、Manager、Worker 都在 IM 协作平面里交流。

这条路径体现 [[declarative-agent-management]]：用户声明 Worker，controller 负责把容器、IM 身份、网关凭据和存储权限收敛到期望状态。

## Helm 组件配置

当前 Helm chart 的主要组件来自 `helm/hiclaw/values.yaml` 与 templates：

| 组件 | values 路径 | 作用 |
|------|-------------|------|
| controller | `controller.*` | CRD reconciler、worker lifecycle、gateway/credential/storage 编排；可配 replica、resources、workerBackend、uninstall hook |
| manager | `manager.*` | 是否创建 Manager CR、Manager runtime/model/image/resources |
| matrix | `matrix.*` | Tuwunel 或 Synapse；managed/existing；控制 Matrix server、持久化和服务端口 |
| gateway | `gateway.*` / `higress.*` | managed Higress 或 existing AI Gateway；配置公网 URL、APIG 信息、Higress subchart |
| storage | `storage.*` | managed MinIO 或 existing OSS；bucket、endpoint、MinIO 资源和持久化 |
| credentialProvider | `credentialProvider.*` | 云上 APIG/OSS 场景下签发 STS / RAM role token |
| secrets | `credentials.*` | Matrix admin、LLM provider、默认模型和 base URL |

本地 kind/minikube 默认更偏 managed Tuwunel + managed Higress + managed MinIO；云上 ACK/ACS 场景可以把 gateway/storage 切到 existing provider。

## 与 [[claude-mem]] 的区别

| 维度 | [[HiClaw]] | [[claude-mem]] |
|------|------------|----------------|
| 目标 | 管理多个 Agent 的协作、身份、容器、房间、凭据 | 给 Claude Code 增加长期记忆 |
| 状态单位 | Worker/Team/Human/Manager CR | 用户 prompt、tool log、memory fact |
| 控制面 | Kubernetes controller + Matrix + gateway | Claude Code hooks + memory server/storage |
| 安全重点 | Agent 只持 consumer key，凭据在 gateway | 记忆采集、压缩、检索和上下文注入 |
| 适合问题 | 多 Agent 运维、人在回路、协作拓扑 | 单 Agent 跨会话记忆 |

二者可组合：HiClaw 负责“Agent 如何被创建、协作和持权”，记忆系统负责“Agent 如何记住长期事实”。
