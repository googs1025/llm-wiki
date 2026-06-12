# Plano 架构与设计思路分析

> 仓库：https://github.com/katanemo/plano · 分析日期：2026-06-12 · 版本：HEAD `2e38f7f`（2026-06-09，release 0.4.24 (#966)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`katanemo/plano` 是 AI-native proxy/data plane，和 agentgateway 同层但更偏 Rust data plane + CLI/config/skills。仓库含 `crates/llm_gateway`、`prompt_gateway`、`hermesllm`、CLI、配置 schema、demos 和 skills，适合补 MCP/AI Gateway tooling map。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `katanemo/plano` 是 AI-native proxy/data plane，和 agentgateway 同层但更偏 Rust … │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `crates/llm_gateway`, `prompt_gateway` · `cli/planoai`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `config/**`                     │  │ `skills/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `crates/llm_gateway`, `prompt_gateway` | 核心 Rust gateway/data plane。 |
| `cli/planoai` | CLI 运维入口。 |
| `config/**` | Envoy template、schema 和测试配置。 |
| `skills/**` | 面向 agent/部署/路由/观测的技能包。 |
| `demos/**`, `tests/**` | 集成示例和 e2e。 |

## 关键数据流

1. 用户通过 config/CLI 定义 gateway、routing、filter chains。
2. Rust data plane 处理 LLM 请求、路由、guardrails。
3. skills/demos 提供 agent orchestration 和运维入口。

## 设计决策与哲学

- 把 proxy/data plane 与 skills/docs 结合，服务 agentic ops。
- Rust 核心适合低延迟代理。
- 配置 schema 是使用体验关键。

## 与已有项目的对比

和 Envoy AI Gateway 相比，Plano 更自有 data plane/skills-first；和 agentgateway 相比，二者都可看作 agentic proxy，但生态和实现路线不同。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
