# RouteLLM 架构与设计思路分析

> 仓库：https://github.com/lm-sys/RouteLLM · 分析日期：2026-06-12 · 版本：HEAD `0b64fda`（2024-08-09，create /health endpoint for health checks）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`lm-sys/RouteLLM` 是较早的 LLM router serving/evaluation framework，偏成本/质量路由算法基线。仓库小，核心在 `routellm/routers`、`routellm/evals` 和 benchmarks；最近 HEAD 停在 2024-08，不应按当前活跃 infra 项同等看待。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `lm-sys/RouteLLM` 是较早的 LLM router serving/evaluation framework，偏成本/质量路由算… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `routellm/routers` · `routellm/evals`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `benchmarks/**`                     │  │ `config.example.yaml`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `routellm/routers` | 不同 routing strategy。 |
| `routellm/evals` | 评估框架。 |
| `benchmarks/**` | MT-Bench 等 benchmark。 |
| `config.example.yaml` | 服务配置。 |

## 关键数据流

1. 请求先由 router 估计简单/困难或成本/质量权衡。
2. 路由到 cheaper/stronger model。
3. eval/benchmark 计算质量、成本和延迟指标。

## 设计决策与哲学

- 算法研究价值高，生产控制面弱。
- 健康检查 commit 说明有 serving 形态，但不是 cloud-native K8s control plane。
- 适合做 semantic/model routing baseline。

## 与已有项目的对比

和 semantic-router 相比，RouteLLM 更研究/算法；和 AI Gateway 项目相比，它不负责 auth、rate limit、provider 翻译。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
