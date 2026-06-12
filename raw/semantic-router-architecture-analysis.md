# vLLM Semantic Router 架构与设计思路分析

> 仓库：https://github.com/vllm-project/semantic-router · 分析日期：2026-06-12 · 版本：HEAD `9893c2c`（2026-06-11，[Dashboard] allow first-admin registration during setup mode (#2158)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

> [!note] Scope
> `semantic-router` / `kserve` 这类大仓库按 ingest-codebase 阈值缩小到源码核心、控制面、README/docs 和关键配置，跳过大资产、历史安装包和生成物。

## 一句话定位

`vllm-project/semantic-router` 是 vLLM 生态的 system-level intelligent router，目标不是 KV cache locality，而是按请求语义/规则/模型能力做 mixture-of-models 路由。仓库超过 200MB，本次按 ingest-codebase 缩小到 `src/semantic-router`、Go/Rust bindings、config、deploy/operator、dashboard/README 等核心。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `vllm-project/semantic-router` 是 vLLM 生态的 system-level intelligent route… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `src/semantic-router`, `config/**` · `*-binding/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `deploy/**`                     │  │ `dashboard/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `src/semantic-router`, `config/**` | 语义路由主逻辑和决策配置。 |
| `*-binding/**` | Candle/ML/NLP/ONNX/OpenVINO 等加速/模型绑定。 |
| `deploy/**` | K8s/operator/helm/kserve/local 部署。 |
| `dashboard/**` | 管理界面，最近 first-admin setup 修复相关。 |
| `perf`, `bench`, `e2e` | 性能与端到端验证。 |

## 关键数据流

1. 请求进入 router。
2. router 读取 config 中 algorithm/decision/signal/knowledge base。
3. embedding/classifier/binding 产生语义信号，选择模型/endpoint。

## 设计决策与哲学

- 语义路由和 KV-aware routing 是不同维度，可叠加但不能混淆。
- 多 binding 说明它追求系统级低延迟/可部署性。
- dashboard/operator 表明它正从 library 走向平台组件。

## 与已有项目的对比

和 RouteLLM 相比，semantic-router 更工程化/系统化；和 llm-d-router 相比，它按语义/模型选择，不按 pod load/KV locality。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
