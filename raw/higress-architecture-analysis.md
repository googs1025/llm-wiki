# Higress 架构与设计思路分析

> 仓库：https://github.com/higress-group/higress · 分析日期：2026-06-12 · 版本：HEAD `2897c1e`（2026-06-07，feat(model-router): add keepOriginalModelName option to preserve full model name (#3916)）· 获取方式：GitHub API 复核 HEAD + tarball 源码扫描。

## 一句话定位

`higress-group/higress` 是阿里系 AI Native API Gateway，基于 Envoy/Istio 控制面和多语言 WASM plugins。P1 中它的价值是 AI gateway/模型路由/凭据治理背景，尤其和 HiClaw 的凭据托管、MCP/LLM 网关能力相关。

## 核心架构图

```text
┌──────────────────────────── user / API surface ──────────────────────────────┐
│ `higress-group/higress` 是阿里系 AI Native API Gateway，基于 Envoy/Istio 控制面和多语… │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ core implementation: `cmd/higress`, `pkg/**` · `api/**`, `client/**`                                    │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ `plugins/**`                     │  │ `istio/**`, `envoy/**`   │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ selected value: routing / serving / dashboard / graph layer for current wiki  │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `cmd/higress`, `pkg/**` | Higress 控制面与网关逻辑。 |
| `api/**`, `client/**` | API 与客户端。 |
| `plugins/**` | WASM 插件：Go/Rust/C++/AssemblyScript。 |
| `istio/**`, `envoy/**` | 上游控制面/数据面依赖。 |
| `registry/**` | Nacos/Eureka/Consul 等服务发现。 |

## 关键数据流

1. 用户配置 route/model-router/plugin。
2. 控制面生成 Envoy/Istio 配置并下发。
3. WASM 插件在数据面处理 AI auth、model route、MCP/HTTP 策略。

## 设计决策与哲学

- 插件化和服务发现能力强，适合传统 API gateway + AI gateway 融合。
- model-router 保留原始模型名选项说明多 provider/model 映射是活跃问题。
- 仓库较大，应聚焦 plugin/model-router/control plane，不必全读 Istio vendor。

## 与已有项目的对比

和 kgateway 相比，Higress 更偏 API gateway 产品和插件生态；和 Envoy AI Gateway 相比，范围更宽但 GenAI 专注度较低。

## 选型提示

- 本页把 P1 backlog 从 GitHub metadata snapshot 升级为源码级架构页。
- 后续深挖时应继续补 release/tag、真实部署案例和关键 issue/PR。
