# Tokscale 架构与设计思路分析

> 仓库：https://github.com/junhoyeo/tokscale · 分析日期：2026-06-12 · 版本：HEAD `aebe4ea`（2026-06-10）

## 一句话定位

Rust 实现的 AI token usage analytics 工具，从 Claude Code、Codex、OpenCode、Pi、Cursor、Gemini 等本地 session 文件/数据库中解析 usage，做并行扫描、归一化、成本定价和 TUI/JSON/报表展示。它是“本地账单与行为计量层”，不是 agent 执行器。

## 分析范围

仓库 506 个文件；分析覆盖 Rust core/CLI，未展开 npm wrapper/frontend package 的发布细节。 本次使用 GitHub API 元数据和默认分支 tarball 重新拉取源码，而不是只从既有文章或 star snapshot 推断。

## 核心架构图

```
┌──────────── Local Agent Data ────────────┐
│ ~/.claude  ~/.codex  OpenCode DB  ...    │
└──────────────┬──────────────────────────┘
               │ paths + scanner settings
               v
┌──────────────────────────────────────────┐
│ Scanner (walkdir + rayon)                │
│ files[], opencode_dbs, hermes_db, ...    │
└──────────────┬──────────────────────────┘
               │ per-client parser
               v
┌──────────────────────────────────────────┐
│ UnifiedMessage / sessionize / workspace  │
└──────────────┬──────────────────────────┘
               │ parallel aggregation
               v
┌──────────────────────┐   ┌────────────────────────┐
│ Daily/session totals  │<──│ PricingService datasets │
│ model/client/provider │   │ custom + public sources │
└──────────────┬───────┘   └────────────────────────┘
               v
┌──────────────────────────────────────────┐
│ CLI table / JSON / TUI / graph frontend   │
└──────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|------|------|------|
| CLI/TUI | crates/tokscale-cli/src/main.rs, tui/* | 定义 models/monthly/hourly/pricing/clients/login 等命令和交互式 TUI。 |
| 扫描器 | crates/tokscale-core/src/scanner.rs, clients.rs, paths.rs | 发现不同 agent 的 session 文件、SQLite DB、额外 scan path，并做并行文件遍历。 |
| Parser/session 模型 | sessions/*.rs, parser.rs, sessionize.rs | 把各 agent 特有 JSONL/DB 归一成 UnifiedMessage、session、workspace、time metrics。 |
| 聚合器 | aggregator.rs, lib.rs | 按日期/session/client/model/provider/workspace 做 rayon map-reduce 聚合。 |
| 定价服务 | pricing/* | 组合 custom/LiteLLM/OpenRouter/models.dev/Cursor override，给模型 usage 估价。 |

这套分层的关键是：入口层负责交互和配置，核心层负责稳定的领域模型或控制循环，适配层吸收外部系统差异。选型时优先看这个项目把复杂性放在哪里：CLI 插件类项目通常把复杂性放在状态/进程管理，Kubernetes/GPU 项目则把复杂性放在 reconcile、scheduler、kubelet/plugin 和硬件状态同步。

## 关键数据流

```
tokscale models --group-by client,model
  │
  ├─ CLI parses client/date/home flags and scanner settings
  │
  ├─ scanner discovers local JSONL/SQLite session sources in parallel
  │
  ├─ sessions/<client>.rs normalizes usage into UnifiedMessage
  │
  ├─ aggregator folds messages into daily/session/model totals
  │
  ├─ PricingService resolves model price with fallbacks/overrides
  │
  └─ CLI/TUI renders table, JSON, cache, contribution graph
```

错误与回退路径主要来自三个位置：外部依赖不可用、状态持久化与真实运行状态不一致、以及上游 API/平台能力变化。源码中通常通过 allowlist、checkpoint、health check、fallback manager、job state 或 controller condition 暴露这些异常，而不是把异常吞掉。

## 设计决策与哲学

- **先归一消息，再做聚合**：各 agent parser 吸收格式差异，后续 group-by 和成本计算只依赖 UnifiedMessage/TokenBreakdown。
- **并行扫描与聚合是核心性能假设**：`scanner.rs` 和 `aggregator.rs` 使用 walkdir/rayon，适合大规模本地 session 历史。
- **定价采用多源 fallback**：`PricingService` 组合 custom、LiteLLM、OpenRouter、models.dev 和 Cursor override，承认模型 ID 演进很快。

## 关键组件深入解读

### 核心入口与状态层

Tokscale 的入口层并不只是命令包装：它承担了“把用户意图变成内部状态机输入”的职责。对 coding-agent 工具来说，这通常意味着解析 slash command/CLI flag、定位 workspace、维护 job/session state；对 Kubernetes GPU 项目来说，这意味着读取 CRD/Pod/ResourceClaim、启动 informer/controller 或 kubelet plugin，然后把外部对象转成内部 reconcile/resource manager 状态。

### 适配层与边界

这个项目最值得关注的是适配边界：它既要保留上游系统的原生语义，又要把差异归一给自己的核心层。代码中的 adapter、resource manager、provider proxy、viewer/export、CDI handler、platform plugin 等目录就是这些边界的体现。边界做得越薄，项目越适合作为基础设施组件；边界做得越厚，项目通常提供更完整的产品体验，但也更容易绑定具体平台。

## 与同类对比

| 维度 | Tokscale | 同类 A | 同类 B |
|------|------|------|------|
| 定位 | usage/cost analytics | claude-tap: request trace | cc-connect: remote control bridge |
| 数据来源 | session 文件/DB | HTTP/SSE/WS 流量 | 聊天平台消息和 agent stdout |
| 输出 | 成本/模型/时间报表 | 上下文证据和 diff | 聊天回复和任务执行 |

## 性能 / 资源开销

本次未跑基准测试。可从源码结构推断：CLI/trace/analytics 项目主要开销在本地文件扫描、代理转发、SQLite 写入和 viewer 渲染；Kubernetes/GPU 项目主要开销在 informer cache、controller reconcile、device health check、NVML/CDI 查询和 DaemonSet/sidecar 常驻资源。

## 安全模型

安全边界取决于项目类型：coding-agent bridge/插件类项目直接连接本地工作区、agent 凭证和外部消息/插件入口，应重点审计 command execution、token/job state、trace 数据和聊天平台 allowlist；GPU/Kubernetes 项目则应重点审计 webhook 权限、CRD validation、RBAC、privileged DaemonSet、hostPath、device node 暴露和 checkpoint/annotation 篡改。
