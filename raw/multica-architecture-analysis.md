# Multica 架构与设计思路分析

> 仓库：https://github.com/multica-ai/multica · 分析日期：2026-06-12 · 版本：HEAD `99afb82`（2026-06-12，Add index on "user".created_at (#4063)）· 获取方式：GitHub API 复核 HEAD + codeload tarball 源码扫描。

## 一句话定位

`multica-ai/multica` 不是新的 coding agent loop，而是 managed agents platform。它把 Claude Code、Codex、Copilot CLI、OpenClaw、OpenCode、Hermes、Gemini、Pi 等本地/云 runtime 抽成“Agent teammate”：有 workspace、agent profile、issue board、task queue、runtime daemon、autopilot、squad、skills、activity timeline 和 WebSocket progress。

## 核心架构图

```text
┌──────────────────────────── human team / board / CLI ────────────────────────┐
│ issue · assignment · comments · autopilot · squad routing                     │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ Go backend (Chi + sqlc + WebSocket)                                           │
│ auth · workspace · agents · issues · task queue · skills · integrations       │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ PostgreSQL + pgvector         │  │ daemon / runtime                            │
│ workspace state · tasks       │  │ detects CLIs · executes tasks · streams log  │
└───────────────────────────────┘  └─────────────┬──────────────────────────────┘
                                                  │
┌─────────────────────────────────────────────────▼────────────────────────────┐
│ Claude Code / Codex / Copilot CLI / OpenCode / Hermes / Gemini / Pi / Kimi    │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `server/cmd/server/**` | Go backend 入口、router、listeners、scheduler、runtime sweeper、auth scope guard。 |
| `server/internal/daemon/**`, `daemonws/**` | 本地 daemon、runtime identity/health/wakeup、WebSocket hub。 |
| `server/internal/handler/**` | agent、autopilot、issue、skill、workspace、auth 等 HTTP handler。 |
| `server/pkg/db/queries/**`, `server/migrations/**` | sqlc 查询和 100+ migration，说明产品状态模型较重。 |
| `packages/views/**`, `apps/mobile/**` | 前端 board/agents/skills/mobile 入口。 |

## 关键数据流

1. 用户或 autopilot 创建 issue，分配给 agent/squad。
2. backend 将任务入队，runtime daemon 通过 WebSocket/轮询接收并 claim/start。
3. daemon 检测本机可用 agent CLI，按 agent 配置执行任务，并把 progress/log/activity 回传。
4. 完成/失败后 backend 更新 issue/task/usage/notification，前端 board 实时展示。

## 设计决策与哲学

- 核心抽象是“agent teammate”，不是“agent framework”；因此 DB schema、权限、工作区、任务生命周期比模型调用更重要。
- 通过 daemon 接入现有 CLI，避免重写 Codex/Claude/Pi 执行 loop，但也继承各 CLI 的安全/稳定性。
- Squad/Autopilot 是调度层：前者解决人如何分派，后者解决周期性工作如何自动生成任务。
- PostgreSQL/pgvector 暗示 skills/search/knowledge 可能内建，但主路径仍是 task management。

## 与已有项目的对比

和 Codex/Pi/oh-my-pi 相比，Multica 是调度/协作外壳；和 AgentScope Runtime 相比，它不把单个 agent app 服务化，而是管一组现有 coding agents；和 [[nanobot]] 相比，它更像团队工作台，不是个人多渠道 agent 内核。

## 选型提示

- 适合深挖的问题：入口协议、状态源、工具/运行时边界、部署模型、失败恢复和安全治理。
- 不要只看 README：本页结论来自源码目录、入口文件、核心包和 GitHub 当前 HEAD 的组合扫描。
- 后续如继续深化，应补充 release/tag 变更、关键 issue/PR 和真实部署案例。
