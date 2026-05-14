---
title: HBONE
tags: [service-mesh, mtls, http2, transport]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[istio]], [[agentgateway]]
---

# HBONE

> Stub — 待充实

**HTTP-based Overlay Network Environment**，[[istio|Istio]] ambient mesh 引入的隧道传输协议。本质：**mTLS over HTTP/2 CONNECT**。

```
client ──TCP──▶ TLS(mTLS) handshake ──▶ HTTP/2 CONNECT to <upstream:port>
                                                │
                                                ▼
                                          tunneled application data
                                          (encrypted by outer mTLS)
```

设计目标：
- **多路复用** —— 多个上游连接共享同一条 TCP / TLS 握手成本（H2 stream）
- **可观测可路由** —— 中间节点（ztunnel / waypoint）能看到 CONNECT target 做 L4 路由
- **跨 mesh identity** —— mTLS 证书携带 SPIFFE ID，互信可基于身份而非 IP

## 在 [[agentgateway]] 中的使用

`crates/hbone/` 直接拿 Istio 的 HBONE 实现做出站隧道：
- 当 backend 是 mesh workload 时，gateway 通过 HBONE 隧道连过去
- 不是 mesh workload 时走普通 TLS / plaintext
- 这让 agentgateway 数据面可以作为 ambient mesh 的一份子，跟 ztunnel / waypoint 互通

## TODO

- [ ] 写 HBONE 跟 sidecar Envoy 直连的对比
- [ ] 写 SPIFFE / SPIRE identity 与 HBONE 证书链
- [ ] 写 HBONE 跟传统 VPN / WireGuard 隧道的对比
- [ ] 写 H2 CONNECT 在防火墙穿透上的优势
