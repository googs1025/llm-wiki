---
title: xDS
tags: [service-mesh, configuration, protocol, grpc]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[istio]], [[agentgateway]]
---

# xDS

> Stub — 待充实

Envoy 起源、Istio 推广的 **配置发现协议族**。"x" 是通配符，常见类型：

| Type | 含义 |
|------|------|
| LDS | Listener Discovery Service |
| RDS | Route Discovery Service |
| CDS | Cluster Discovery Service |
| EDS | Endpoint Discovery Service |
| SDS | Secret Discovery Service |
| ADS | Aggregated Discovery Service（把上面所有的多路复用在一个 stream） |

两种同步模式：
- **SotW (State of the World)** —— 每次全量推送
- **Delta** —— 增量推送（resource_names_subscribe / unsubscribe）

## 在 [[agentgateway]] 中的使用

agentgateway controller (Go) 通过 gRPC 实现 **ADS server**，*只用* Delta 模式（不用 SotW 增量），减少全量同步开销。Rust 数据面订阅两个 type URL：
- `istio.workload.Address` —— 兼容 [[istio|Istio]] ambient mesh 的 workload / service 发现
- `agentgateway.dev.resource.Resource` —— 主资源 oneof，9 个变体（Bind / Listener / Route / TCPRoute / Backend / Policy / Workload / Service / RouteGroup）

**单连接复用**而不是每种资源一个 stream，这是 ADS 的核心收益。

## TODO

- [ ] 写 xDS protocol state machine（initial request → response → ACK / NACK）
- [ ] 写 Delta xDS 的 resource_names_subscribe 协议细节
- [ ] 写 SotW vs Delta 取舍（小规模偏 SotW 简单，大规模必须 Delta）
- [ ] 写常见 xDS 实现库（go-control-plane / rust ts-rs / envoy）
