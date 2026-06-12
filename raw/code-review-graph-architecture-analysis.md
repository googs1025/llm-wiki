# code-review-graph 架构与设计思路分析

> 仓库：https://github.com/tirth8205/code-review-graph · 分析日期：2026-06-12 · 版本：HEAD `b72413c`（2026-06-10，docs: fix daemon logs flag names in cli docstring）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`tirth8205/code-review-graph` 是本地优先 code intelligence graph，目标是给 MCP/CLI/coding agent 提供结构化代码上下文，尤其服务 code review、delta review、debug/refactor。仓库有 Python core、tools、VSCode extension、skills、docs/tests。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `tirth8205/code-review-graph` 是本地优先 code intelligence graph，目标是给 MCP/CLI… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `code_review_graph/**` · `code_review_graph/tools/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `skills/**`                     │  │ `code-review-graph-vscode/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `code_review_graph/**` | Python 核心图构建/查询。 |
| `code_review_graph/tools/**` | CLI/MCP 工具。 |
| `skills/**` | build graph、review changes、review PR、debug issue 等技能。 |
| `code-review-graph-vscode/**` | VSCode extension。 |
| `tests/fixtures`, `docs` | 测试和说明。 |

## 关键数据流

1. 本地仓库被解析成代码图。
2. agent/CLI/MCP 根据任务查询相关节点、边、diff 或 review context。
3. 技能把常见 review/refactor 流程固化为 agent instructions。

## 设计决策与哲学

- local-first 保护代码隐私，也减少服务端依赖。
- 从 vector search 升级到 code graph，适合补 code RAG 地图。
- skills 与 MCP tools 并存，说明它面向 coding agent 工作流。

## 与已有项目的对比

和 Claude Context/memsearch 相比，它更图谱化；和 deepwiki-open 相比，它服务交互式 review，不是生成静态 wiki。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
