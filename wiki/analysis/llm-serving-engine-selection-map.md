---
title: LLM Serving / 推理引擎选型地图
tags: [llm-inference, llm-serving, kv-cache, selection, ai-infra]
date: 2026-09-22
sources: [src-dynamo-architecture, src-sglang-architecture, src-skypilot-architecture, src-k8s-gpu-device-plugins-stars, src-vllm-architecture, src-aibrix-architecture, src-k8s-serving-stack-comparison]
related: ["[[llm-inference-serving-project-map]]", "[[vllm]]", "[[sglang]]", "[[dynamo]]", "[[paged-attention]]", "[[radix-attention]]", "[[disaggregated-serving]]", "[[kv-cache-offload]]", "[[aibrix]]", "[[inference-routing]]", "[[model-serving-operator]]"]
---

# LLM Serving / 推理引擎选型地图

已有 [[llm-inference-serving-project-map]] 把 D1-D5 的边界和证据铺开。这页面向选型：先判断问题属于哪一层，再选择可组合的项目；不要把 engine、distributed runtime、K8s routing/control plane 和 GPU 基础设施当成同类替代品。

## 当前上游核验（2026-09-22）

截至 2026-09-22，通过 GitHub API 与官方文档核验以下 HEAD；详细架构证据见 [[llm-inference-serving-project-map]]。

