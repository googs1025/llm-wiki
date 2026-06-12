---
title: LoongSuite Pilot 架构与设计思路分析
tags: [architecture, coding-agent, observability, telemetry]
date: 2026-06-12
sources: [loongsuite-pilot-architecture-analysis.md]
related: [[loongsuite-pilot]], [[coding-agent-observability]], [[token-usage-observability]], [[claude-code]], [[codex]], [[claude-tap]], [[tokscale]]
---

# LoongSuite Pilot 架构与设计思路分析

> 原文：`raw/loongsuite-pilot-architecture-analysis.md` · 仓库：https://github.com/alibaba/loongsuite-pilot · 分析版本 HEAD `e936fb0`（2026-06-12，main）

## 一句话定位

[[loongsuite-pilot]] 是 Alibaba 开源的轻量多 Agent AI coding telemetry collector，用本地 daemon 自动发现 [[claude-code]]、[[codex]]、Cursor、Qoder、QoderWork 等 coding agent，部署 hook / plugin-probe，然后把本地日志、SQLite、session、trace 输入统一归一化为 `AgentActivityEntry`。它补齐的是 [[coding-agent-observability]] 里的“常驻采集管道 + 标准 schema + 多后端上报”位置，和 [[claude-tap]] 的请求 trace、[[tokscale]] 的成本统计互补。

## 核心架构图

```
┌────────────────────────────────────────────────────────────────────┐
│                      Local developer machine                        │
│                                                                    │
│  ┌──────────────┐  hook/plugin/log/sqlite/session  ┌─────────────┐ │
│  │ Coding Agents│ ───────────────────────────────▶ │ Input layer │ │
│  │ Claude/Codex │                                 │ BaseInput   │ │
│  │ Cursor/Qoder │                                 │ subclasses  │ │
│  └──────┬───────┘                                 └──────┬──────┘ │
│         │ deploy / repair hooks                         entries   │
│         ▼                                                   │      │
│  ┌───────────────────┐                                      ▼      │
│  │ DeploymentManager │   definitions/state       ┌────────────────┐│
│  │ agents.d + local  │◀────────────────────────▶ │ InputManager   ││
│  └────────┬──────────┘                            │ policy + mask  ││
│           │                                       └───────┬────────┘│
│           ▼                                               │         │
│  ┌───────────────────┐                                    ▼         │
│  │AgentDiscoverySvc  │ fs.watch + polling       ┌─────────────────┐│
│  │Idle/Starting/...  │────────────────────────▶ │ MultiFlusher    ││
│  └───────────────────┘                          │ JSONL/SLS/HTTP ││
│                                                   │ OTLP Trace     ││
│  ┌───────────────────┐                            └───────┬────────┘│
│  │ metrics/statusbar │ runtime.json / summaries           │         │
│  └───────────────────┘                                    ▼         │
└──────────────────────────────────────────────────── observability ──┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| CLI / daemon entry | 加载配置、启动 Orchestrator、注册系统/用户服务、提供 start/stop/status/rollback |
| 编排核心 | 装配 state、agent control、deployment、inputs、flushers、metrics、status bar；管理输入生命周期和统一处理链 |
| Agent 接入声明 | 用声明式 JSON 描述 detection、hook settings、events、plugin source；部署 hooks / plugin probe 并记录部署状态 |
| 输入采集层 | 用 Hook、SQLite、Session、CLI 等基类从不同 agent 本地状态增量读取 |
| 标准化与隐私 | 把 source-specific event 转为 canonical dotted keys；按 agent content policy 删除消息内容；按规则对敏感字段打码 |
| 输出层 | Fan-out 到本地 JSONL、Alibaba Cloud SLS、HTTP POST、OTLP trace；失败缓存和重试由 flusher 负责 |
| 运行健康与 UI | 写 runtime / metrics summary，支持 macOS status bar 和本地只读 dashboard |

核心边界是：agent hook 只写本地 history JSONL，Input 只负责增量读取，InputManager 才做 collector 级 content policy / mask，Flusher 只做输出。这让采集、隐私处理、输出后端可以独立演进。

## 关键数据流

```
startup
  │
  ▼
