---
title: kgateway
tags: [entity, api-gateway, ai-gateway, kubernetes, envoy]
date: 2026-06-13
sources: [kgateway-architecture-analysis.md]
related: [[gateway-api]], [[ai-gateway]], [[agentgateway]], [[higress]], [[kubernetes]], [[mcp-gateway-tooling-map]]
---

# kgateway

kgateway 是通用 cloud-native API Gateway，并带 AI Gateway 能力。仓库核心是 Gateway API 资源、controller/deployer、Envoy xDS、plugins、policies、SDS、安全和 conformance/e2e。详见 [[src-kgateway-architecture]]。

## 架构边界

kgateway 的主线是 Kubernetes / [[gateway-api|Gateway API]] 原生通用网关，AI Gateway 是其 policy/plugin 能力分支。它不是只面向模型 API 的窄代理。

## 关键设计

- `api/v1alpha1`、`pkg/kgateway`、`pkg/xds` 负责 Gateway API 扩展、controller 和 xDS 生成。
- `pkg/plugins`、`pkg/pluginsdk` 提供扩展机制。
- `pkg/deployer` 和 `pkg/sds` 管 Envoy 部署和 Secret Discovery。
- ReferenceGrant / cross-namespace 引用治理是安全边界重点。

## 选型判断

已有 Gateway API / Envoy 体系并想统一通用 API 与 AI gateway 时看 kgateway。GenAI 专用治理看 [[ai-gateway|Envoy AI Gateway]]；产品化插件网关看 [[higress]]；agent protocol unified gateway 看 [[agentgateway]]。