| 项目 | 核验版本 | 当前职责 |
|------|----------|----------|
| [[vllm]] | HEAD [`d50723df04f7`](https://github.com/vllm-project/vllm/commit/d50723df04f7) | engine scheduler、model execution、local KV |
| [[sglang]] | HEAD [`04c0913434c4`](https://github.com/sgl-project/sglang/commit/04c0913434c4) | engine/runtime、RadixCache、distributed/P-D integration |
| [[dynamo]] | HEAD [`f36d2fab37fd`](https://github.com/ai-dynamo/dynamo/commit/f36d2fab37fd) | distributed request/control/state runtime、routing、KV transfer、planner |
| [[llm-d]] | HEAD [`1e9a86a3a9da`](https://github.com/llm-d/llm-d/commit/1e9a86a3a9da) | Proxy/EPP、InferencePool、Model Server 与 routing signals |
| [[aibrix]] | HEAD [`96056b47f158`](https://github.com/vllm-project/aibrix/commit/96056b47f158) | K8s routing、autoscaling、adapter/model lifecycle、KV/multi-role orchestration |

## 选型结论

没有一个项目能在所有层胜出。先选 engine，再按确实存在的集群、路由、运维和基础设施需求叠加能力；每加一层都要用收益覆盖其控制面和故障域成本。

| 选择 | best fit | avoid-if | adoption cost | 下一步核验 |
|------|----------|----------|---------------|------------|
| [[vllm]] | 需要成熟的 OpenAI-compatible 基线、广泛模型覆盖和 [[paged-attention]] | 目标模型/硬件在 [[sglang]] 上有已验证的显著优势 | 低到中；先处理镜像、模型、监控和容量 | 用真实模型、量化、并发和输出长度压测吞吐、P99、显存与稳定性 |
| [[sglang]] | 前缀复用、结构化生成、speculative decoding 或其执行路径更匹配 workload | 团队更看重保守生态基线，或关键模型/硬件适配尚未验证 | 低到中；高级特性和 distributed/P-D backend 会增加调优面 | 对同一流量回放，核验 [[radix-attention]] 命中、尾延迟、正确性和故障恢复 |
| [[dynamo]] | 多节点 runtime、P/D、KV transfer、KV-aware routing 需要统一协调 | 单机或普通副本服务已满足目标，暂不需要跨节点状态协同 | 高；引入 router、worker pools、KV/control state 与额外可观测性 | 做端到端 P/D/KV transfer 基准，并演练 worker、网络和 KV tier 故障 |
| [[llm-d]] | K8s 上需要 Gateway API、EPP endpoint picking 和 InferencePool | 不使用 K8s/Gateway API，或普通 Service/LB 已足够 | 中到高；新增 CRD、Gateway/EPP、升级兼容与运维责任 | 核验目标 Gateway/InferencePool 版本、路由信号、扩缩交互和故障回退 |
| [[aibrix]] | 需要 autoscaling、LoRA/adapter、model lifecycle 及更广的 K8s inference operations | 只缺路由，或团队不需要其 lifecycle/control-plane 能力 | 中到高；应按组件渐进采用，不必部署全部能力 | 逐项验证所选 controller/CRD 的边界、升级路径、状态恢复和与现有平台的重叠 |

## 先选层，再选项目

| 当前问题 | 应选择的层 | 代表项目 |
|----------|------------|----------|
| scheduler、kernel、local KV、单实例吞吐 | 推理引擎 | [[vllm]], [[sglang]] |
| multi-node runtime、P/D、KV transfer | distributed serving runtime | [[dynamo]] |
| Gateway API、endpoint picking、InferencePool | K8s routing/serving stack | [[llm-d]] |
| autoscaling、LoRA/model lifecycle、K8s inference operations | K8s inference control plane | [[aibrix]] |
| GPU allocation、sharing、health、capacity | infrastructure | [[k8s-gpu-device-stack]] |

不同层的项目不是直接替代关系；生产系统通常组合一个 engine、一个 routing/control layer 和一个 infrastructure layer。distributed runtime 只在多节点协调收益明确时加入，routing 与 control plane 也可以按需求择一或组合，而不是默认全栈采用。

## 架构区别

| 层 | 负责什么 | 不负责什么 | 典型组合边界 |
|----|----------|------------|--------------|
| [[vllm]] / [[sglang]] engine | scheduler、kernel、model execution、local KV | 完整 K8s routing/control plane 和 GPU 集群底座 | 向上暴露服务端点和运行指标 |
| [[dynamo]] distributed runtime | 多节点 request/control/state、P/D pools、KV transfer/routing | 替代底层 engine 或通用 K8s 平台 | 组织 engine workers；可与 K8s 层集成 |
| [[llm-d]] routing/serving stack | Gateway API、EPP、InferencePool、Model Server 与 routing signals | engine kernel、通用 model lifecycle 平台 | 在 K8s 请求入口选择合适的 engine endpoint |
| [[aibrix]] inference control plane | autoscaling、adapter/model lifecycle、routing 与多角色编排 | 替代 engine kernel 或 GPU device layer | 按需选择 controller，与 engine、Gateway 和基础设施衔接 |
| [[k8s-gpu-device-stack]] infrastructure | GPU allocation、sharing、health、capacity 和队列 | 模型执行、KV-aware request routing | 为所有上层提供设备与容量约束 |

详细的 D1-D5 组件图、控制流和证据集中在 [[llm-inference-serving-project-map]]；本页只保留影响选型的层间边界。

## 决策轴

- **执行适配**：先用真实模型、硬件、量化方式、scheduler/KV 行为和运维约束比较 [[vllm]] 与 [[sglang]]，不要只看通用 benchmark。
- **跨节点协调**：只有在 P/D、KV transfer 或多节点 runtime 是明确瓶颈时评估 [[dynamo]]；同时比较 engine-native integration 的能力和复杂度。
- **K8s 请求路由**：需要 Gateway API、EPP、InferencePool 时评估 [[llm-d]]，普通 Service/Gateway 足够时不增加该层。
- **K8s 推理运维**：需要 autoscaling、adapter/model lifecycle 和更广控制面时评估 [[aibrix]]，按组件采用并检查职责重叠。
- **设备与容量**：用 [[k8s-gpu-device-stack]] 处理 GPU allocation、sharing、health 和 capacity；它会约束上层部署，但不替代引擎或路由。
- **跨云资源位置**：需要跨云/K8s/Slurm 选择资源和启动 workload 时再看 [[src-skypilot-architecture|SkyPilot]]；它是资源控制面，不是 inference engine。

## 决策流程图

以下分支不是互斥答案：先选 engine，后续命中的层可以继续组合；任何一步收益不明确，都停在当前最小充分栈。

```text
需要模型执行引擎？
├─ 是 → 按模型、硬件、scheduler/KV 行为和运维适配选择 vLLM / SGLang
│        │
│        ├─ 需要 multi-node runtime 或 P/D、KV transfer 协调？
│        │  ├─ 是 → 评估 Dynamo 与 engine-native integrations
│        │  └─ 否 → 保持当前 engine 层
│        │
│        ├─ K8s 上需要 Gateway / EPP / InferencePool routing？
│        │  ├─ 是 → 评估 llm-d
│        │  └─ 否 → 使用普通 Service / Gateway
│        │
│        └─ 需要 autoscaling、adapters、model lifecycle 和更广 K8s operations？
│           ├─ 是 → 评估 AIBrix 的所需组件
│           └─ 否 → 不增加 inference control plane
└─ 否 → 先确认问题是否其实属于 routing、control plane 或 infrastructure

所有分支结束 → 保留满足需求的最小组合；不因“平台完整”而默认叠加全部项目
```

## 组合方案

| 模式 | 组成 | best fit | avoid-if | adoption cost | 下一步核验 |
|------|------|----------|----------|---------------|------------|
| 最小 engine service | [[vllm]] 或 [[sglang]] + 普通 Service/Gateway | 单集群、普通副本路由，重点是尽快提供稳定推理 API | 已确认需要 KV-aware endpoint picking、P/D 或复杂 lifecycle | 低；主要是 engine、镜像、模型存储、指标和入口配置 | 回放真实流量，核验容量、P99、滚动升级和实例故障回退 |
| K8s 智能路由 | engine + [[llm-d]] Router/InferencePool | K8s/Gateway API 环境需要根据 KV、负载或模型信号选择 endpoint | 普通 Service/LB 已达标，或不能承担 CRD/Gateway/EPP 运维 | 中到高；增加 routing control/data path 与版本兼容面 | 核验路由增益、信号陈旧行为、扩缩期间 endpoint 一致性和 fallback |
| distributed runtime | engine + [[dynamo]] | 多节点 P/D、KV transfer 或跨 worker 状态协调能带来可测收益 | 单机/普通副本已满足 SLO，网络或 KV transfer 成本抵消收益 | 高；增加 runtime 服务、worker pools、状态/KV tier 和故障域 | 比较共置与分离部署，测端到端 TTFT/TPOT/P99，并做网络、worker、KV 故障演练 |
| inference operations platform | engine + 选定的 [[aibrix]] 组件 | 需要 autoscaling、LoRA/adapters、model lifecycle 或多角色 K8s 运维 | 只缺一个小能力，现有平台已覆盖，或职责重叠无法收敛 | 中到高；按所选 controller/CRD 计，不要求全量采用 | 建立组件级 PoC，核验 reconciliation、升级/回滚、状态恢复及与现有 autoscaler/Gateway 的所有权 |

## 避坑条件

- 不要把 [[dynamo]] 当成“另一个 vLLM”；它是 serving 编排层。
- 不要把 [[llm-d]] 当成 engine 或完整 inference operations 平台；它当前的选型核心是 Gateway/EPP/InferencePool routing/serving stack。
- 不要把 [[aibrix]] 当成必须整套部署的发行版；只采用能覆盖明确 operations 缺口且所有权清晰的组件。
- 不要把 [[src-skypilot-architecture|SkyPilot]] 当成 inference engine；它是资源控制面。
- P/D 分离只有在 prompt/decode 负载、KV transfer、路由和扩缩都配套时才有收益。
- KV cache 已经是一等资源，路由、迁移、offload 都要显式建模。
- 不要把不同层的项目塞进单选题，也不要为了“完整架构”默认部署所有层；从最小充分栈开始，用实测瓶颈决定下一层。
