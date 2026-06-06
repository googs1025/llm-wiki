---
title: OpenShell 架构与设计思路分析
tags: [architecture, ai-agent, sandbox, security]
date: 2026-06-05
sources: [openshell-architecture-analysis.md]
related: [[OpenShell]], [[NVIDIA]], [[NemoClaw]], [[agent-sandbox]], [[agentgateway]], [[cloud-native-security]], [[agent-credential-isolation]], [[mcp]], [[vllm]]
---

# OpenShell 架构与设计思路分析

> 原文：`raw/openshell-architecture-analysis.md` · 仓库：https://github.com/NVIDIA/OpenShell · 分析版本 HEAD `97986d9`

## 一句话定位

[[OpenShell]] 是 [[NVIDIA]] 面向 autonomous AI Agent 的安全私有运行时：它不是新的 Agent framework，而是把 Agent 放进可审计、可配置、可连接、可恢复的 sandbox 里运行。它的关键手段是把 Gateway 控制面、sandbox 内 Supervisor enforcement、OPA/Z3 policy pipeline、provider credential 管理和 `inference.local` 推理路由拆成清晰边界；这也解释了它为什么能和 [[NemoClaw]]、[[agent-sandbox]]、[[agentgateway]] 互补。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ User surfaces                                                                 │
│                                                                              │
│ openshell CLI          Python SDK / future SDKs          TUI                  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │ gRPC / HTTP
                                ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway control plane                                                        │
│ crates/openshell-server                                                      │
│                                                                              │
│ - authn/authz for users and sandbox callbacks                                 │
│ - object store: sandboxes, providers, policy, settings, inference, sessions   │
│ - compute orchestration: create/delete/watch/reconcile/resume                 │
│ - provider credential and inference bundle resolution                         │
│ - supervisor session registry and relay coordination                          │
│                                                                              │
│              ┌─────────────────────┐        ┌────────────────────────────┐   │
│              │ SQLite / Postgres   │        │ provider / policy objects  │   │
│              └─────────────────────┘        └────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────────────────────────┘
               │ compute driver contract
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Runtime integrations                                                          │
│                                                                              │
│ Docker driver     Podman driver     Kubernetes driver     VM / libkrun driver │
│                                                                              │
│ Each driver provisions workload identity, callback material, image/template,  │
│ supervisor binary, initial command, runtime env, and lifecycle events.        │
└──────────────┬───────────────────────────────────────────────────────────────┘
               │ starts sandbox workload
               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sandbox data plane                                                            │
│ crates/openshell-sandbox                                                      │
│                                                                              │
│ ┌──────────────────────┐        ┌─────────────────────────────────────────┐  │
│ │ Supervisor            │        │ Restricted agent child                  │  │
│ │ - starts as root      │ spawn  │ - non-root user                         │  │
│ │ - loads policy/config ├───────▶│ - filesystem/process/network limits     │  │
│ │ - injects credentials │        │ - ordinary egress forced through proxy  │  │
│ │ - starts proxy + SSH  │        └──────────────────┬──────────────────────┘  │
│ │ - opens outbound      │                           │ CONNECT / HTTP          │
│ │   session to gateway  │◀──── relay/config/logs ───┘                         │
│ └──────────┬───────────┘                                                      │
│            │                                                                  │
│            ▼                                                                  │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ Policy proxy                                                             │ │
│ │ - bind process identity via /proc/net/tcp + binary hash                  │ │
│ │ - evaluate OPA network action                                            │ │
│ │ - reject SSRF/internal destinations unless explicitly allowed            │ │
│ │ - terminate TLS for L7 inspection and credential rewrite where enabled   │ │
│ │ - intercept https://inference.local and route via openshell-router       │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 用户入口 | CLI/SDK/TUI 解析 gateway context、sandbox name、auth token，把用户意图变成 Gateway API 调用。 |
| Gateway 控制面 | API、认证、持久状态、policy/settings/provider/inference 配置、compute orchestration、relay 协调。 |
| 持久化 | protobuf object store，SQLite/Postgres 后端，`resource_version` CAS；生产写路径必须显式使用 `WriteCondition` 或 `update_message_cas`。 |
| Compute runtime | 抽象 Docker/Podman/Kubernetes/VM driver；负责 create/delete/watch/reconcile/startup resume。 |
| Sandbox supervisor | sandbox 内安全边界：加载 policy/settings、准备 filesystem/process/netns/TLS、启动 proxy/SSH、拉取 provider env、启动 agent child、热更新 policy。 |
| Policy proxy | 用 OPA 做 L4/L7 网络决策，用 `/proc/net/tcp` 绑定调用进程身份，做 SSRF 防护、TLS/L7 inspection、凭证 rewrite、`inference.local` 路由。 |
| Provider / inference | provider discovery、credential 注入、OpenAI/Anthropic/NVIDIA 等模型路由；sandbox 内 `inference.local` 不走普通 OPA network policy。 |

OpenShell 的分层约束很强：Gateway owns desired state，Supervisor owns runtime enforcement。Gateway 不做 agent egress 的 per-request 裁决，真正的 [[cloud-native-security|安全]] enforcement 放在 sandbox 内，那里能看到进程身份、文件系统、网络命名空间、TLS 流和 runtime credentials。

## 关键数据流

