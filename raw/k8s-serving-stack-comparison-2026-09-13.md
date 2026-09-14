# Kubernetes Serving Stack 对比：llm-d、AIBrix、KServe、KubeAI、OME、GPUStack、RBG、Kthena

> 分析日期：2026-09-13 · 资料范围：各项目当前 GitHub README 与官方文档首页/架构文档

## 核心判断

这八个项目不在同一个抽象层。可以分成四组：

1. **分布式推理 serving stack**：llm-d、AIBrix、Kthena。
2. **通用/标准化模型服务 control plane**：KServe、OME、KubeAI。
3. **GPU 资源与 Model-as-a-Service 平台**：GPUStack。
4. **分布式、有状态、多角色 workload primitive**：RBG。

```
                         应用 / OpenAI-compatible API
                                      │
        ┌─────────────────────────────┴─────────────────────────────┐
        │                         入口与路由                          │
        │ Kthena Router · AIBrix Gateway · llm-d EPP · KServe Router │
        └─────────────────────────────┬─────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │             推理 workload 编排                  │
              │ llm-d · Kthena ModelServing · RBG RoleBasedGroup│
              └───────────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │           模型生命周期与 runtime 抽象             │
              │ KServe · OME · KubeAI · Kthena ModelBooster      │
              └───────────────────────┬───────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              │          GPU 集群 / 多云 / MaaS 资源平台          │
              │ GPUStack · Kubernetes · Volcano · GPU Operator  │
              └─────────────────────────────────────────────────┘
```

## 项目定位

| 项目 | 一句话定位 | 最核心的业务问题 |
|---|---|---|
| llm-d | Kubernetes-native distributed inference stack，围绕 Gateway/EPP、InferencePool、model server、KV/P/D 和外围工具组成生态 | 如何在 K8s 标准入口下把单机 engine 变成高性能、多副本、分布式 LLM serving |
| AIBrix | vLLM 生态的可插拔 GenAI inference infrastructure | 如何为企业 vLLM fleet 补齐 gateway、LoRA、KV、autoscaling、distributed inference 和硬件故障处理 |
| KServe | 统一 predictive + generative AI 的标准化 K8s inference platform | 如何用一个成熟 API/operator 同时承载传统 ML 和 GenAI，并提供模型缓存、路由、canary、scale-to-zero |
| KubeAI | 面向 LLM/VLM/embedding/speech 的轻量 AI inference operator | 如何用较少的 K8s API 快速部署模型，并把 OpenAI-compatible 入口、模型加载和 autoscaling 组合起来 |
| OME | Open Model Engine，面向模型部署的 K8s operator/control plane | 如何把 model agent、runtime selector、accelerator config 和模型生命周期解耦 |
| GPUStack | GPU cluster manager + Model-as-a-Service platform | 如何跨本地、K8s、云管理 GPU，自动选择 engine/参数并提供多模型 API、计量和 GPU 运维 |
| RBG | RoleBasedGroup workload API，面向多角色、有状态、协调式 AI inference workload | 如何用 Kubernetes 原语表达 gateway→router→prefill→decode，并保证多角色的原子部署、升级、扩缩与故障协调 |
| Kthena | Kubernetes-native AI serving platform，控制面与数据面独立 | 如何把 ModelServing、ModelServer、ModelRoute、P/D、路由、限流、扩缩和 Volcano 调度组成可拆装平台 |

## 能力矩阵

