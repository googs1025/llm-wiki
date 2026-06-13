---
title: NemoClaw
tags: [entity, ai-agent, sandbox, nvidia, coding-agent]
date: 2026-06-13
sources: [nemoclaw-architecture-analysis.md]
related: [[openshell]], [[agent-sandbox]], [[agentgateway]], [[agent-credential-isolation]], [[cloud-native-security]], [[vllm]]
---

# NemoClaw

NemoClaw 是 NVIDIA 为 [[openshell|OpenShell]] sandbox 内 always-on AI Agent 提供的 TypeScript CLI 控制面。它把 guided onboarding、gateway、provider inference、sandbox 生命周期、agent setup、network policy、凭证迁移和 e2e 验证收束成一个命令面。详见 [[src-nemoclaw-architecture]]。

## 架构边界

NemoClaw 不是新的推理引擎，也不是新的多 Agent framework。它更像 [[openshell|OpenShell]] 的 host-side 编排层：在宿主机上规划 gateway、provider、sandbox、OpenClaw/Hermes runtime、policy preset 和 messaging channel，然后把结果应用到 sandbox。

## 关键设计

- 命令层保持很薄，`src/commands/**` 主要负责参数解析。
- `onboard` 是可恢复状态机，串起 preflight、gateway、provider inference、sandbox、agent setup 和 policy。
- Provider 凭证迁移到 gateway，agent 通过 `inference.local` 调模型，符合 [[agent-credential-isolation]]。
- Policy 默认 deny-by-default，再叠加 selected presets 和 messaging channel 所需网络权限。
- Messaging channel 通过 manifest 编译成 credential、network policy、agent render、health check 等计划。

## 选型判断

需要把 OpenClaw/Hermes 这类个人 agent 放进可审计 sandbox 并接入多 provider 推理时看 NemoClaw。需要底层 runtime enforcement 时看 [[openshell]]；需要 Kubernetes 原生 sandbox 时看 [[agent-sandbox]]；需要统一治理 LLM/MCP/A2A 出口时看 [[agentgateway]]。
