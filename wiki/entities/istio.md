---
title: Istio
tags: [service-mesh, kubernetes, networking, cncf]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[kubernetes]], [[xds]], [[hbone]], [[agentgateway]], [[gateway-api]]
---

# Istio

> Stub — 待充实

CNCF 毕业级服务网格。控制面 → 数据面通过 [[xds|xDS]] 协议分发配置，数据面历史上是 Envoy（sidecar 模式 + 新的 ambient 模式 / ztunnel + waypoint）。包括 mTLS / 流量管理 / 可观测 / 授权策略整套能力。

## 关键技术资产被 [[agentgateway]] 复用

- **KRT collections** —— Istio 内部用于反应式建模 K8s 资源的表抽象。每个 watched resource 变成一个 collection，translator 是 collection 之间的 transform。
- **xDS Delta ADS** —— Istio 控制面分发协议，agentgateway controller 直接用同样模式给 Rust 数据面推配置
- **HBONE 隧道** —— [[hbone|HBONE]]（HTTP-based Overlay Network Environment）= mTLS over HTTP/2 CONNECT，agentgateway 数据面用 HBONE 跟 ambient mesh 的其他成员（ztunnel / waypoint）互通
- **[[gateway-api|Gateway API]] 实现** —— Istio 是 Gateway API 主要实现之一

## TODO

- [ ] 写 sidecar vs ambient 架构对比
- [ ] 写 Envoy 配置发现与 xDS resource type 完整列表
- [ ] 写 KRT 的设计哲学与 reactive 编程模型
- [ ] 写 Istio Authorization Policy 与 agentgateway 的 agpol 异同
