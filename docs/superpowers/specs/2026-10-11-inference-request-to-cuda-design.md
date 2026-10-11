---
title: AIBrix、Dynamo、llm-d 请求到 CUDA 执行链设计
date: 2026-10-11
status: pending-user-review
---

# AIBrix、Dynamo、llm-d 请求到 CUDA 执行链设计

## 1. 目标

本次建设面向希望从 AI Infra 控制面一路学到 GPU 执行细节的读者。主线问题是：一次 OpenAI-compatible 在线推理请求从 AIBrix、Dynamo 或 llm-d 入口进入之后，如何经过路由、排队、Prefill/Decode、KV cache、vLLM/SGLang scheduler、模型算子和 GPU kernel，最终在 NVIDIA GPU 的 SM、Tensor Core 和内存层级上完成计算，并将 token 流返回客户端。

内容必须同时区分两个正交维度：

1. 推理引擎：vLLM 与 SGLang。
2. Serving 形态：聚合式（Prefill 与 Decode 共置）与 P/D 分离式。

每个平台页都给出 `平台 × 引擎 × Serving 形态` 的支持状态和独立流程，不能用一张通用图暗示所有组合拥有相同实现、成熟度或数据路径。

## 2. 成功标准

1. 读者能从统一入口选择 AIBrix、Dynamo 或 llm-d，再选择 vLLM/SGLang 和聚合式/P-D 路径。
2. 三个平台页分别解释请求热路径、控制面旁路、KV 元数据与数据路径、token 返回路径及失败边界。
3. vLLM 与 SGLang 各有独立源码调用链，不用抽象名掩盖具体 scheduler、batch、KV allocator、model runner 和 attention backend 差异。
4. GPU 下钻页从框架算子解释到 CUDA/Triton/custom kernel、launch、thread block、warp、Tensor Core、CUDA core、HBM/L2/shared memory/register 和同步，不停在“调用 GPU”这一层。
5. 每个重要阶段至少有一张局部图；全文预计 40–50 张等宽 ASCII 图。
6. 所有版本敏感判断都固定到实施时重新核验的官方仓库 commit；历史 Source 页与新鲜 GitHub 观察明确分开。
7. 新页面进入 `wiki/index.md` 阅读路径，相关 Entity/Concept 有反向链接，HTML 与 graph 同步，无孤儿页或断链。

## 3. 非目标

- 不覆盖模型训练、反向传播、优化器或数据并行训练流程。
- 不把 TensorRT-LLM、TGI、MindIE 等第三种 engine 扩展到同等深度；必要时只作为边界说明。
- 不把所有模型结构逐层展开；以 Decoder-only Transformer、Dense MLP 和典型 MoE 为主，特殊模型只标差异点。
- 不承诺不同平台、engine 或 KV connector 之间存在统一的 P/D handoff、重试和故障恢复协议。
- 不把 default branch HEAD 当作稳定 release；页面记录核验日期、commit 和证据类型。
- 不修改 `raw/`，也不把既有 raw-backed Source 摘要改写成当前事实。
- 不引入新的图形运行时。图源使用 Markdown 内的 ASCII，保证 Obsidian、Git diff 和现有 HTML builder 一致可读。

## 4. 设计选择

### 4.1 采用七页分层结构

七个新页面全部位于 `wiki/analysis/`；稳定术语仍由既有 `wiki/concepts/` 页面承载。

```text
[[llm-inference-request-lifecycle]]
│
├── 平台请求路径
│   ├── [[aibrix-inference-request-flow]]
│   ├── [[dynamo-inference-request-flow]]
│   └── [[llm-d-inference-request-flow]]
│
├── 引擎执行路径
│   ├── [[vllm-gpu-execution-path]]
│   └── [[sglang-gpu-execution-path]]
│
└── GPU 下钻
    └── [[llm-gpu-kernel-execution-path]]
```

选择七页而不是十二篇组合页，是为了避免平台入口、engine 内部和 GPU 微架构内容重复。每个平台页仍保留四条独立流程；共享的 engine 与 GPU 细节通过明确的 handoff 锚点进入下钻页。

