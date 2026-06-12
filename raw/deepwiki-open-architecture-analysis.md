# deepwiki-open 架构与设计思路分析

> 仓库：https://github.com/AsyncFuncAI/deepwiki-open · 分析日期：2026-06-12 · 版本：HEAD `16f35a0`（2026-06-03，Feature: Introduce LiteLLM client for multi-provider model routing (#529)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`AsyncFuncAI/deepwiki-open` 是开源 DeepWiki 风格 repo wiki generator。仓库小而清晰：Next.js UI、Python API、tools、docker-compose、LiteLLM config；最近加入 LiteLLM client，说明多 provider model routing 是当前重点。它对 llm-wiki 自身有镜像价值。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `AsyncFuncAI/deepwiki-open` 是开源 DeepWiki 风格 repo wiki generator。仓库小而清晰：N… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `src/app`, `src/components`, `src/contexts` · `api/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `api/tools/**`                     │  │ `litellm-config.yml`, `docker-compose*`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `src/app`, `src/components`, `src/contexts` | Next.js 前端。 |
| `api/**` | Python API server 和 repo/tools 逻辑。 |
| `api/tools/**` | 代码分析/检索/生成工具。 |
| `litellm-config.yml`, `docker-compose*` | 模型路由和部署。 |
| `tests/**` | API/integration/unit tests。 |

## 关键数据流

1. 用户输入 GitHub repo 或本地源码。
2. API 工具抓取/解析代码，调用 LLM 生成结构化 wiki。
3. 前端展示 wiki 并支持问答/导航。

## 设计决策与哲学

- 把 repo wiki 作为产品形态，而不是只做 search API。
- LiteLLM 抽象 provider，降低模型切换成本。
- 生成内容需要可审计证据，否则容易成为不可验证总结。

## 与已有项目的对比

和本 llm-wiki 工作流相比，deepwiki-open 自动化程度高但人工策展弱；和 code-review-graph/GitNexus 相比，它更偏文档生成，而不是交互式代码图分析。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
