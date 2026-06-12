# kagent 架构与设计思路分析

> 仓库：https://github.com/kagent-dev/kagent · 分析日期：2026-06-12 · 版本：HEAD `feb8cf9`（2026-06-12，fix(bedrock): stream events incrementally instead of buffering (#1989)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`kagent-dev/kagent` 是 cloud-native agentic AI 平台，面向 Kubernetes/DevOps 操作而不是通用 chat agent。仓库由 Go control plane、Python package/samples、Helm charts、UI、内置 tools/skills 组成，适合补 [[ai-ops]] 中“agentic workflow + MCP + K8s runtime”的路线。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kagent-dev/kagent` 是 cloud-native agentic AI 平台，面向 Kubernetes/DevOps 操作… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `go/api`, `go/core`, `go/adk` · `python/packages`, `python/samples`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `helm/**`                     │  │ `ui/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `go/api`, `go/core`, `go/adk` | Go 侧 API、核心对象和 ADK 集成。 |
| `python/packages`, `python/samples` | Python agent/tool package 和示例。 |
| `helm/**` | kagent、agents、tools 的安装分发。 |
| `ui/**` | 管理界面。 |
| `.agents/skills`, `.claude/skills`, `contrib/tools` | 技能/工具生态入口。 |

## 关键数据流

1. 用户从 UI/CLI/API 创建或调用 agent。
2. agent 通过工具/MCP/K8s API 执行 DevOps 操作。
3. Go control plane 负责状态、配置、流式事件和部署对象，Helm 安装到集群。

## 设计决策与哲学

- 按 cloud-native control plane 组织，而不是单机 CLI。
- 把 tools/skills 作为可扩展资产，适合和 MCP 网关路线结合。
- 最近 Bedrock streaming 修复说明其模型 provider 事件流是关键路径。

## 与已有项目的对比

和 `kubectl-ai` 相比，kagent 更像平台；和 `k8m`/`kubewall` 相比，它不是 dashboard，而是 agentic workflow 运行层。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