若某个组合的证据状态是 `conceptual` 或 `unsupported / not found`，对应章节仍然存在，但内容改为“可确认边界、缺失证据、不能画出的步骤和下一步验证”，不得伪造成功时序图以凑齐四条路径。

### 4.2 采用“证据阶梯”

每个支持矩阵单元必须标记为以下一种状态：

- `documented`：官方架构或操作文档明确描述。
- `tested`：官方 CI、example、recipe 或测试覆盖，但产品文档可能不完整。
- `experimental`：仓库中存在实现或配置，稳定性/兼容性仍有限。
- `conceptual`：架构上可以组合，但本次未找到官方端到端证据。
- `unsupported / not found`：官方明确不支持，或当前核验没有找到实现证据。

`conceptual` 不能画成可直接部署的成功路径；它只用于解释接口边界和待验证项。

### 4.3 使用一致的层级与箭头语义

所有页面采用相同分层：

```text
L0 Client / API protocol
L1 Gateway / proxy / authentication / request normalization
L2 Router / endpoint picker / admission / queue
L3 Distributed serving / P-D coordinator / KV transfer
L4 Engine frontend / scheduler / continuous batch / KV allocator
L5 Model runner / model layers / parallel collectives
L6 Framework dispatcher / compiled graph / custom ops
L7 CUDA or Triton kernels / NCCL / NIXL data movement
L8 GPU SM / warp / Tensor Core / memory hierarchy
```

图中箭头约定：

- `──►`：请求、token 或同步调用的主数据流。
- `··►`：metrics、KV event、discovery、control reconciliation 等异步反馈。
- `══►`：KV tensor、activation 或 collective 等大块 GPU 数据移动。
- `[CPU]`、`[GPU]`、`[NET]`：明确执行位置；不能把控制消息和 KV payload 画成同一条线。

## 5. 页面设计

### 5.1 `llm-inference-request-lifecycle.md`

职责：作为统一学习入口，建立不依赖具体项目的端到端心智模型。

主要内容：

1. 三个选择维度：平台、engine、聚合式/P-D。
2. 八层端到端总图。
3. 一次请求的状态对象演化：JSON → normalized request → tokens → scheduler request → sequence/batch → tensors → kernel work → logits → sampled token → SSE chunk。
4. 聚合式与 P/D 的共同阶段和分叉点。
5. 四象限导航矩阵及七页阅读顺序。
6. “控制面不在每个 token 热路径上”的边界图。
7. 概念索引：TTFT、ITL/TPOT、continuous batching、chunked prefill、prefix cache、PagedAttention、RadixAttention、CUDA Graph、TP/PP/EP/DP、NCCL/NIXL。

预计图：4–5 张。

### 5.2 三个平台请求页

文件：

- `aibrix-inference-request-flow.md`
- `dynamo-inference-request-flow.md`
- `llm-d-inference-request-flow.md`

每页固定使用同一模板：

1. 当前仓库 snapshot、版本边界与证据清单。
2. 平台架构及 ownership 图。
3. `vLLM/SGLang × aggregated/P-D` 支持矩阵。
4. vLLM 聚合式请求时序。
5. SGLang 聚合式请求时序。
6. vLLM P/D 请求、KV metadata 和 KV payload 时序。
7. SGLang P/D 请求、KV metadata 和 KV payload 时序。
8. KV-aware routing：prefix hash/index、负载、排队、候选过滤、score/pick。
9. streaming 返回：首 token、后续 token、finish reason、取消传播。
10. timeout、KV miss、stale index、prefill/decode worker loss、部分输出后的不可透明重试。
11. 控制面与数据面分离：deployment、autoscaling、health、discovery 不伪装成逐 token 同步调用。
12. 源码阅读入口表：文件、symbol、调用者、输出对象、下一跳。
13. 与另外两个平台的边界对照。

每个平台预计 6–8 张图，三页共 20 张左右。

平台特有重点：

