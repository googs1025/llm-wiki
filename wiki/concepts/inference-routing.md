---
title: Inference Routing
tags: [concept, inference-routing, llm-serving, ai-gateway, gateway-api]
date: 2026-09-13
sources: [k8s-gateway-routing-comparison-2026-09-13.md, dynamo-architecture-analysis.md, llm-d-router-architecture-analysis.md, llm-d-kv-cache-architecture-analysis.md, semantic-router-architecture-analysis.md, gateway-api-inference-extension-architecture-analysis.md, llm-d-inference-sim-architecture-analysis.md, llm-d-batch-gateway-architecture-analysis.md]
related: [[llm-d]], [[llm-d-router]], [[llm-d-kv-cache]], [[semantic-router]], [[routellm]], [[ai-gateway]], [[envoy-ai-gateway]], [[gateway-api-inference-extension]], [[gateway-api]], [[kv-cache-offload]], [[llm-d-inference-sim]], [[llm-d-batch-gateway]], [[batch-inference]]
---

# Inference Routing

Inference routing 指 LLM/模型服务请求进入 serving fleet 后，如何选择 provider、模型、endpoint、pod、prefill/decode worker 或 KV cache 命中路径。

## 四类路由

| 类型 | 代表 | 决策信号 |
|---|---|---|
| Gateway/API endpoint picking | [[gateway-api-inference-extension]], [[llm-d-router]] | endpoint health、metrics、InferencePool、目标模型 |
| 语义/模型能力路由 | [[semantic-router]], RouteLLM | prompt semantic、成本/质量、guard、模型能力 |
| KV/cache aware routing | [[llm-d-kv-cache]], [[dynamo]], [[kthena]], [[aibrix]] | prefix overlap、KV block location、worker load、LoRA/cache affinity |
| Batch-to-serving dispatch | [[llm-d-batch-gateway]] | batch job、per-model plan、processor concurrency、下游 endpoint capacity |
| Edge/provider governance | [[envoy-ai-gateway]], [[ai-gateway]] | auth、provider、quota、rate limit、audit、fallback |

## 选型提示

不要把所有 router 混为一类。[[llm-d-router]] / Gateway API router 更靠近 Kubernetes endpoint；semantic router 更靠近 prompt/model selection；KV-aware router 更靠近 serving runtime 和 cache locality，[[llm-d-kv-cache]] 则把 KV event/index/scoring 这层单独拆出来。[[dynamo]] 的补充是：selection host 可以是 Dynamo Frontend、GAIE EPP 或 standalone router，但 KV overlap 与 active load 的选择模型保持一致。

[[llm-d-inference-sim]] 对 routing 选型很有用：它不会给出真实 GPU 性能，但能在无 GPU 环境中模拟 OpenAI/vLLM API、KV block/cache events、TTFT/ITL 和 fake metrics，从而验证 endpoint picking、KV-aware scoring 和 autoscaling 闭环。[[llm-d-batch-gateway]] 则说明 batch workload 的“路由”更多发生在 processor 的 per-model plan 和并发控制层，不应和在线低延迟 request routing 混在一起评估。

## KV-aware 路由决策树

```text
请求 → 协议/凭证/配额通过？ ─ 否 → 拒绝或 fallback
              ↓ 是
        模型与能力匹配？ ─── 否 → model router / cascade
              ↓ 是
        endpoint 健康？ ──── 否 → 排除
              ↓ 是
        prefix/KV locality？ → 计算 cache credit
              ↓
        综合 queue + KV + SLO + cost
              ↓
        选择 endpoint / prefill-decode pair
              ↓
        结果与 KV events 反馈回路由器
```

## 网关层与 Endpoint Router 的组合

```
Client
  │ OpenAI / Anthropic request
  ▼
Envoy AI Gateway（可选）
  │ auth · provider · quota · global rate limit
  ▼
Semantic Router / RouteLLM（可选）
  │ model · capability · quality/cost · cascade
  ▼
Gateway API + Inference Extension
  │ InferencePool / Endpoint Picker protocol
  ▼
llm-d Router EPP
  │ KV · queue · priority · health · pod placement
  ▼
vLLM / SGLang / TRT-LLM endpoint
```

这几层可以组合，但不是必须全部部署。[[envoy-ai-gateway]] 解决 provider 与边缘治理，[[semantic-router]]/[[routellm]] 解决模型/能力选择，[[gateway-api-inference-extension]] 定义标准协议，[[llm-d-router]] 负责 Kubernetes serving endpoint 选择。
