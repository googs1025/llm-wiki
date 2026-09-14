---
title: LLM 网关与路由层对比
tags: [architecture, ai-gateway, inference-routing, gateway-api, llm-serving, kubernetes]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md]
related: [[inference-routing]], [[ai-gateway]], [[llm-d-router]], [[semantic-router]], [[routellm]], [[gateway-api-inference-extension]], [[envoy-ai-gateway]], [[llm-inference]]
---

# LLM 网关与路由层对比

## 先分清四类决策

```
Client request
      │
      ▼
┌────────────────────┐
│ Edge/API governance │  auth · key · quota · rate limit · audit
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Model/ability route │  semantic · quality · cost · risk · cascade
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Serving endpoint    │  model · pool · pod · GPU · queue · KV locality
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Engine scheduling   │  batching · KV blocks · kernel · token generation
└────────────────────┘
```

## 统一架构图

```
                              ┌──────────────────────┐
                              │ Applications / Agents │
                              └──────────┬───────────┘
                                         │ OpenAI / Anthropic API
                         ┌───────────────▼────────────────┐
                         │ Tier 1: Edge / AI Gateway       │
                         │ Envoy AI Gateway / API Gateway  │
                         │ auth · provider · quota · audit │
                         └───────────────┬────────────────┘
                                         │
                         ┌───────────────▼────────────────┐
                         │ Tier 2: Model / Ability Router  │
                         │ Semantic Router / RouteLLM      │
                         │ intent · difficulty · quality  │
                         │ cost · risk · cascade          │
                         └───────────────┬────────────────┘
                                         │ model target / route recipe
                         ┌───────────────▼────────────────┐
                         │ Tier 3: K8s Inference Router    │
                         │ GIE Protocol + llm-d Router     │
                         │ EPP: filter → score → pick     │
                         │ load · KV · priority · health   │
                         └───────────────┬────────────────┘
                                         │ selected endpoint
                         ┌───────────────▼────────────────┐
                         │ InferencePool / Model Server    │
                         │ vLLM · SGLang · TRT-LLM         │
                         │ aggregated or P/D workers      │
                         └────────────────────────────────┘
```

## 项目定位

| 项目 | 决策层 | 核心输出 | Kubernetes 边界 |
|---|---|---|---|
| [[llm-d-router]] | endpoint/pod/worker | selected endpoint + routing metadata | EPP/ext-proc、Gateway API、InferencePool |
| [[semantic-router]] | model/ability/recipe | model、cascade、capability path | 可部署在 K8s，但不是 GIE 协议本身 |
| [[routellm]] | strong/weak model | cheaper 或 stronger model | SDK/OpenAI-compatible server，不是 operator |
| [[gateway-api-inference-extension]] | inference endpoint protocol | inference endpoint pick | Gateway API 的推理扩展 |
| [[envoy-ai-gateway]] | edge/provider governance | provider/model upstream | Envoy Gateway + two-tier gateway |

## 五条请求流程图

### llm-d-router

```
Gateway / Envoy
      │ ext-proc inference request
      ▼
llm-d Router EPP
      │
      ├─ resolve model / rewrite target
      ├─ filter unhealthy or incompatible endpoints
      ├─ scrape load / KV / scheduling signals
      ├─ score candidates with configured plugins
      └─ pick endpoint and return routing metadata
      ▼
Selected InferencePool endpoint
      │
      └─► model server / vLLM / SGLang / P-D path
```

### Semantic Router

```
OpenAI / Anthropic request
            │
            ▼
Semantic Router
            │ classify intent / difficulty / risk / modality
            ▼
Recipe / virtual model
   ┌────────┼──────────┐
   ▼        ▼          ▼
local   specialist   cascade / multi-model workflow
model   model        + retrieval / memory / tools / guardrails
            │
            ▼
stable response API + routing evidence
```

### RouteLLM

```
Application / OpenAI client
            │
            ▼
RouteLLM Controller / OpenAI server
            │ router score + threshold
            ├─ score below threshold ─► weak / cheaper model
            └─ score above threshold ─► strong / expensive model
            │
            ▼
provider or OpenAI-compatible endpoint
            │
            └─ evaluation: router × benchmark × quality/cost curve
```

### Gateway API Inference Extension

```
Client
  │
  ▼
Gateway API implementation
  │ HTTPRoute / inference request
  ▼
Inference Extension protocol
  │ asks Endpoint Picker for a target
  ▼
InferencePool + Endpoint Picker
  │ model-aware endpoint selection
  ▼
Inference endpoint / model server
```

### Envoy AI Gateway

```
Application
   │
   ▼
Tier One Gateway
   │ authentication · top-level route · global rate limit
   ▼
Tier Two Gateway / inference gateway
   │ fine-grained self-hosted model access
   │ optional endpoint picker / LLM-aware routing
   ├──────────────► hosted providers
   └──────────────► self-hosted model serving cluster
```

## 选型结论

- provider、key、quota、限流和审计：[[envoy-ai-gateway]]。
- 语义、风险、能力和质量-成本模型选择：[[semantic-router]] / [[routellm]]。
- KV、队列、GPU、健康和 InferencePool endpoint 选择：[[gateway-api-inference-extension]] / [[llm-d-router]]。
- 多层组合时，必须记录每一层的 route decision、模型名、endpoint、策略版本和失败原因。

## 相关页面

- [[inference-routing]]
- [[ai-gateway]]
- [[llm-inference]]
- [[src-k8s-gateway-routing-comparison]]