- AIBrix：Gateway plugin、routing policy、model/adapter runtime、P/D handoff、vLLM 与 SGLang 路径的成熟度差异。
- Dynamo：Frontend、KV-aware Router、Runtime endpoint/discovery/event plane、aggregated/disaggregated backend、NIXL 与 Planner/Operator 旁路。
- llm-d：Gateway/Proxy、EPP/Inference Scheduler、InferencePool、P/D coordinator、KV index/offloader、DisaggregatedSet/LeaderWorkerSet 与 engine connector。

### 5.3 `vllm-gpu-execution-path.md`

职责：从 vLLM API/engine 边界追到 kernel launch，并为四个平台组合提供共同下半段。

核心调用链以实施时当前 V1 代码为准，至少覆盖：

```text
API server / EngineClient
  → EngineCore request queue
  → Scheduler.schedule
  → KVCacheManager prefix lookup / block allocation
  → scheduler output
  → Worker / GPUModelRunner.execute_model
  → input preparation / CUDA Graph selection
  → model forward
  → attention backend / MLP or MoE / collectives
  → logits processor / sampler
  → EngineCore output update
  → streamed token
```

独立解释：

- Prefill、chunked prefill、decode 如何竞争 token budget。
- PagedAttention block table 如何变成 attention kernel 可消费的地址/索引。
- eager、torch.compile 与 CUDA Graph 路径的边界。
- TP/PP/EP/DP 时每一层前后的 collective 和 rank ownership。
- Dense MLP 与 MoE dispatch/combine 的不同 GPU 路径。
- sampling 在 GPU/CPU 上的版本性边界，不写死未经证实的执行位置。
- P/D 模式下 engine 之外的 connector 在何处交接 KV，哪些部分仍属于 vLLM。

预计图：7–8 张。

### 5.4 `sglang-gpu-execution-path.md`

职责：从 SGLang server/tokenizer/scheduler 追到 kernel launch，不复用 vLLM 名称替代其真实抽象。

核心调用链以实施时当前代码为准，至少覆盖：

```text
HTTP server / TokenizerManager
  → request IPC
  → Scheduler event loop
  → waiting/running queues
  → ScheduleBatch / forward mode
  → RadixCache prefix match
  → token-to-KV allocation
  → ModelRunner forward
  → attention backend / MLP or MoE / collectives
  → logits / sampling
  → detokenizer / streamed token
```

独立解释：

- RadixCache ownership、prefix match、lock/refcount 与 eviction。
- extend、decode、idle 等 forward mode 如何改变 batch 和 kernel 形态。
- overlap scheduler 或双 batch overlap 等当前实现存在时的 CPU/GPU 并行边界。
- Triton/CUDA backend、CUDA Graph 与 attention backend 选择。
- TP/PP/EP 与 MoE 的通信路径。
- P/D connector、KV bootstrap/handoff 与 SGLang engine 内部的边界。

预计图：7–8 张。

### 5.5 `llm-gpu-kernel-execution-path.md`

职责：解释“GPU 最终怎么计算”，并纠正常见的“所有计算都在 CUDA Core 上执行”的过度简化。

页面按以下链路组织：

```text
Python model layer
  → PyTorch dispatcher / custom op registration
  → torch.compile graph OR eager op
  → ATen / Triton / CUDA C++ / CUTLASS / FlashAttention backend
  → host-side launch configuration
  → CUDA stream + grid + thread blocks
  → SM schedules warps
  → LD/ST units move data through HBM/L2/shared/registers
  → Tensor Cores execute MMA for GEMM/attention
  → CUDA cores handle scalar/vector arithmetic and auxiliary work
  → reductions / synchronization / output stores
  → next kernel or NCCL collective
```

必须详细覆盖：

