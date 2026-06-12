# KServe 架构与设计思路分析

> 仓库：https://github.com/kserve/kserve · 分析日期：2026-06-12 · 版本：HEAD `ccf1d3d`（2026-06-12，fix(llmisvc): filter HTTPRoute parent status by gateway name (#5583)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

> [!note] Scope
> `semantic-router` / `kserve` 这类大仓库按 ingest-codebase 阈值缩小到源码核心、控制面、README/docs 和关键配置，跳过大资产、历史安装包和生成物。

## 一句话定位

`kserve/kserve` 是 Kubernetes 标准化 model serving 平台。仓库超过 200MB，本次缩小到 `cmd/manager/llmisvc/router/localmodel`、`pkg/apis/controller/webhook`、charts/config/docs。新近 commit 修复 LLMISvc HTTPRoute parent status 过滤，说明 Gateway API/LLM service 路线正在快速演进。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kserve/kserve` 是 Kubernetes 标准化 model serving 平台。仓库超过 200MB，本次缩小到 `cmd/… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/manager`, `pkg/controller` · `cmd/llmisvc`, `config/llmisvc`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `cmd/localmodel`, `config/localmodels`                     │  │ `pkg/apis`, `pkg/webhook`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/manager`, `pkg/controller` | 核心 controller manager。 |
| `cmd/llmisvc`, `config/llmisvc` | LLM InferenceService 相关控制面。 |
| `cmd/localmodel`, `config/localmodels` | 本地模型缓存/分发。 |
| `pkg/apis`, `pkg/webhook` | API 和 webhook。 |
| `charts/**`, `docs/**` | 安装和文档。 |

## 关键数据流

1. 用户创建 InferenceService/LLMISvc/LocalModel 资源。
2. controllers 创建 predictor/router/storage runtime 和 Gateway/HTTPRoute。
3. status/webhook 维护可用性和校验。

## 设计决策与哲学

- KServe 是标准化/成熟路线，兼容传统 ML 与 GenAI。
- LLMISvc 是向 LLM serving 专门化的新增重点。
- 仓库历史包袱大，读源码要聚焦当前 LLMISvc/localmodel/control plane。

## 与已有项目的对比

和 OME/KubeAI 相比，KServe 更成熟和标准；和 llm-d/AIBrix 相比，它是 serving platform 基座，不专门做 SOTA routing/KV 优化。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