loadConfig → StateStore/AgentControl → buildFlusher
  │
  ▼
DeploymentManager.deployAll()
  │      ├─ load agents.d + agents.d.local
  │      ├─ detect installed agents
  │      └─ install hooks / plugin probes (best-effort)
  ▼
registerAllInputs()
  │      ├─ Qoder SQLite / trace / work inputs
  │      ├─ Cursor / Claude Code / Codex hook inputs
  │      └─ Wukong / file collection optional inputs
  ▼
AgentDiscoveryService
  │      ├─ fs.watch watchPaths
  │      └─ polling fallback
  ▼
Input.collect()
  │      ├─ byte offset / rowid / session cursor / snapshot dedup
  │      └─ transform raw record → AgentActivityEntry
  ▼
InputManager.handleEntries()
  │      ├─ inject user.id
  │      ├─ apply per-agent content policy
  │      └─ mask secrets
  ▼
MultiFlusher
  │      ├─ JSONL local fallback
  │      ├─ SLS AK/WebTracking
  │      ├─ HTTP batch
  │      └─ OTLP trace conversion
  ▼
local files / SLS / HTTP endpoint / OpenTelemetry backend
```

hook 类输入的热路径更窄：

```
Agent hook event
  │
  ▼
*-loongsuite-pilot-hook.sh
  │      └─ fail-open: Node/runtime/parse failure must not block agent
  ▼
*processor.mjs + agent-event-normalizer.mjs
  │
  ▼
~/.loongsuite-pilot/logs/<agent>/history/<agent>-YYYY-MM-DD.jsonl
  │
  ▼
BaseHookInput.collect()
  │      ├─ read from persisted byte offset
  │      ├─ reset offset if file truncated
  │      └─ parse line-by-line JSON
  ▼
transformHookRecord() → InputManager → Flusher
```

## 设计决策与哲学

- **常驻 collector，而不是单一 agent 插件**：Orchestrator 装配 state/control、flusher、hook deployment、input discovery、metrics/status bar，说明主产品是多 agent 观测管道，不是某个 agent 的孤立 hook。
- **声明式 agent definition + 本地覆盖目录**：`agents.d` 描述 detection、hook events、settings path 和 deploy mode；核心部署器按策略执行，新增 agent 的成本主要落在 JSON 定义和输入适配。
- **发现与部署分离**：AgentDiscoveryService 只跑状态机和 fs.watch/polling；发现新 agent 后委托 DeploymentManager 部署，发现层不理解 hook 写入细节。
- **隐私策略放在统一出口前**：InputManager 对所有 entry 统一执行 `user.id` 注入、content policy 和 secret mask，再分发给 JSONL/SLS/HTTP/OTLP，避免不同后端拿到不同隐私处理结果。
- **输出后端 fan-out，但失败隔离**：无后端时回退 JSONL；多后端通过 allSettled 并行发送，单个后端失败不会拖垮整条 pipeline。

## 与同类对比

| 维度 | [[loongsuite-pilot]] | [[claude-tap]] | [[tokscale]] |
|------|----------------------|----------------|--------------|
| 核心问题 | 多 coding agent 活动 telemetry 统一采集和上报 | 真实 API 请求/响应 trace 捕获与回放 | 多客户端 token/cost 离线统计 |
| 采集位置 | agent hooks、SQLite、本地 session/log、plugin probe | 本地 reverse/forward proxy | 本地 session 文件/数据库扫描 |
| 输出形态 | JSONL / SLS / HTTP / OTLP trace / status bar | SQLite trace + live viewer/export | TUI/JSON 报表 |
| 强项 | 常驻 daemon、声明式 agent definition、统一 schema、多后端 | 单次请求证据链和调试体验 | 成本趋势、定价、多 workspace 汇总 |

## 相关页面

- [[loongsuite-pilot]]
- [[coding-agent-observability]]
- [[token-usage-observability]]
- [[claude-tap]]
- [[tokscale]]
