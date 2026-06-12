# LoongSuite Pilot 架构与设计思路分析

> 仓库：https://github.com/alibaba/loongsuite-pilot · 分析日期：2026-06-12 · 版本：HEAD `e936fb0`（2026-06-12，main）

## 一句话定位

LoongSuite Pilot 是 Alibaba 开源的轻量多 Agent AI coding telemetry collector，用本地 daemon 自动发现 Claude Code、Codex、Cursor、Qoder、QoderWork 等 coding agent，部署 hook / plugin-probe，然后把本地日志、SQLite、session、trace 输入统一归一化为 `AgentActivityEntry`。它的价值不是执行任务，而是把多种 coding agent 的请求、工具调用、token、trace、运行健康和输出链路接到 JSONL、SLS、HTTP、OTLP 这类可观测后端。

这使它与 claude-tap / Tokscale 形成互补：claude-tap 偏“抓真实请求与流”，Tokscale 偏“离线 token/cost 统计”，LoongSuite Pilot 偏“常驻多 Agent 采集管道 + 标准化 schema + 多后端上报”。

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| CLI / daemon entry | `src/index.ts`, `scripts/loongsuite-pilot.sh`, `deploy/*` | 加载配置、启动 Orchestrator、注册系统/用户服务、提供 start/stop/status/rollback |
| 编排核心 | `src/core/orchestrator.ts`, `src/core/config-loader.ts`, `src/core/input-manager.ts`, `src/core/agent-discovery-service.ts` | 装配 state、agent control、deployment、inputs、flushers、metrics、status bar；管理输入生命周期和统一处理链 |
| Agent 接入声明 | `agents.d/*.json`, `src/deployment/*` | 用声明式 JSON 描述 detection、hook settings、events、plugin source；部署 hooks / plugin probe 并记录部署状态 |
| 输入采集层 | `src/inputs/base/*`, `src/inputs/*` | 用 `BaseHookInput`、`BaseSqliteInput`、`BaseSessionInput`、`BaseCliForwarder` 等模式从不同 agent 本地状态增量读取 |
| 标准化与隐私 | `src/normalization/*`, `src/mask/*`, `assets/hooks/agent-event-normalizer.mjs` | 把 source-specific event 转为 canonical dotted keys；按 agent content policy 删除消息内容；按规则对敏感字段打码 |
| 输出层 | `src/flushers/*` | Fan-out 到本地 JSONL、Alibaba Cloud SLS、HTTP POST、OTLP trace；失败缓存和重试由 flusher 负责 |
| 运行健康与 UI | `src/metrics/*`, `src/status-bar/*`, `app/macos-status-bar/*`, `scripts/serve-loongsuite-pilot-monitor.mjs` | 写 runtime / metrics summary，支持 macOS status bar 和本地只读 dashboard |
| 测试与验证 | `tests/*`, `docs/modules/*`, `assets/skills/*` | 用模块文档、schema fixture、E2E、性能测试和诊断 skill 约束 collector 行为 |

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

错误处理策略偏“采集服务不拖累 agent”：hook processor fail-open；DeploymentManager 部署失败按 agent 记录错误但继续其他 agent；MultiFlusher 用 `Promise.allSettled`，单个后端失败不影响其他输出；SLS / HTTP 有重试和失败日志。

## 设计决策与哲学

- **常驻 collector，而不是单一 agent 插件**：`Orchestrator.start()` 先初始化 state/control，再构建 flusher、部署 agent hook、注册 input、启动 discovery、metrics 和 status bar（`src/core/orchestrator.ts:115-238`）。这说明项目把“多 agent 观测管道”作为主产品，而不是给某个 agent 写一个孤立 hook。
- **声明式 agent definition + 本地覆盖目录**：`DeploymentManager` 从内置 `agents.d` 和用户 `agents.d.local` 加载定义，并按 `deployMode` 选择 hook 或 plugin-probe 策略（`src/deployment/deployment-manager.ts:48-55`, `100-150`）。这让新增 agent 的成本主要落在 JSON 定义和输入适配，而不是改编排核心。
- **发现与部署分离**：`AgentDiscoveryService` 只处理 `AgentDetectionEntry` 状态机和 fs.watch/polling（`src/core/agent-discovery-service.ts:40-116`），而 `buildDeployDetectionEntries()` 在发现新 agent 时委托 `DeploymentManager.deploySingle()`（`src/core/orchestrator.ts:289-315`）。发现层不需要知道 hook 的写入细节。
- **多采集策略共享统一生命周期**：`BaseInput` 固定 `start → onStart → runCycle → setInterval → stop`，具体策略由 Hook/SQLite/Session/CLI 等基类实现；`BaseHookInput` 用每日文件 + 持久 byte offset 增量读取，并处理文件截断恢复（`src/inputs/base/base-hook-input.ts:39-89`）。这比每个 agent 各写一套采集循环更容易控制幂等和恢复。
- **隐私策略放在统一出口前**：`InputManager.handleEntries()` 对所有 entry 先注入 `user.id`，再执行 `applyAgentContentPolicy()` 和 `maskAgentActivityEntry()`，最后才 dispatch 到 flusher（`src/core/input-manager.ts:176-210`）。这保证 JSONL、SLS、HTTP、OTLP 拿到的是同一份已处理数据。
- **输出后端 fan-out，但失败隔离**：`buildFlusher()` 支持 SLS、JSONL、HTTP、OTLP trace，并在没有任何后端时回退到本地 JSONL（`src/core/orchestrator.ts:337-382`）；`MultiFlusher` 用 allSettled 并行发送，避免一个后端拖垮整条 pipeline。
- **本地可观测不进入采集热路径**：metrics writer、status bar、dashboard 都读本地 runtime/summary/output 文件；即使 status bar 启动失败也只是 warn，不影响 daemon（`src/core/orchestrator.ts:216-231`）。这适合个人开发机长期驻留。

