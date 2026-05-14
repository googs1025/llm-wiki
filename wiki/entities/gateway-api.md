---
title: Kubernetes Gateway API
tags: [kubernetes, networking, gateway, api]
date: 2026-05-14
sources: [agentgateway-architecture-analysis.md]
related: [[kubernetes]], [[istio]], [[agentgateway]]
---

# Kubernetes Gateway API

> Stub — 待充实

K8s SIG-Network 的**新一代入口 API**，取代 Ingress。设计为更具表达力、可扩展、面向角色（infrastructure provider / cluster operator / application developer 三层职责分离）。核心资源族：

| 资源 | 角色 |
|------|------|
| `GatewayClass` | infrastructure provider 注册的 Gateway 实现（类比 IngressClass） |
| `Gateway` | cluster operator 部署的 gateway 实例（绑定 IP / 证书 / 监听端口） |
| `HTTPRoute` / `GRPCRoute` / `TCPRoute` / `TLSRoute` | application developer 挂在 Gateway 上的具体路由 |
| `ListenerSet`（experimental） | 跨 Gateway 共享 listener 配置 |
| `InferencePool`（experimental） | AI 推理负载均衡（项目 wg-inference 中） |
| `ReferenceGrant` | 跨 namespace 引用授权 |

## 在 [[agentgateway]] 中的使用

agentgateway 直接复用上游 Gateway API 资源做路由声明，*不* fork、*不* 改 Gateway API 本体。扩展能力放在引用型自家 CRD：
- `AgentgatewayPolicy` 挂在 Gateway / Listener / Route 上做 CEL 策略
- `AgentgatewayBackend` 在 HTTPRoute 的 backendRef 里被引用，定义 AI / MCP / A2A 后端
- `AgentgatewayParameters` 跟 GatewayClass 的 parametersRef 关联，控制 deployer 行为

这种"主资源用上游 API，扩展用自家引用型 CRD"的模式跟 Istio Gateway API 实现是同款。

## TODO

- [ ] 写 Gateway API 跟 Ingress 的对照
- [ ] 写主流实现（Istio / Envoy Gateway / Cilium / Kong / NGINX Gateway Fabric）
- [ ] 写 GAMMA（service mesh interop）扩展
- [ ] 写 InferencePool 与 AI 推理调度
