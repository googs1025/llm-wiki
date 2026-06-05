---
title: NemoClaw 架构与设计思路分析
tags: [architecture, ai-agent, sandbox]
date: 2026-06-05
sources: [nemoclaw-architecture-analysis.md]
related: [[NemoClaw]], [[OpenShell]], [[OpenClaw]], [[Hermes]], [[agent-sandbox]], [[agentgateway]], [[vllm]], [[agent-credential-isolation]], [[cloud-native-security]]
---

# NemoClaw 架构与设计思路分析

> 原文：`raw/nemoclaw-architecture-analysis.md` · 仓库：https://github.com/NVIDIA/NemoClaw · 分析版本 HEAD `3c0340a`

## 一句话定位

[[NemoClaw]] 是 [[NVIDIA]] 为 [[OpenShell]] sandbox 内运行 always-on [[AI Agent]] 提供的 TypeScript CLI 控制面：它把 guided onboarding、gateway、[[OpenClaw]] / [[Hermes]] agent 配置、routed inference、网络策略、凭证迁移、sandbox 生命周期和 e2e 验证收束到一个命令面。它更接近 [[agent-sandbox]] 与 [[agentgateway]] 之间的 host-side 编排层，而不是新的推理引擎；推理侧通过 `inference.local` 接入 NVIDIA/OpenAI/Anthropic/Gemini/[[vllm]]/Ollama 等 provider。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              User / CI / shell                               │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ nemoclaw / nemohermes
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ CLI front door                                                               │
│ src/nemoclaw.ts                                                             │
│ src/lib/cli/public-dispatch.ts                                               │
│                                                                              │
│ - sandbox-first grammar: nemoclaw <sandbox> <action>                         │
│ - argv normalization + public route translation                              │
│ - oclif command discovery/delegation                                          │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ command id / normalized argv
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Thin command surface                                                         │
│ src/commands/**                                                              │
│                                                                              │
│ parse flags/args ───────▶ src/lib/actions/** / command-support helpers       │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       │ action call
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Host-side orchestration                                                       │
│ src/lib/onboard.ts + src/lib/actions/**                                      │
│                                                                              │
│ preflight → gateway → provider/inference → sandbox → agent setup → policy    │
│              │             │                 │             │                 │
│              │             │                 │             └─ messaging plan │
│              │             │                 └─ registry/session state       │
│              │             └─ inference.local / model router / credentials   │
│              └─ OpenShell gateway lifecycle                                  │
└────────────────────────────┬───────────────────────────────┬─────────────────┘
                             │                               │
                             ▼                               ▼
┌──────────────────────────────────────────────┐   ┌───────────────────────────┐
│ External/runtime adapters                     │   │ Declarative assets         │
│ src/lib/adapters/{openshell,docker,http}/**   │   │ nemoclaw-blueprint/**      │
│ src/lib/runner.ts                             │   │ policies / presets / router│
└────────────────────────────┬─────────────────┘   └──────────────┬────────────┘
                             │                                      │
                             ▼                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ OpenShell gateway + sandbox runtime                                           │
│                                                                              │
│ gateway named "nemoclaw"                                                      │
│ - provider credentials are system-of-record in gateway                        │
│ - inference.local routes sandbox traffic to selected provider                 │
│ - network policy applies baseline + selected presets                          │
│                                                                              │
│ sandbox                                                                       │
│ - OpenClaw or Hermes runtime                                                  │
│ - agent config rendered/synced from host-side plan                            │
│ - messaging channel hooks and health checks                                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CLI 入口与公共语法 | 兼容 `nemoclaw <sandbox> <action>`，做 argv normalization、route translation、sandbox 名检查，再转给 oclif。 |
| 命令层 | `src/commands/**` 只解析 flags/args 并调用 action，不承载产品行为。 |
| Action / onboard 编排层 | 把命令变成 preflight、gateway、provider/inference、sandbox、agent setup、policy 的 host-side workflow。 |
| 领域规划层 | provider 映射、policy/lifecycle 分类、messaging manifest 编译等尽量保持纯函数或可测试规划逻辑。 |
| 外部边界适配 | 封装 OpenShell、Docker、HTTP、shell 子进程和 privileged sandbox exec。 |
| 状态与凭证 | `~/.nemoclaw` JSON registry/session/shields 状态；凭证只在进程 env staging，gateway 是 system of record。 |
| 安全与策略 | baseline deny-by-default policy、policy presets、shields up/down/status、redaction/hash。 |
| Messaging 扩展 | channel manifest → serializable plan → OpenShell provider/policy/agent config applier。 |
| 推理与模型路由 | `inference.local` 统一 sandbox 内出口，host/gateway 侧映射到 cloud 或 local provider。 |
| Blueprint 与测试 | OpenShell sandbox 资产、policy preset、runtime scripts、unit/e2e/e2e-scenario 验证矩阵。 |

核心分层约束是"薄命令 + 厚编排 + 纯规划 + 外部边界适配"。这与 [[ai-agent-plugin-patterns]] 里的接口化、边界清晰、可迁移能力包方向一致，也和 [[agent-credential-isolation]] 的凭证边界设计相互呼应。

## 关键数据流

### Onboard 主流程

```
┌──────────────┐
│ nemoclaw     │
│ onboard      │
└──────┬───────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ src/lib/onboard.ts:onboard                                          │
│                                                                    │
│ 1. branding/env/options: agent, non-interactive, resume, fresh      │
│ 2. validate sandbox name + usage notice + provider hint             │
│ 3. acquire onboard lock + load/create resumable session             │
│ 4. stage legacy credentials into process.env for gateway migration  │
│ 5. select agent: OpenClaw / Hermes                                  │
└──────┬─────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ state handlers                                                      │
│                                                                    │
│ handlePreflightState                                                │
│   └─ Docker/OpenShell/GPU/DNS/platform checks                       │
│ handleGatewayState                                                  │
│   └─ start/reuse/recover named OpenShell gateway                    │
│ handleProviderInferenceState                                        │
│   └─ provider/model/credential route; model router/local proxy      │
│ handleSandboxState                                                  │
│   └─ create/reuse/recreate sandbox, persist registry/session        │
│ handleAgentSetupState                                               │
│   └─ install/sync OpenClaw or Hermes runtime config                 │
│ handlePoliciesState                                                 │
│   └─ apply baseline + selected policy presets                       │
└──────┬─────────────────────────────────────────────────────────────┘
       │
       ▼
┌────────────────────────────────────────────────────────────────────┐
│ OpenShell gateway + sandbox side effects                            │
│                                                                    │
│ openshell gateway start/reuse                                       │
│ openshell provider create/update --credential <ENV_KEY>             │
│ openshell sandbox create/connect/exec                               │
│ openshell policy set                                                │
│ ~/.nemoclaw/sandboxes.json + session files                          │
└────────────────────────────────────────────────────────────────────┘
```

Onboard 是可恢复的 host-side 状态机，不是一次性安装脚本。它支持 resume/fresh/non-interactive、全局 lock、step 记录和失败恢复；近期提交也集中在把 provider inference、sandbox branch、OpenClaw setup 等分支抽成 FSM result。

### Messaging channel 编译与应用

```
┌──────────────────────┐
│ channel manifests     │
│ telegram/slack/...    │
└──────────┬───────────┘
           │ registry.list()
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ MessagingWorkflowPlanner                                         │
│ - de-duplicate configured channels                               │
│ - reject unsupported channels for selected agent                  │
│ - build ManifestCompilerContext                                  │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ ManifestCompiler.compile                                         │
│                                                                  │
│ resolve manifests                                                │
│ compile per-channel inputs + enrollment/reachability hooks        │
│ fan out into:                                                     │
│   credentialBindings                                              │
│   networkPolicy                                                   │
│   agentRender                                                     │
│   buildSteps                                                      │
│   stateUpdates                                                    │
│   healthChecks                                                    │
└──────────┬──────────────────────────────────────────────────────┘
           │ SandboxMessagingPlan (schemaVersion: 1)
           ▼
┌─────────────────────────────────────────────────────────────────┐
│ MessagingSetupApplier                                            │
│ - base64 JSON plan through env when needed                        │
│ - applyCredentialsAtOpenShell                                    │
│ - applyPolicyAtOpenShell                                         │
│ - applyAgentConfigAtOpenShell                                    │
│ - list/run hook requests                                          │
└──────────┬──────────────────────────────────────────────────────┘
           ▼
┌──────────────────────┐
│ OpenShell + sandbox   │
│ provider/policy/config│
└──────────────────────┘
```

Messaging 子系统的关键是 declarative manifest compiler：channel 不直接侵入 onboard 主流程，而是声明 secret/config input、policy preset、agent render、hook phase 和 health check，再编译成 serializable plan。

### 推理路由与凭证边界

```
┌────────────────────────────┐
│ user selects provider/model │
└──────────────┬─────────────┘
               ▼
┌──────────────────────────────────────────────────────────────┐
│ src/lib/inference/config.ts                                  │
│ provider -> endpointUrl=https://inference.local/v1            │
│          -> profile=inference-local                           │
│          -> credentialEnv                                     │
│          -> providerLabel/model                               │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ OpenShell gateway provider                                   │
│ true credential lives in gateway, not in sandbox config       │
│ sandbox agent receives managed provider/base URL/model ref    │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Sandbox policy baseline                                      │
│ managed_inference allows inference.local for selected binaries│
└──────────────┬───────────────────────────────────────────────┘
               ▼
┌────────────────────────────┐
│ external provider / local   │
│ NVIDIA/OpenAI/vLLM/Ollama...│
└────────────────────────────┘
```

这里的设计重点是 [[agent-credential-isolation]]：sandbox 看到的是 `inference.local` 和 managed provider/model ref，真正 provider credential 由 [[OpenShell]] gateway 托管。local Ollama/vLLM 还有专用 token env，避免误用 host OpenAI key。

## 设计决策与哲学

- **命令面兼容产品语法，但不复制业务层**：public dispatcher 负责 `nemoclaw <sandbox> <action>` 到 oclif command 的转换，产品行为仍在 actions/onboard。
- **Onboard 是可恢复状态机**：resume/fresh/non-interactive、session、lock、step result 和 failure marking 都是一等流程，而不是 shell script 串联。
- **Declarative assets + host orchestrator**：`nemoclaw-blueprint/**` pin 住 sandbox image digest、OpenShell/OpenClaw 版本、inference profile、router 和 policy；TypeScript 负责消费和编排。
- **凭证由 gateway 托管**：NemoClaw 只做当前进程 env staging 与 legacy migration，新凭证不写本地明文文件。
- **网络默认最小化**：baseline policy 只开放核心 agent、managed inference 和必要服务；GitHub、messaging、package index 等走用户显式 policy preset。
- **Shields 只能 host-side 控制**：sandbox 不能自己降级或升级 shields；host 通过 privileged path 做 config lock、policy 切换和 hash seal。
- **Messaging 走 manifest compiler**：新增 channel 的主要扩展面是 manifest + hook，而不是修改 onboard 主流程。
- **本地 JSON 状态优先**：`~/.nemoclaw` registry/session 降低部署复杂度，但用 advisory lock、resume 和 recovery 补齐一致性。

## 关键组件深入解读

### Onboard 编排器

`src/lib/onboard.ts` 是复杂度中心，但它更像 coordinator：初始化运行模式、校验 sandbox 名、获取 consent、抢 lock、加载/创建 session、迁移 legacy credentials，再顺序调用 preflight/gateway/provider/sandbox/agent/policy 状态处理器。近期 git 历史显示维护方向是在保留一个端到端入口的同时，把巨型分支拆成 FSM result 和可测试状态模块。

### Messaging manifest compiler

Messaging compiler 对每个 channel manifest 做 input resolution、credential availability、enrollment/reachability hook，然后 fan out 成 credential binding、network policy、agent render、build step、state update 和 health check。Applier 接受 serializable `SandboxMessagingPlan`，说明 plan 是跨 host/OpenShell/sandbox 边界传递的 contract，而不是运行时对象。

## 相关页面

- [[agent-sandbox]]
- [[agentgateway]]
- [[agent-credential-isolation]]
- [[cloud-native-security]]
- [[vllm]]
- [[ai-agent-plugin-patterns]]
- [[NVIDIA]]
- [[OpenShell]]
- [[OpenClaw]]
- [[Hermes]]
