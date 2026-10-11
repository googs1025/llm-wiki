---
title: LLM 推理请求端到端生命周期：从入口到 CUDA
tags: [analysis, llm-inference, request-lifecycle, vllm, sglang, cuda, gpu]
date: 2026-10-11
sources: []
related: ["[[llm-inference]]", "[[disaggregated-serving]]", "[[inference-routing]]", "[[aibrix-inference-request-flow]]", "[[dynamo-inference-request-flow]]", "[[llm-d-inference-request-flow]]", "[[vllm-gpu-execution-path]]", "[[sglang-gpu-execution-path]]", "[[llm-gpu-kernel-execution-path]]"]
---

# LLM 推理请求端到端生命周期：从入口到 CUDA

这是一组“沿着一次请求走”的学习入口。它把 [[aibrix]]、[[dynamo]]、[[llm-d]] 的平台层，[[vllm]]、[[sglang]] 的引擎层，以及 GPU kernel 的执行层连接起来。目标不是把所有系统画成相同形状，而是建立一套共同坐标，再明确每个项目在哪里改变了请求、状态或数据的所有权。

> [!warning] 先区分“组合”与“支持”
> `平台 × 引擎 × aggregated/P-D` 是研究矩阵，不是默认支持矩阵。每个平台页会按固定 commit 将组合标为 `documented`、`tested`、`experimental`、`conceptual` 或 `unsupported / not found`。没有端到端证据的组合不会被画成可工作的成功链。

## 如何选择一条路径

先回答三个问题：入口由谁管理、GPU 上运行哪个 engine、Prefill 与 Decode 是否跨 worker 交接 KV。

| 选择维度 | 选项 | 它主要改变什么 |
|---|---|---|
| 平台 | [[aibrix-inference-request-flow]] | Gateway plugin、routing policy、runtime/adapter 与 P/D handoff |
| 平台 | [[dynamo-inference-request-flow]] | Frontend、KV-aware Router、Runtime request/event plane、NIXL |
| 平台 | [[llm-d-inference-request-flow]] | Gateway/Proxy、EPP、InferencePool、P/D coordinator 与 K8s orchestration |
| 引擎 | [[vllm-gpu-execution-path]] | EngineCore、Scheduler、KVCacheManager、GPUModelRunner、PagedAttention |
| 引擎 | [[sglang-gpu-execution-path]] | TokenizerManager、Scheduler、ScheduleBatch、RadixCache、ModelRunner |
| 执行 | [[llm-gpu-kernel-execution-path]] | PyTorch/Triton/CUDA op 到 stream、kernel、warp、Tensor Core 与显存 |

```text
                         选择平台入口
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
       AIBrix             Dynamo              llm-d
          └──────────────────┼──────────────────┘
                             ▼
                    选择引擎与版本证据
                    ┌────────┴────────┐
                    ▼                 ▼
                  vLLM              SGLang
                    └────────┬────────┘
                             ▼
                    选择 Serving 形态
                    ┌────────┴────────┐
                    ▼                 ▼
              Aggregated             P/D
              同池执行           KV 跨角色交接
                    └────────┬────────┘
                             ▼
               Model ops → CUDA kernels → GPU
```

一个实用读法是先看目标平台页，走到 engine handoff 后进入对应引擎页，再从具体 attention/GEMM/custom op 跳到 GPU 下钻页。平台页回答“请求去哪里”，引擎页回答“这一轮算什么”，GPU 页回答“这些 tensor 怎样真的被计算”。

## L0–L8 端到端总图

下面九层是定位问题的共同坐标，不表示九个同步函数调用。尤其是 Kubernetes reconcile、autoscaling、discovery 和 KV event 多为异步反馈，不会在每个 token 的热路径上逐层执行。

```text
[CPU/NET]
L0  Client / Agent
    JSON request · messages · sampling params · stream=true
       │ HTTP/gRPC request                                      ▲ SSE/token chunks
       ▼                                                        │
L1  Gateway / Proxy / Protocol
    auth · quota · model rewrite · request normalization
       │ normalized request                                     │
       ▼                                                        │
L2  Router / Endpoint Picker / Admission
    eligibility · prefix locality · load · queue · priority
       │ selected endpoint / route metadata                      │
       ▼                                                        │
L3  Distributed Serving
    aggregated dispatch OR prefill selection → KV handoff → decode selection
       │ engine request                    KV metadata ──►        │
       │                                   KV payload  ══►        │
       ▼                                                        │
L4  Engine Frontend / Scheduler / KV Allocator
    tokenize or token IDs · waiting/running · token budget · block/page ownership
       │ scheduler output / model input                          │
       ▼                                                        │
L5  Model Runner / Parallel Ranks
    embedding · transformer layers · TP/PP/EP/DP · logits · sampling
       │ tensor ops                                              │
       ▼                                                        │
L6  Framework Dispatch / Compile
    PyTorch dispatcher · torch.compile · custom op · Triton/CUDA extension
       │ kernel launch descriptors                               │
       ▼                                                        │
[GPU]
L7  CUDA / Triton / NCCL Kernels
    gather · norm · RoPE · GEMM · attention · MoE · reduce · sampling
       │ warps load/compute/store                                │
       ▼                                                        │
L8  GPU Microarchitecture
    HBM ↔ L2 ↔ shared memory ↔ registers · SM · warp schedulers
    Tensor Core MMA · CUDA-core scalar/vector work · LD/ST units

[ASYNC CONTROL]
metrics · health · KV events · discovery · autoscaling · reconcile ··► L1/L2/L3/L4
```

