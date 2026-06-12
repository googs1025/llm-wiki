# GitNexus 架构与设计思路分析

> 仓库：https://github.com/abhigyanpatwari/GitNexus · 分析日期：2026-06-12 · 版本：HEAD `14397dd`（2026-06-12，feat(taint): intra-procedural taint analysis (#2083) (#2164)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`abhigyanpatwari/GitNexus` 是 repo knowledge graph/Graph RAG 项目，强调浏览器端/交互式代码理解。仓库体量较大，核心包括 `gitnexus/src`、web app、shared package、Claude/Cursor plugins、PR swarm review 和 eval；最近 commit 加 intra-procedural taint analysis，说明静态分析能力在增强。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `abhigyanpatwari/GitNexus` 是 repo knowledge graph/Graph RAG 项目，强调浏览器端/交互… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `gitnexus/src` · `gitnexus-web/src`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `gitnexus-shared/src`                     │  │ `gitnexus-claude-plugin`, `gitnexus-cursor-integration`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `gitnexus/src` | 核心图谱/分析逻辑。 |
| `gitnexus-web/src` | Web UI。 |
| `gitnexus-shared/src` | 共享类型/工具。 |
| `gitnexus-claude-plugin`, `gitnexus-cursor-integration` | agent/editor 集成。 |
| `pr-swarm-review`, `eval/**` | PR review 多 agent/评估。 |

## 关键数据流

1. 代码仓库被索引为知识图谱。
2. Web/agent/plugin 查询 graph，支持 RAG/taint/review。
3. PR swarm/eval 用图谱上下文辅助审查。

## 设计决策与哲学

- 浏览器/前端交互是强信号，适合可视化理解项目。
- 静态分析与 Graph RAG 合并，区别于纯向量检索。
- 仓库集成面很宽，核心选型应看 graph build/query 和证据可追踪性。

## 与已有项目的对比

和 code-review-graph 相比，GitNexus 更产品/UI 化；和 deepwiki-open 相比，它更交互图谱，不只是文档生成。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
