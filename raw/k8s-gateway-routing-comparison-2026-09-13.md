# LLM 网关与路由层对比

> 分析日期：2026-09-13 · 资料范围：llm-d-router、vLLM Semantic Router、RouteLLM、Gateway API Inference Extension、Envoy AI Gateway 的 README/官方文档

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

Envoy AI Gateway 主要在第一层，也可以承接第二层的 provider/traffic routing；Semantic Router 与 RouteLLM 主要在第二层；Gateway API Inference Extension 定义第三层的 Kubernetes inference endpoint picking 协议；llm-d-router 是第三层的生产化智能实现，并把 KV、load、priority、model rewrite 等信号注入数据面。

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

## 项目定位与能力矩阵

| 项目 | 决策层 | 核心输入 | 输出 | Kubernetes 关系 |
|---|---|---|---|---|
| llm-d-router | endpoint/pod/worker | InferencePool、KV locality、负载、priority、模型重写 | selected endpoint + request policy | EPP/ext-proc、Gateway API、InferencePool |
| Semantic Router | model/ability/recipe | intent、difficulty、context、modality、identity、risk、system state | model/cascade/recipe/capability path | 可部署在 K8s，但不是 GIE 协议本身 |
| RouteLLM | strong/weak model decision | prompt 与训练/评测得到的 router score、threshold | strong 或 weak model | 可通过 SDK/OpenAI-compatible server 接入，不是 K8s operator |
| Gateway API Inference Extension | protocol/control contract | model identity、InferencePool、endpoint picker request | endpoint pick decision | Kubernetes Gateway API 的 inference 扩展，定义 InferencePool 与 picker protocol |
| Envoy AI Gateway | edge/provider governance | API key、provider、route、quota、rate limit、provider status | provider/model upstream | Envoy Gateway + two-tier gateway，可连接自托管 inference gateway |

## 五条请求流程图

### 1. llm-d-router：EPP endpoint picking

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

### 2. Semantic Router：从请求语义选择能力路径

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

### 3. RouteLLM：成本-质量二选一

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

### 4. Gateway API Inference Extension：标准化 gateway 到推理池

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

### 5. Envoy AI Gateway：两层网关

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

## 业务问题与选型

| 业务问题 | 首选关注点 | 组合方式 |
|---|---|---|
| 一个入口管理多个云 provider、key、quota、限流 | Envoy AI Gateway | 外层 Envoy + 内层 llm-d/KServe/Kthena |
| 不同问题自动选择便宜/强模型 | Semantic Router / RouteLLM | 先选模型，再交给 serving endpoint router |
| 需要按 KV、队列、GPU 状态选择 pod | Gateway API Inference Extension / llm-d-router | Gateway/EPP → InferencePool → model server |
| 需要语义、PII、jailbreak、工具过滤和 recipe | Semantic Router | 作为模型入口前的能力策略层 |
| 需要低成本路由算法基线和离线评测 | RouteLLM | SDK/server + provider，不承担 K8s 生命周期 |

## 设计边界

- AI Gateway 解决“谁能访问哪个 provider、如何治理和兜底”；endpoint router 解决“这次请求打哪个 pod/worker”。
- Semantic Router 输出的是 model/recipe/capability path；llm-d-router 输出的是 InferencePool endpoint。
- RouteLLM 的 strong/weak router 是算法与评测框架，不等价于生产 Gateway 或 Kubernetes controller。
- Gateway API Inference Extension 是协议和 API 边界，不是完整 serving stack；llm-d-router 是其生产化 endpoint picker 实现之一。
- 多层路由会增加延迟、调试和策略冲突风险，需要记录每一层的 route decision、模型名、endpoint、策略版本与失败原因。

## 官方资料

- llm-d-router: https://github.com/llm-d/llm-d-router
- Semantic Router: https://github.com/vllm-project/semantic-router
- RouteLLM: https://github.com/lm-sys/RouteLLM
- Gateway API Inference Extension: https://github.com/kubernetes-sigs/gateway-api-inference-extension
- Envoy AI Gateway: https://github.com/envoyproxy/ai-gateway