各层最重要的所有权边界：

- L1 决定协议与治理，不拥有模型权重。
- L2 选择 endpoint，不等于 KV 数据必经路由器进程。
- L3 协调 worker 和 KV 交接，不替代引擎的 batch scheduler。
- L4 拥有请求队列、token budget 和逻辑 KV allocation。
- L5 把一个 iteration 变成各 rank 的 tensor 运算。
- L6/L7 决定具体实现、launch 和融合方式。
- L8 执行指令与数据移动；“GPU utilization 高”仍不能说明瓶颈属于哪类单元。

## 请求对象如何演化

一次请求不是以同一个对象穿过所有层。跨层调试时要先问“当前看到的对象属于哪一层”，否则很容易把 HTTP 字段、scheduler state、block table 和 CUDA pointer 混为一谈。

```text
[L0] OpenAI-compatible JSON
 messages · model · max_tokens · temperature · stream
       │ parse / validate / chat template
       ▼
[L1] Normalized request
 request_id · prompt · sampling params · tenant/session hints
       │ tokenize（位置因平台/engine 而异）
       ▼
[L2/L3] Route request
 token IDs or prefix hashes · candidate endpoints · route metadata
       │ dispatch / optional P-D coordination
       ▼
[L4] Engine request state
 prompt_token_ids · generated_token_ids · priority · arrival/deadline
       │ prefix lookup / KV allocation / schedule
       ▼
[L4/L5] Iteration batch
 scheduled token counts · slot mapping · block/page table · positions
       │ tensorize / copy metadata to device
       ▼
[L5/L6] Model inputs and op graph
 input_ids · hidden states · positions · KV views · attention metadata
       │ dispatch / compile / graph replay
       ▼
[L7/L8] Kernel work
 device pointers · strides · launch grid · stream · synchronization dependencies
       │ kernels produce logits
       ▼
[L5/L4] Sample result
 token id · logprobs · finish state · updated KV/request state
       │ detokenize / protocol encode
       ▼
[L1/L0] SSE chunk or final JSON
 delta content · usage · finish_reason
```

同一个 `request_id` 可以串起这些对象，但它通常不是 GPU kernel 参数。GPU 侧更多依赖 device pointer、shape、stride、block table、slot mapping 和 stream dependency。反过来，从 kernel trace 回到用户请求需要 engine trace、NVTX range 或 request metrics 建立关联。

## 聚合式与 P/D 的分叉

Prefill 和 Decode 在两种形态中都存在。差异是它们是否由同一 worker/engine instance 持有连续状态，以及 KV 是否跨角色或跨设备传输。

```text
                              normalized request
                                      │
                         route + admission + queue
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                  Aggregated                  P/D separated
             [same worker / pool]          [prefill role/pool]
                         │                         │
              prefix lookup + allocate     prefix lookup + allocate
                         │                         │
                 prefill kernels            prefill kernels
                         │                         │
             KV stays locally owned      handoff metadata ──► coordinator/decode
                         │              KV tensor payload ══► decode GPU/cache tier
                         │                         │
                 decode iterations          decode iterations
                         │                         │
                         └────────────┬────────────┘
                                      ▼
                            sampled token stream
```

### 聚合式

聚合式通常让同一个 scheduler 把 prefill、chunked prefill 和 decode work 放进 successive iterations。它省去跨 worker KV handoff，但长 prompt、短 decode、batch composition 和显存压力会在同一资源池竞争。Continuous batching 仍然可能让同一 GPU iteration 同时承载不同请求的 prefill chunk 与 decode token。

### P/D 分离式

P/D 将计算特性不同的阶段分配给不同角色：Prefill 更偏大矩阵吞吐和 TTFT，Decode 更偏单步延迟、KV 带宽及持续状态。它新增三个契约：

1. control metadata：request/rank/block/connector/session 信息如何匹配；
2. KV payload：哪些 layer/block、以什么 layout、经何种 transport 移动；
3. readiness：Decode 何时能够安全读取完整 KV 并开始首个 decode step。

P/D 不自动等于跨节点。它可以同进程不同角色、同节点跨 GPU，也可以跨节点经 RDMA/NIXL 等路径。网络、拓扑和 connector 版本决定 KV transfer 是否比重新 prefill 更划算。