1. CPU host、CUDA driver/runtime、kernel launch 与异步 stream。
2. Grid、thread block、warp、thread 与 SM residency。
3. Register、shared memory、L1、L2、HBM 的数据移动和容量/带宽/延迟含义。
4. Tensor Core 与 CUDA core 的职责差异；GEMM 主计算通常不能笼统写成“CUDA core 计算”。
5. Embedding/gather、RMSNorm、RoPE、QKV projection、attention、output projection、MLP/SwiGLU、MoE、logits、sampling 的典型 kernel 序列。
6. FlashAttention/PagedAttention/RadixAttention 中逻辑缓存结构如何成为物理内存访问。
7. GEMM tiling：CTA tile、warp tile、MMA tile、global→shared→register pipeline。
8. Attention tiling：Q tile、KV tile、online softmax、局部 reduction 与写回。
9. CUDA Graph 捕获/重放减少 launch overhead，但不消除 kernel 自身计算。
10. Kernel fusion 如何减少 HBM round trip，及为什么会增加寄存器压力或降低 occupancy。
11. TP/EP collective：NCCL kernel、NVLink/PCIe/RDMA 与计算 stream 的同步/重叠。
12. P/D KV transfer：NIXL/RDMA/IPC 等传输不等价于 attention kernel；metadata control path 与 KV payload 分开。
13. 性能观测映射：TTFT/ITL 到 queue、kernel、memory、collective、launch gap；对应 Nsight Systems/Compute、DCGM 和 engine metrics。
14. 一张完整的单层 Transformer GPU 时间线，以及一张单 token decode 时间线。

预计图：10–12 张。

## 6. 概念与既有页面同步

本次不为每个术语新建页面，而是优先更新已有 Concept，增加新入口与必要边界：

- `wiki/concepts/llm-inference.md`
- `wiki/concepts/disaggregated-serving.md`
- `wiki/concepts/inference-routing.md`
- `wiki/concepts/paged-attention.md`
- `wiki/concepts/radix-attention.md`
- `wiki/concepts/kv-cache-offload.md`
- `wiki/concepts/gpu-programming-learning.md`

Entity 只增加请求流入口、当前支持边界和版本提示，不复制分析页全文：

- `wiki/entities/aibrix.md`
- `wiki/entities/dynamo.md`
- `wiki/entities/llm-d.md`
- `wiki/entities/vllm.md`
- `wiki/entities/sglang.md`

导航层更新：

- `wiki/index.md` 增加“请求到 CUDA”阅读路径及七个页面入口。
- `wiki/log.md` 追加一次 durable query operation。
- 运行 `wiki/html-assets/build.py` 重建 HTML、index 和 graph。

## 7. 源码研究与证据策略

实施时按平台热路径逐条完成源码追踪，不能只依据 README 画图。

### 7.1 官方仓库

- `vllm-project/aibrix`
- `ai-dynamo/dynamo`
- `llm-d/llm-d`
- `llm-d/llm-d-router`（GitHub API 的历史仓库名可能发生 redirect，记录 canonical repository）
- `vllm-project/vllm`
- `sgl-project/sglang`

### 7.2 证据优先级

1. 当前 commit 的代码、测试和配置。
2. 同一 commit 附近的官方架构/操作文档。
3. release notes 或 tag 文档。
4. 现有 raw-backed Source 摘要，只作为历史背景。
5. 通用 CUDA Programming Guide、PTX/硬件资料，用于稳定 GPU 概念；具体 kernel 仍回到项目源码。

### 7.3 可追溯格式

每个页面页首记录：

- 核验日期。
- repository 与 canonical URL。
- commit SHA。
- 本地 clone 是否为 fork/滞后 snapshot。
- 版本敏感结论列表。

源码入口表使用 `repository/path:symbol`，并链接到固定 commit。正文明确区分：

- `仓库事实`：代码/文档直接证明。
- `架构解释`：根据调用链归纳。
- `GPU 通用机制`：硬件/编程模型知识。
- `待验证`：未找到端到端证据或依赖具体部署。

## 8. 图表规范

每张图包含四部分：标题、前置条件、ASCII 图、图后逐箭头解释。不得只给图不解释。

图的密度允许高，但必须遵循：