## 关键组件深入解读

### Orchestrator（`src/core/orchestrator.ts`）

Orchestrator 是一个生命周期装配器，不直接解析 agent 日志。它的 `start()` 顺序很明确：创建数据目录；加载 `StateStore` 和 `AgentControlManager`；构建 flusher；初始化 `InputManager`、`AlarmManager` 和 mask/content policy；用 `DeploymentManager.deployAll()` 部署 hook/plugin；注册所有内置 inputs；把 input detection 和 deployment detection 合并给 `AgentDiscoveryService`；最后启动 retention、watchdog、file collection、metrics/status bar。

这个顺序体现了两个设计点。第一，hook 部署在 input 启动之前做，避免 input 监听不存在的 history 目录。第二，deployment detection 和 input detection 都用同一种 `AgentDetectionEntry` 抽象，所以“发现 agent 后启动 input”和“发现 agent 后部署 hook”可以共享 discovery 状态机。

### InputManager（`src/core/input-manager.ts`）

InputManager 是所有输入的统一出口。它注册 `BaseInput` 后监听 `entries` 事件，维护每个 input 的 in/out counter，然后在 `handleEntries()` 里做三件横切处理：`user.id` 注入、content policy、secret mask。它不关心 entry 来自 hook、SQLite 还是 session 文件，也不关心输出到 SLS 还是 JSONL。

这个位置是隐私边界：hook processor 可能已做 best-effort filtering，但 collector 侧仍权威地执行一遍。这样即便某个 agent processor 漏掉消息字段，进入 flusher 前仍有统一的删除/打码机会。

### DeploymentManager + agents.d

`agents.d/codex.json` 展示了项目的声明式接入模型：检测路径是 `~/.codex`，hook settings 写入 `~/.codex/hooks.json`，事件覆盖 SessionStart / UserPromptSubmit / PreToolUse / PostToolUse / Stop，hook command 指向 `$PILOT_DATA/hooks/codex-loongsuite-pilot-hook.sh`，并带 `trustToml` 写入策略。这让 Codex 接入由 definition 描述，DeploymentManager 只负责检测、判断是否需要部署、调用策略和更新 `deployed-agents.json`。

### BaseHookInput

hook 输入的稳定性主要靠 byte offset checkpoint。`BaseHookInput.collect()` 每轮只读取今天的 `<prefix>-YYYY-MM-DD.jsonl` 从上次 offset 到当前文件大小的增量，读取后立刻把 `lastFile/lastOffset` 写入 state。若文件因重装或轮转被截断，记录 offset 大于文件大小时重置为 0。这是典型“本地 append-only log + checkpoint”的采集形态。

## 与同类对比

| 维度 | LoongSuite Pilot | claude-tap | Tokscale |
|------|------------------|------------|----------|
| 核心问题 | 多 coding agent 活动 telemetry 统一采集和上报 | 真实 API 请求/响应 trace 捕获与回放 | 多客户端 token/cost 离线统计 |
| 采集位置 | agent hooks、SQLite、本地 session/log、plugin probe | 本地 reverse/forward proxy | 本地 session 文件/数据库扫描 |
| 输出形态 | JSONL / SLS / HTTP / OTLP trace / status bar | SQLite trace + live viewer/export | TUI/JSON 报表 |
| 执行任务 | 不执行 | 不执行 | 不执行 |
| 强项 | 常驻 daemon、声明式 agent definition、统一 schema、多后端 | 单次请求证据链和调试体验 | 成本趋势、定价、多 workspace 汇总 |
| 主要代价 | 需要部署 hooks/服务，采集面更宽，隐私配置更重要 | 需要代理流量，覆盖范围取决于代理链路 | 依赖各 agent 本地数据格式，实时性较弱 |

## 性能 / 资源开销

仓库没有公开基准数据。源码层面可以看到几个资源控制点：`BaseInput` 默认轮询间隔 30s，`AgentDiscoveryService` 默认全局轮询 5 分钟并优先 fs.watch，SLS 默认 batch size 20 / flush interval 2s，monitor/dashboard 是可选旁路。项目更像“低频本地守护进程 + 批量上报”，不是高吞吐服务端数据平面。

## 安全模型

主要攻击面是本地 hook 写入、日志内容隐私、云端上报凭据和 dashboard 暴露。项目采用的边界包括：

- hook 脚本必须 fail-open，避免监控工具阻塞 coding agent；
- message content capture 可按 agent 关闭，collector 侧统一删除高敏字段；
- mask 模块在统一分发前扫描 API key、private key、数据库 URL 等；
- SLS 支持 endpoint 级 redaction，和 collector mask 共存；
- dashboard 默认本机监听，status bar/monitor 不应进入采集热路径；
- `agents.d.local` 能扩展定义，但也意味着本地配置目录需要被视为可信输入。

选型上，LoongSuite Pilot 适合长期运行和团队/个人本地 telemetry 汇总；如果只需要临时抓一次请求细节，claude-tap 更轻；如果只需要离线估算成本，Tokscale 更直接。