## 控制面为什么不在 Token 热路径

平台要持续发现 endpoint、处理故障并调整副本，但这些动作通过状态与事件影响后续请求，不应被误画成每个 decode token 都等待一次 Kubernetes reconcile。

```text
HOT PATH（每个请求；decode 段可能每个 token 重复）

Client ──► Gateway ──► Route/Pick ──► Engine Queue ──► GPU Iteration ──► Token
                           ▲                ▲                 │
                           │                │                 │ metrics/events
                           │                │                 ▼
COLD / FEEDBACK PATH       │                │

Kubernetes API · Operator · HPA/KEDA · Planner · health/discovery · KV events
        │ reconcile desired workers         │ refresh readiness/load/index
        └································►┴································
```

控制面可能改变下一次 endpoint 候选集、现有 worker readiness 或队列容量，也可能触发 graceful drain。它不会为已经输出一部分 token 的请求自动提供无损迁移；是否能恢复取决于 KV、generated tokens、sampling state 和 backend 协议是否可重建。

## 箭头与执行位置约定

```text
request / token / synchronous metadata      A ──► B
event / metric / discovery / reconciliation A ··► B
KV tensor / activation / collective payload A ══► B

[CPU] host process or scheduler logic
[GPU] device-resident compute or memory operation
[NET] node/process/device transport boundary
```

这些符号表达“数据或控制关系”，不是性能保证。`══►` 表示 bulk data path，但实际实现可能用 GPU peer copy、CUDA IPC、NVLink、PCIe、RDMA、NIXL connector 或先落 CPU/cache tier；必须回到对应平台页的固定版本证据。

## 核心术语速查

| 术语 | 本学习路径中的精确定义 |
|---|---|
| Prefill | 对 prompt/context 执行前向计算并建立各层 KV；通常计算吞吐敏感 |
| Decode | 使用既有 KV 逐步生成 token；通常 ITL、KV 带宽和调度间隙敏感 |
| Continuous batching | scheduler 在 iteration 边界动态加入、继续、暂停或完成请求 |
| Chunked prefill | 将长 prompt 拆成多个调度 chunk，与其他 prefill/decode work 竞争预算 |
| Prefix cache | 复用相同 token prefix 已产生的 KV；命中位置和 worker 负载必须共同考虑 |
| PagedAttention | 用逻辑 block/page 与映射元数据组织非连续 KV，并让 attention backend 消费映射 |
| RadixAttention / RadixCache | 用 radix-tree 风格 prefix ownership/matching 管理可复用 KV；不是跨副本路由本身 |
| CUDA Graph | 捕获并重放相对稳定的 GPU launch DAG，减少 host launch overhead |
| TP / PP / EP / DP | tensor、pipeline、expert、data parallel；它们与跨实例 P/D 是不同维度 |
| NCCL | 多 GPU collective 通信库，常承载 all-reduce、all-gather、reduce-scatter、all-to-all |
| NIXL | 面向异构内存和网络的数据移动抽象之一，可用于 KV transfer；不执行 attention 计算 |
| TTFT | time to first token，包含入口、排队、prefill、handoff 和首 token 前的关键延迟 |
| ITL / TPOT | token 间延迟 / 每输出 token 时间，常受 decode iteration、batch 和通信影响 |

## 阅读顺序

### 按一个部署追到底

1. 从 [[aibrix-inference-request-flow]]、[[dynamo-inference-request-flow]] 或 [[llm-d-inference-request-flow]] 选择实际平台。
2. 在平台支持矩阵里确认 engine 与 aggregated/P-D 状态。
3. 沿平台时序走到 engine handoff，再进入 [[vllm-gpu-execution-path]] 或 [[sglang-gpu-execution-path]]。
4. 从 ModelRunner/attention/custom op 进入 [[llm-gpu-kernel-execution-path]]，检查 kernel、memory 和 collective。

### 按问题反向定位

- endpoint 选错、prefix 命中差、队列不均：从 [[inference-routing]] 与平台页 L1–L3 开始。
- TTFT 高：依次检查入口/排队、prefill scheduling、KV handoff、prefill GEMM/attention。
- ITL 抖动：检查 decode batch、CUDA Graph 命中、KV memory access、TP/EP collective 和 launch gap。
- GPU 利用率高但吞吐低：进入 GPU 页区分 memory-bound、compute-bound、communication-bound 与 occupancy 问题。
- P/D 后反而变慢：分别量化 route/queue、KV metadata、KV payload、readiness barrier 与 decode 首步，不只看传输带宽。

本页建立共同语言；项目事实以三个平台页和两个引擎页记录的固定 commit 为准。已有概念背景可从 [[llm-inference]]、[[disaggregated-serving]]、[[inference-routing]]、[[paged-attention]]、[[radix-attention]] 和 [[kv-cache-offload]] 继续阅读。