- 总图只展示层与 ownership，局部图再展开 symbol 和对象。
- 同一图不混合请求热路径与 deployment reconcile；必要时上下分区。
- P/D 图必须画出 control metadata、KV payload 和 token stream 三条不同路径。
- Engine 图必须标 CPU/GPU 边界、进程边界和 rank 边界。
- GPU 图必须标 memory hierarchy、同步点和 kernel/collective 类型。
- 所有缩写在图后第一次出现时展开。
- 宽图可横向滚动，但优先控制在约 120–150 个字符；超出时拆成总图与局部图。

## 9. 正确性边界

页面必须反复保持以下区分：

- Gateway/Router/EPP 做 endpoint decision，不一定承载完整 token 数据流。
- KV index/event 只描述位置或命中信号，不是 KV tensor 本身。
- Prefix cache 命中不保证目标 worker 当前排队更短。
- 聚合式不等于没有 prefill/decode 阶段，只是二者在同一 engine/worker 池执行。
- P/D 分离不等于每个请求都跨节点；可能同机、同节点跨 GPU 或跨节点。
- PagedAttention 是 KV 地址管理与 attention 访问方式，不是完整 routing 策略。
- RadixAttention/RadixCache 与跨副本 KV-aware routing 属于不同层。
- CUDA Graph 是 launch 优化，不是新的模型算法。
- Tensor Core、CUDA core、LD/ST unit、NCCL/NIXL 各自承担不同工作。
- 请求已输出 token 后，透明 retry 可能破坏流语义；恢复能力必须按平台/backend 契约描述。
- Control plane 的 autoscaling/reconcile 是异步反馈，不在每个 token 的同步调用栈里。

## 10. 验证策略

### 10.1 内容验证

- 七个新页面均有完整 YAML frontmatter、`[[wikilink]]` 和入站链接。
- 三个平台各有四象限支持矩阵及四条流程；无法证实的组合明确标状态。
- vLLM/SGLang 页面均包含 API→scheduler→KV→model runner→kernel handoff。
- GPU 页面包含 host launch、SM/warp、Tensor Core/CUDA core、memory hierarchy、kernel sequence、collective 和 profiling。
- 平台、engine、GPU 三层的交接对象名称一致。
- 检查所有固定 commit 链接可解析。

### 10.2 图表验证

- 统计 ASCII 图数量，目标不少于 40 张。
- 每张图均有标题、前置条件和正文解释。
- 抽查四条端到端路径：AIBrix+vLLM+P/D、Dynamo+SGLang+P/D、llm-d+vLLM+aggregated、llm-d+SGLang+aggregated。
- 抽查一条请求从 JSON 到 SSE token 的对象演化。
- 抽查一层 Transformer 从 input tensor 到 HBM 写回的 kernel 时间线。

### 10.3 Wiki 与生成验证

- 校验 frontmatter、断链和孤儿页。
- 更新 index、Entity、Concept 和 log 后重建 HTML/graph。
- Builder 连续执行两次，第二次不产生新差异。
- 检查七个生成 HTML 页面、导航、代码块横向滚动和 graph 节点/边。
- 运行 `git diff --check`。
- 不修改 `raw/`，不覆盖手写 HTML，不包含工作区既有无关文件。

## 11. 提交边界

设计文档单独提交。实施完成后，durable wiki operation 使用：

```text
query: Trace inference requests from gateways to CUDA
```

实施提交只包含本专题 Markdown、索引、日志和对应生成物，不纳入工作区中既有的无关未跟踪文件。

## 12. 风险与控制

- **页面过长**：总览、平台、engine、GPU 四层拆页；重复机制只保留摘要和链接。
- **组合支持被高估**：所有矩阵单元使用证据阶梯，不以目录名替代端到端支持证明。
- **源码快速漂移**：固定 commit，记录核验日期，并把稳定概念与版本性 symbol 分开。
- **“CUDA core”表述失真**：专门区分 Tensor Core、CUDA core、memory pipeline 和 communication engine。
- **图过密难读**：每张图只回答一个主问题，超过宽度或同时出现多条时间轴时拆图。
- **控制面和热路径混淆**：使用分层、箭头语义和独立旁路图。
- **GPU 细节变成泛科普**：每个硬件概念都回链到 vLLM/SGLang 的具体算子或性能现象。