```
┌──────────────┐
│ openshell CLI │
└──────┬───────┘
       │ CreateSandbox(name/spec/policy/providers)
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway gRPC handler                                                         │
│ - validate spec/labels/providers                                             │
│ - fill default image                                                          │
│ - ensure sandbox process identity + validate policy safety                    │
│ - allocate UUID/name and set phase=Provisioning                               │
│ - optionally mint gateway sandbox JWT                                         │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ ComputeRuntime::create_sandbox
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Gateway compute runtime                                                      │
│ - update in-memory sandbox index                                             │
│ - persist Sandbox with WriteCondition::MustCreate                             │
│ - call selected compute driver                                                │
│ - rollback store/index when driver creation fails                             │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ driver provisions workload
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Docker / Podman / Kubernetes / VM                                            │
│ - inject gateway callback, identity/token material, supervisor, env, command  │
│ - report lifecycle through watch stream / reconciliation                      │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ starts openshell-sandbox
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Sandbox supervisor                                                           │
│ - load policy and settings                                                    │
│ - fetch provider env from gateway                                             │
│ - prepare filesystem, process limits, netns, seccomp, TLS CA                  │
│ - start policy proxy and SSH server                                           │
│ - open outbound ConnectSupervisor session                                     │
│ - spawn restricted agent child                                                │
└──────┬───────────────────────────────────────────────────────────────────────┘
       │ ordinary egress / exec / file sync / logs
       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Policy proxy + supervisor relay                                              │
│ - CONNECT denied: OCSF log + DenialEvent → gateway policy proposal pipeline   │
│ - CONNECT allowed: SSRF check → optional TLS/L7 inspection → upstream         │
│ - inference.local: TLS terminate → parse inference API → openshell-router     │
│ - gateway connect/exec: GatewayMessage::RelayOpen → reverse RelayStream       │
└──────────────────────────────────────────────────────────────────────────────┘
```

创建路径体现了 OpenShell 的一致性优先：Gateway 先验证 spec/policy、生成 sandbox identity 和 phase，再由 compute runtime 以 `MustCreate` 写入 store，随后才调用具体 driver；driver 失败时会回滚 store/index，避免留下“半创建”的 sandbox。Supervisor 启动则是另一条安全 pipeline：加载 policy/OPA、拉 provider env、准备 filesystem/netns/seccomp/TLS、启动 proxy/SSH、建立 outbound session，最后才 spawn restricted agent child。

## 设计决策与哲学

- **控制面和 enforcement 分离**：Gateway 存储和分发策略，但请求时裁决放在 sandbox 内 Supervisor/proxy/kernel controls，因为那里能绑定 binary identity、TLS/L7 和 runtime credentials。
- **Supervisor 主动连 Gateway**：sandbox 通过 outbound `ConnectSupervisor` 持有 live session，Gateway 的 connect/exec/file sync 通过 relay 协调，不要求每种 runtime 暴露可直连地址。
- **driver 薄、语义厚**：Docker/Podman/Kubernetes/VM driver 只翻译平台操作；sandbox lifecycle、phase、policy/settings/provider/inference 是 OpenShell 自己的语义层。
- **持久状态按对象存储 + CAS**：状态对象统一进 protobuf object store，生产写路径通过 CAS 或 MustCreate，降低并发 Gateway handler/reconciler 互相覆盖的风险。
- **网络策略绑定进程身份**：proxy 通过 `/proc/net/tcp` 解析 socket owner，把 binary path/hash/ancestor/cmdline 放进 OPA input，避免一个 sandbox 内所有进程共享同一网络权限。
- **推理路由作为特殊本地能力**：`https://inference.local` 由 sandbox proxy TLS terminate 并转给 `openshell-router`，避免 agent 直接持有 provider credentials 访问模型端点；这和 [[agent-credential-isolation]] 的思想一致。
- **policy proposal 默认人工审批**：denial 可以生成 draft policy chunk，但 Gateway 会用 Z3 prover 检查 policy delta；只有显式 auto 模式且 prover delta 为空才自动批准。

## 关键组件深入解读

### Gateway Compute Runtime

`ComputeRuntime` 是 Gateway 对 sandbox lifecycle 的核心封装。它把 Docker、Kubernetes、Podman、remote VM 都收敛成同一个 driver trait，Gateway 层只关心 create/delete/list/watch/validate。创建路径先持久化再调用 driver，失败回滚；删除路径先 CAS 设置 `Deleting`，清理 sandbox-owned records，再调用 driver delete。watch/reconcile 是长期后台任务：watch loop 应用 driver event，reconcile loop 定期比对 store 与 backend，发现 backend 缺失就走 orphan pruning。

近期 HEAD `97986d9` 正好改了 startup resume：legacy 或未初始化 sandbox row 会 decode 成 proto 默认 `Unspecified` phase，之前 resume sweep 会跳过它，导致 Gateway 重启后既不恢复也不报错；最新修复把 `Unspecified` 视为应当运行，backend 存在则 resume，不存在则 mark Error。

### Supervisor Relay 与 Sandbox Proxy

OpenShell 的 connect/exec/file sync 不走 Gateway 直接拨 sandbox，而是由 Supervisor 先向 Gateway 建立 gRPC session。Gateway 想打开 relay 时，先等待 session，登记 pending channel，再向 Supervisor 发 `RelayOpen`；Supervisor 用 `RelayStream` 首帧 claim channel。这个顺序避免反向连接先到而 Gateway 还没有等待者的竞态。

Proxy 是数据面的核心：先解析 CONNECT，`inference.local:443` 进入 inference interception；其他目标先做进程身份绑定和 OPA policy evaluation，再做 SSRF 防护、TLS/L7 inspection、credential rewrite 或 raw relay。L7 和 inference 都在 L4 allow 之后发生，`tls: skip` 则显式退回 raw tunnel。

## 相关页面

- [[NemoClaw]]
- [[agent-sandbox]]
- [[agentgateway]]
- [[cloud-native-security]]
- [[agent-credential-isolation]]
- [[mcp]]
- [[vllm]]
