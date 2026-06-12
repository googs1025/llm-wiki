---
title: Kubernetes Gateway API
tags: [kubernetes, networking, gateway, api]
date: 2026-06-12
sources: [agentgateway-architecture-analysis.md, gateway-api-inference-extension-architecture-analysis.md]
related: [[kubernetes]], [[istio]], [[agentgateway]], [[gateway-api-inference-extension]], [[inference-routing]]
---

# Kubernetes Gateway API

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

## 与 Ingress 的对照

| 维度 | Ingress | Gateway API |
|------|---------|-------------|
| 角色模型 | 一个资源里混合平台和应用意图 | GatewayClass / Gateway / Route 分离职责 |
| 协议覆盖 | 主要 HTTP/HTTPS | HTTP、gRPC、TCP、TLS 等资源族 |
| 扩展方式 | annotation 堆叠，controller-specific | 标准字段 + policy attachment + extension points |
| 多团队边界 | namespace / host 冲突处理弱 | `ReferenceGrant`、Route attachment 更明确 |
| 适合场景 | 简单 Web ingress | 多租户入口、mesh interop、AI inference routing |

## 主流实现位置

| 实现 | 特点 | 适合关注点 |
|------|------|------------|
| Istio | Gateway API + service mesh / HBONE / xDS 生态 | mesh 与 ingress 统一 |
| Envoy Gateway | 以 Envoy 为数据面的 Gateway API 实现 | API gateway / GenAI gateway 扩展 |
| Cilium Gateway API | eBPF datapath + Cilium 网络策略生态 | 网络、安全、L7 policy 结合 |
| Kong / NGINX Gateway Fabric | 传统 API gateway / ingress controller 演进 | 已有网关生态迁移 |
| agentgateway | 复用 Gateway API 控制面，扩展 AI/MCP/A2A backend | AI-native L7 gateway |

## GAMMA 与 Service Mesh

GAMMA（Gateway API for Mesh Management and Administration）把 Gateway API 的 Route / policy attachment 思路扩展到 service mesh 内部流量。对 AI infra 的价值是：入口流量、服务间流量、Agent 到工具/模型的出口流量可以逐渐使用同一套资源模型表达，而不是 Ingress、VirtualService、网关插件各写一套。

[[agentgateway]] 借用 [[istio]] / [[xds]] / [[hbone]] 的思路，说明 Gateway API 已经不只是“北南向入口”，也可以成为 AI gateway 控制面的公共语言。

## InferencePool 与 AI 推理调度

[[gateway-api-inference-extension]] 把推理 endpoint picking 推进 Gateway API extension 层：

- `InferencePool` 表示一组可被 gateway 选择的推理后端；
- EPP / LWEPP 作为 Endpoint Picker 参考实现；
- 下游如 [[llm-d]] 可以把 KV cache、P/D 分离、负载、端口、模型能力等信息接进 picking；
- 它解决的是“Gateway 该把这个推理请求发给哪个 endpoint”，不是 provider auth、prompt mutation 或模型本身推理。

因此 Gateway API 在 AI 场景里的位置正在上移：从普通 HTTP ingress，变成 LLM serving routing、AI gateway policy 和 mesh interop 的共同 API 层。
