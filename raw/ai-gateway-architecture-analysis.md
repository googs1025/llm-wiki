# Envoy AI Gateway 架构与设计思路分析

> 仓库：https://github.com/envoyproxy/ai-gateway · 分析日期：2026-06-12 · 版本：HEAD `9a4b02c`（2026-06-12，fix: skip empty-content assistant messages in Bedrock translator (#2191)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`envoyproxy/ai-gateway` 是 Envoy Gateway 生态的 GenAI gateway。源码包含 CRD API、controller、extproc、provider translators、backend auth、body/header mutator、rate limit、redaction、MCP proxy、metrics/tracing 和大量 data-plane/e2e tests。它解决的是 LLM/API 访问治理，不是模型 serving engine。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `envoyproxy/ai-gateway` 是 Envoy Gateway 生态的 GenAI gateway。源码包含 CRD API、c… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `api/v1alpha1`, `api/v1beta1` · `cmd/controller`, `internal/controller`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `cmd/extproc`, `internal/extproc`                     │  │ `internal/translator`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `api/v1alpha1`, `api/v1beta1` | AI Gateway CRD。 |
| `cmd/controller`, `internal/controller` | 控制面。 |
| `cmd/extproc`, `internal/extproc` | Envoy External Processing 数据面。 |
| `internal/translator` | OpenAI/Bedrock 等 provider 翻译。 |
| `internal/mcpproxy`, `ratelimit`, `redaction`, `backendauth` | MCP 代理、安全、限流和认证。 |

## 关键数据流

1. Gateway/HTTPRoute 流量进入 Envoy。
2. extproc 根据 AI Gateway 配置改写/校验/路由请求。
3. translator 处理不同 provider 协议差异，auth/ratelimit/redaction 处理治理。

## 设计决策与哲学

- 建立在 Envoy Gateway 上，复用成熟 L7 控制面。
- 把 provider protocol translation 当核心能力，最近 Bedrock translator 修复就是例子。
- MCP proxy 表明它不只管 LLM，也在扩展到 tool gateway。

## 与已有项目的对比

和 agentgateway 相比，Envoy AI Gateway 更 Envoy Gateway/CRD-first；和 Higress/kgateway 相比，它更专注 GenAI，而不是通用 API gateway。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