| 能力 | llm-d | AIBrix | KServe | KubeAI | OME | GPUStack | RBG | Kthena |
|---|---|---|---|---|---|---|---|---|
| 主要抽象 | Gateway/EPP + InferencePool | Gateway/CRD + vLLM 组件 | InferenceService / LLMInferenceService | Model CRD + proxy | CRD + model/runtime agents | Server/Worker/Scheduler/Model | RoleBasedGroup / RoleInstance | ModelBooster / ModelServing / ModelServer / ModelRoute |
| 多 engine | vLLM、SGLang 等 | vLLM 生态为主，持续扩展 | predictive 多框架 + vLLM/llm-d | vLLM、Ollama、VLM/embedding/speech | runtime selector | vLLM、SGLang、TRT-LLM、自定义 | 以 workload/engine adapter 解耦 | vLLM、SGLang、Triton 等 |
| KV-aware routing | 重点能力，由 router/KV cache 组件提供 | 重点能力，含 KV event/cache/offload | GenAI 能力已覆盖 KV offload/LLM serving，但不以单一 KV router 作为全部定位 | 非核心定位 | 非核心定位 | 以 engine/平台优化与可扩展 KV 系统为主 | 可承载，取决于 router/engine 集成 | 内置 cache-aware、prefix-cache、LoRA-aware scoring |
| P/D disaggregation | 核心能力 | distributed inference 能力 | LLM serving / llm-d backend 路线 | 依赖 engine/部署组合 | 主要提供生命周期抽象 | 以平台和 engine 能力支持 | 核心 workload 拓扑 | 核心能力，ServingGroup × Prefill/Decode |
| 路由入口 | GAIE EPP、Gateway/Proxy | LLM Gateway、Envoy/Gateway 生态 | router、Ingress/Knative/LLM serving | OpenAI-compatible proxy | 通常交给下游/外部入口 | 内置 gateway/API | 不一定自带完整入口，强调 workload | standalone Router + Gateway API |
| autoscaling | 生态组件/WVA/HPA/KEDA 等 | LLM app-tailored autoscaler | request-based、scale-to-zero、Knative 等 | model autoscaler、scale from zero | 生命周期/资源控制，扩缩依部署方式 | scheduler/平台级资源管理 | coordinated scaling、role-level policies | role-level、panic/stabilization、heterogeneous/cost-aware |
| 拓扑/ gang | 依 K8s/Gateway/调度生态 | LWS/Ray/K8s 组合 | K8s 工作负载与 runtime 组合 | 依 K8s 调度 | accelerator config/runtime | GPU cluster scheduler | 核心：role topology、gang、硬件亲和 | 核心：network topology、gang、Volcano |
| 多租户/治理 | Gateway API、InferencePool 生态 | LoRA、gateway、quota/企业能力 | canary、auth/integration、predictive governance | 简化 API 与 proxy | operator 边界 | auth、access control、metering | workload coordination，不是完整 API gateway | model route、canary、weighted traffic、token rate limit |
| 最适合 | K8s 标准化分布式 LLM serving | vLLM 企业 fleet 与组件化优化 | Kubeflow/标准 ML + GenAI 平台 | 快速自托管模型 API | runtime/operator 平台化 | GPU 云/多集群 MaaS | 多角色 P/D workload 原语 | 一体化 K8s LLM serving 与 Volcano |

## 八个项目的架构重点

### llm-d：标准化入口与分布式推理生态

llm-d 把 Gateway API Inference Extension、EPP、InferencePool 和 model server 放在主链上，再向 KV cache、P/D、variant autoscaling、batch、benchmark、simulator 扩展。它的关键价值是把 LLM-aware routing 接到 Kubernetes 标准入口；它不等于一个新的推理 engine，也不等于单一 Operator。

### AIBrix：vLLM 生态的可插拔基础设施

AIBrix 的 README 把能力拆成 LLM gateway/routing、LoRA 管理、LLM app-tailored autoscaler、Unified AI Runtime、distributed inference、distributed KV cache、异构 GPU serving 和硬件故障检测。它适合已经围绕 vLLM 组织 engine，希望逐步加入企业级控制面能力的团队；不应把它理解为通用 Kubernetes model API 的唯一标准。

### KServe：通用模型服务标准化层

KServe 同时服务 predictive AI 和 generative AI。其 GenAI 方向包括 vLLM/llm-d backend、OpenAI-compatible protocol、model caching、KV offload 和 request-based autoscaling；传统方向还包括多框架、InferenceGraph、canary、解释性和 drift/outlier 相关能力。它的优势是生态与 API 标准化，代价是需要根据 serverless、RawDeployment、ModelMesh、LLMInferenceService 等模式选择正确部署路径。

