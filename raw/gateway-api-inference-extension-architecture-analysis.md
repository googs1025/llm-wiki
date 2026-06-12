# Gateway API Inference Extension 架构与设计思路分析

> 仓库：https://github.com/kubernetes-sigs/gateway-api-inference-extension · 分析日期：2026-06-12 · 版本：HEAD `974d27c`（2026-06-11，lwepp: Support port-aware endpoint filtering for Data Parallelism (#2963)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`kubernetes-sigs/gateway-api-inference-extension` 是 Kubernetes SIG 路线的推理流量标准化入口。它定义 InferencePool 等 API，提供 EPP/LWEPP、client-go、conformance、benchmarking 和 Gateway API 集成，是 llm-d-router 等项目对齐的标准层。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `kubernetes-sigs/gateway-api-inference-extension` 是 Kubernetes SIG 路线的推理… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `api/v1`, `apix/**` · `cmd/epp`, `cmd/lwepp`, `pkg/epp`, `pkg/lwepp`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `client-go/**`                     │  │ `conformance/**`, `benchmarking/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `api/v1`, `apix/**` | InferencePool 和 EndpointPicker 相关 API。 |
| `cmd/epp`, `cmd/lwepp`, `pkg/epp`, `pkg/lwepp` | Endpoint Picker 实现。 |
| `client-go/**` | 生成客户端。 |
| `conformance/**`, `benchmarking/**` | 一致性与性能验证。 |
| `site-src/**` | 官方文档站点。 |

## 关键数据流

1. HTTPRoute/Gateway 指向 InferencePool。
2. EPP/LWEPP 根据 endpoint 状态、端口和模型能力选择后端。
3. conformance/benchmark 确保实现符合 Gateway API 推理扩展语义。

## 设计决策与哲学

- 把推理路由变成 Gateway API extension，而不是每个 serving 系统自定义。
- 保留 EPP 参考实现，同时让 downstream 可替换。
- 最近支持 port-aware endpoint filtering，说明 data parallelism 已进入标准关注点。

## 与已有项目的对比

和 llm-d-router 相比，它是标准/API 和参考层；和 Envoy AI Gateway 相比，它更偏 endpoint picking，不管 provider auth/cost/prompt mutation。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
