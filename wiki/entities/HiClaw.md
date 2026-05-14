---
title: HiClaw
tags: [agent-platform, k8s-operator, multi-agent, ai-infra]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md]
related: [[claude-code]], [[higress]], [[matrix-protocol]], [[k8s-operator]], [[mcp]], [[declarative-agent-management]], [[agent-credential-isolation]]
---

# HiClaw

阿里 Higress 团队（agentscope-ai）出品的开源 **K8s 原生多 Agent 协作平台**。把"管 AI Agent 大军"问题完全套进 K8s 范式：4 个 CRD（`Worker` / `Team` / `Human` / `Manager`）声明 Agent，controller 把每个 Agent 落成"容器 + Matrix IM 用户 + Higress consumer"三位一体，人类与 Agent 在同一组 Matrix 房间里协作，真实 LLM 凭据托管在 Higress 网关，Worker 只持 consumer key 实现 [[agent-credential-isolation|凭据零暴露]]。

详细架构与设计哲学见 [[src-hiclaw-architecture]]。

## 关键事实

- 仓库：[agentscope-ai/HiClaw](https://github.com/agentscope-ai/HiClaw)
- 版本：v1.1.0（2026-04-24）
- 主要语言：Go（controller，153 文件） + Python（worker runtimes：QwenPaw / Hermes）
- 同栈：[[higress|Higress AI Gateway]] · Tuwunel（[[matrix-protocol|Matrix]] 服务端） · MinIO · Element Web · `k3s-io/kine`（嵌入式 etcd）
- Worker runtime 三选一：OpenClaw（[[claude-code]] 系）/ QwenPaw（基于 Qwen Code）/ Hermes（autonomous coding agent）；当前默认 QwenPaw

## TODO

- [ ] 写一份"从 0 到一个 Worker 跑起来"的实战 walkthrough
- [ ] 跟 [[claude-mem]] 做"AI Agent 长期记忆 vs 多 Agent 协作运维"维度对比
- [ ] 补 Helm chart 各 sub-component（element-web / gateway / matrix / storage）的配置说明