### KubeAI：轻量、应用友好的模型 operator

KubeAI 用 Model CRD、OpenAI-compatible model proxy、model loader 和 autoscaler 把 LLM、VLM、embedding、speech-to-text 变成易部署服务。它的抽象比 KServe 更聚焦 AI inference，适合快速从“模型文件”得到“可调用 API”；遇到 P/D、复杂 KV locality、多角色 gang 或跨 GPU topology 时，需要额外组合其他系统。

### OME：模型部署与 runtime/accelerator 解耦

OME 的中心问题不是在线路由，而是如何用 operator 选择 runtime、model agent 和 accelerator configuration。它适合平台团队建立模型部署抽象和 runtime 选择层；若核心问题是 KV-aware routing 或 P/D traffic orchestration，应把 OME 与专用 router/serving stack 组合，而不是单独期待它解决请求级调度。

### GPUStack：从 GPU 资源到 Model-as-a-Service

GPUStack 的边界更宽：可以管理本地服务器、Kubernetes 和云环境的 GPU cluster，配置 vLLM/SGLang/TRT-LLM 或自定义 engine，提供模型服务、GPU instance、认证、访问控制、监控、token/API 计量和故障恢复。它更像一体化 GPU 平台；若团队只需要 K8s CRD 和标准 model serving API，GPUStack 可能比需求更重。

### RBG：多角色、有状态 workload 原语

RBG 的 RoleBasedGroup 把一个推理服务表达成多个 role，例如 gateway、router、prefill、decode。Role、RoleInstance 和 CoordinatedPolicy 分别承载角色规格/生命周期、Pod group 状态和跨角色升级/扩缩协调；它强调拓扑、状态、原子操作和硬件亲和，而不是提供一个完整的 API gateway。RBG 更接近“给 serving platform 使用的 workload substrate”。

### Kthena：控制面/数据面拆分的一体化 serving 平台

Kthena 用 ModelBooster 提供一站式 API，用 ModelServing 表达 ServingGroup × Role，用 ModelServer 做服务暴露和 workload discovery，用 ModelRoute 表达模型匹配、canary、权重、限流和 traffic policy；Router 作为独立数据面执行 model/KV/LoRA/负载相关选择。其显著特点是 workload controller 和 networking/router 可以分别安装，支持 topology-aware scheduling、gang scheduling、P/D role-level autoscaling 与 Volcano 集成。

## 选型路径

```
你首先需要什么？
        │
        ├─ 传统 ML + GenAI 统一 API / Kubeflow 生态？ ──► KServe
        │
        ├─ 轻量快速把模型变成 OpenAI API？ ───────────► KubeAI
        │
        ├─ runtime / accelerator / model lifecycle 抽象？ ─► OME
        │
        ├─ GPU 集群、多云、MaaS、计量与运维一体化？ ───► GPUStack
        │
        ├─ Gateway API + InferencePool + 分布式 LLM？ ───► llm-d
        │
        ├─ vLLM fleet + LoRA/KV/企业组件？ ───────────► AIBrix
        │
        ├─ 多角色、有状态、P/D workload 协调原语？ ────► RBG
        │
        └─ K8s 原生完整 LLM serving + Volcano 拓扑？ ──► Kthena
```

最终选择要看组织边界：平台团队是否已经有 Gateway API、是否坚持标准 K8s API、是否需要 P/D 和 KV 路由、是否需要管理 GPU 集群本身、以及是否把多角色 workload 当成独立基础设施能力。

## 官方资料

- llm-d: https://github.com/llm-d/llm-d
- AIBrix: https://github.com/vllm-project/aibrix
- KServe: https://github.com/kserve/kserve
- KubeAI: https://github.com/substratusai/kubeai
- OME: https://github.com/kubeflow/ome
- GPUStack: https://github.com/gpustack/gpustack
- RBG: https://github.com/sgl-project/rbg
- Kthena: https://github.com/volcano-sh/kthena
