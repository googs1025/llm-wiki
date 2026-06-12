# kubectl-ai 架构与设计思路分析

> 仓库：https://github.com/GoogleCloudPlatform/kubectl-ai · 分析日期：2026-06-12 · 版本：HEAD `08cf256`（2026-03-25，fix: register built-in tools (bash, kubectl) in MCP server mode (#643)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`GoogleCloudPlatform/kubectl-ai` 是 kubectl 入口的 K8s assistant。核心是 Go CLI/agent loop，内置 bash、kubectl、journal、sessions、sandbox 和 MCP server mode；最近 commit 特别修复 MCP server mode 下 built-in tools 注册，说明它既是交互 CLI，也是可被其他 agent 调用的 K8s tool server。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `GoogleCloudPlatform/kubectl-ai` 是 kubectl 入口的 K8s assistant。核心是 Go CLI/… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/**` · `pkg/agent`, `pkg/tools`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `pkg/mcp`                     │  │ `pkg/sessions`, `pkg/journal`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/**` | CLI 命令入口。 |
| `pkg/agent`, `pkg/tools` | agent loop 和 bash/kubectl 等工具。 |
| `pkg/mcp` | MCP server mode。 |
| `pkg/sessions`, `pkg/journal` | 会话与操作记录。 |
| `k8s/**`, `modelserving/**` | 集群部署和模型服务示例。 |

## 关键数据流

1. 用户在终端输入自然语言问题。
2. agent 选择 bash/kubectl 内置工具查询集群。
3. 结果写入 journal/session，并生成解释或下一步命令。

## 设计决策与哲学

- 把 kubectl 作为主要 UX，降低 K8s 用户迁移成本。
- MCP server mode 让它从 standalone CLI 变成其他 agent 的 K8s backend。
- 工具面相对克制，适合安全审计。

## 与已有项目的对比

和 kagent 相比更轻、更 CLI-first；和 K8s dashboard 类项目相比，它不提供完整 UI，而是把 kubectl 工作流自然语言化。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
