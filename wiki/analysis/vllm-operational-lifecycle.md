---
title: vLLM 运维生命周期：启动、Preload、Sleep、更新与退出
tags: [analysis, vllm, llm-serving, operations, lifecycle, gpu-memory, reliability]
date: 2026-10-12
sources: []
related: ["[[vllm]]", "[[vllm-gpu-execution-path]]", "[[llm-inference-request-lifecycle]]", "[[llm-serving-reliability]]", "[[model-serving-operator]]", "[[gpu-programming-learning]]"]
---

# vLLM 运维生命周期：启动、Preload、Sleep、更新与退出

本页解释一个 vLLM 实例如何从 process 创建走到 serving、暂停、释放 GPU memory、恢复、更新权重和退出。主线不是“有哪些命令”，而是每个动作改变了哪些 owner 的状态：API process、EngineCore、GPU workers、preload daemon、外部 Gateway/Kubernetes 分别掌握什么。

可执行命令和故障排查由配套的 vLLM production operations runbook 承载；单次请求在 engine 内的调用链见 [[vllm-gpu-execution-path]]。

## 版本与证据边界

核验日期：2026-10-12。

| 证据面 | 固定版本 | 本页用法 |
|---|---|---|
| Stable release | [v0.31.0](https://github.com/vllm-project/vllm/releases/tag/v0.31.0)，2026-10-05 发布 | Sleep、Preload、IPC loader 等 release-documented 合同 |
| Upstream main | [`c85616efc6f0eaa50ca1f1a09c32368aedffd3d8`](https://github.com/vllm-project/vllm/tree/c85616efc6f0eaa50ca1f1a09c32368aedffd3d8) | main-documented 增量能力和最新源码形状 |
| 历史 wiki Source | [[src-vllm-architecture]] | 2026-09 本地代码快照，不覆盖本页的 0.31.0 判断 |

本页采用五种证据标签：

- `release-documented`：v0.31.0 tag 的官方文档或源码直接支持。
- `main-documented`：固定 main commit 存在，但不能倒推所有 stable release。
- `development-endpoint`：仅在 server development mode 暴露。
- `integration-dependent`：取决于 accelerator、executor、parallelism、connector 或 loader。
- `external-control-plane`：需要 Gateway、Kubernetes 或 operator 补齐。

### 固定源码入口

| 生命周期环节 | v0.31.0 固定入口 |
|---|---|
| Sleep 使用说明 | [`docs/features/sleep_mode.md`](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/features/sleep_mode.md) |
| Preload 使用说明 | [`docs/features/preload.md`](https://github.com/vllm-project/vllm/blob/v0.31.0/docs/features/preload.md) |
| Scheduler/worker dispatch | [`vllm/v1/engine/core.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/v1/engine/core.py) / [`gpu_worker.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/v1/worker/gpu_worker.py) |
| Sleep backend | [`sleep_mode_backend.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/device_allocator/sleep_mode_backend.py) |
| Preload CLI/daemon | [`preload.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/entrypoints/cli/preload.py) / [`daemon.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/model_loader/weight_cache/daemon.py) |
| IPC loader | [`ipc_loader.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/model_loader/weight_cache/ipc_loader.py) |
| Dev Sleep API | [`sleep/api_router.py`](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/entrypoints/serve/dev/sleep/api_router.py) |

## Lifecycle 状态机

```text
CREATED
   │ process/distributed init
   ▼
LOADING
   ├── disk/object-store loader
   └── preload daemon → ipc_cache map/copy
   │ weights constructed and validated
   ▼
WARMING
   │ memory profile · KV allocation · kernel warmup · optional graph capture
   ▼
READY / SERVING
   │ external admission off · request policy chosen
   ▼
DRAINING / PAUSED
   ├── Sleep L0 ─────────────► PAUSED, memory stays resident
   ├── Sleep L1 ─────────────► SLEEPING, weights CPU-backed, KV discarded
   ├── Sleep L2 ─────────────► SLEEPING, weights/KV discarded
   └── process shutdown ─────► STOPPED

SLEEPING
   │ wake tags / reload / allocate KV
   ▼
WAKING
   ├── all ranks succeed + warm check ──► READY
   └── mismatch/OOM/rank failure ───────► FAILED → rollback/restart
```

状态机有两个层次：vLLM engine 的真实 scheduler/memory state，以及 `external-control-plane` 对入口的 serving eligibility。Engine 进入 Sleep 不会自动修改 Kubernetes readiness 或 Gateway endpoint membership；外部系统必须先停止新流量并在恢复验证后重新放行。

## Process / Engine / Worker / Daemon 所有权

```text
[API Server process]
HTTP/gRPC · tokenizer/request preprocessing · client streams
        │ EngineCoreClient
        ▼
[EngineCore process]
Scheduler queues · Request state · KV logical ownership · pause state
        │ executor RPC/direct calls
        ▼
[GPU Worker rank(s)]
model object · weights · KV tensors · CUDA Graph · device allocator
        │ collectives
        └══► peer TP/PP/DP/EP ranks

[Preload daemon process per GPU]
post-quantized rank shard · CUDA IPC handles · Unix socket · fingerprint
        │ map/copy weights only
        └══► GPU Worker

[External control plane]
Pod/process lifecycle · readiness · routing membership · replica replacement
        ··► API/Engine/Daemon actions
```

关键边界：

- API Server持有连接和流，不拥有GPU weights/KV。
- EngineCore持有调度/请求逻辑，不能单独释放worker显存。
- 每个GPU Worker执行Sleep backend并拥有本rank device state。
- Preload daemon不是vLLM serving engine；它没有request queue、KV cache和sampling state。
- Kubernetes/Gateway决定是否把新request送来，但不能凭Pod状态推断所有rank已完成wake。

## 普通启动与 Preload 启动

### 普通加载

```text
checkpoint / model repository
        │ download/read
        ▼
each worker builds model
        │ load rank shard
        │ quantization post-processing
        ▼
engine-owned GPU weights
        │ warmup/profile/KV allocation
        ▼
READY
```

这是默认所有权：weights由engine worker allocation持有，process退出就释放。

### `vllm preload` + `ipc_cache`

`release-documented`（v0.31.0）：

```text
vllm preload launcher
  └── daemon per local GPU/rank
       checkpoint → shard → post-quantize → daemon GPU allocation
                                          │ export CUDA IPC handles
                                          │ bind private Unix socket when ready
                                          ▼
vllm serve --load-format ipc_cache
  └── worker builds meta model
       ├── compare weight fingerprint + GPU UUID
       ├── zero_copy: map daemon tensors
       └── copy: clone to engine allocation; daemon releases cache
```

Preload优化的是engine restart的weight load与post-processing。它不保留KV、请求、CUDA Graph executable、scheduler queue或客户端连接。Fingerprint覆盖checkpoint content metadata、model architecture、dtype、quantization、parallel layout、revision与vLLM version；不匹配时默认fallback到disk，除非显式关闭fallback。

## Warmup 与 Ready

```text
weights available
   │
   ├── determine/profile usable GPU memory
   ├── allocate KV cache / workspace
   ├── initialize attention and custom-op backends
   ├── compile/JIT/download kernels as configured
   ├── dummy/profile runs
   └── optional CUDA Graph capture / FlashInfer autotune
            │
            ▼
engine can execute smoke request
            │
            ├··► process health
            ├··► engine readiness
            ├··► Kubernetes readiness
            └··► router membership
```

“Process alive”只说明进程未退出；“Ready”至少应包含model/weights可用、所有必要ranks可通信、KV/runner初始化完成且engine允许调度。Preload daemon的`/health`只表示daemon ranks已缓存并serving，不等价于engine ready。

`main-documented`：固定 main 文档还描述可选CUDA Graph memory offload和实验性NCCL communicator suspend。它们不是v0.31.0本页基础矩阵的默认假设，采用前必须核验目标main/release、backend与driver/NCCL版本。

## Drain 与 Pause

```text
external router
   │ remove endpoint / readiness=false
   ▼
stop new admission
   │
   ├── abort: terminate accepted requests
   ├── wait: stop new work and drain existing requests
   └── keep: pause all; retained requests need safe recomputation/resume semantics
   │
   ▼
EngineCore scheduler reaches requested pause boundary
   │ output queue / transfer / worker work safe
   ▼
memory lifecycle action may begin
```

`release-documented`：当前Sleep API的`mode`决定已有请求处理方式，具体in-process/async engine限制需按调用路径验证。运维系统不能在仍有GPU work或P/D transfer访问同一allocation时直接free memory。

已向client发送token的stream若因abort/restart中断，不能假设可在另一实例透明续写；参见 [[llm-serving-reliability]]。

## Sleep Level 0/1/2

`release-documented`：

```text
Level 0
  scheduler: PAUSED
  GPU weights: keep
  KV physical memory: keep (unless separately release_kv_cache_memory)
  process: alive

Level 1
  scheduler: PAUSED
  GPU weights: release; contents backed in CPU RAM
  KV cache: discard
  intended wake: restore same model weights + allocate fresh KV

Level 2
  scheduler: PAUSED
  GPU weights: discard (selected buffers may be CPU-saved)
  KV cache: discard
  intended wake: allocate weights region → load/update weights → allocate KV
```

Level 1要求足够host memory保存weights。Level 2降低host backup压力，适合不同权重或RLHF更新，但不能仅调用full wake就假定旧weights自动回来；文档路径要求partial wake weights、reload，再wake KV。

只释放KV是独立路径：先完成Level 0 pause且executor memory全部resident，再`release_kv_cache_memory()`，最后`wake_up(tags=["kv_cache"])`。保留的request需要重算被丢弃的KV，不能沿用旧block内容。

## Partial Wake 与 Reload Weights

```text
Sleep Level 2
   │ old weights/KV absent
   ▼
wake_up(tags=["weights"])
   │ allocate weight regions only; scheduler remains paused/is_sleeping
   ▼
collective reload/update on every worker rank
   │ verify version/layout/checksum + all ranks success
   ▼
wake_up(tags=["kv_cache"])
   │ allocate/init fresh KV capacity
   ▼
optional warmup/smoke
   │
wake scheduling / external readiness=true
```

Tags `weights`、`kv_cache`、`scheduling` 是不同资源/控制面。Partial wake期间`is_sleeping`仍应视为true，直到所有必需allocation恢复且scheduler可运行。Multi-rank update必须整体成功；单rank failure时整个serving group退出readiness并rollback或restart，不能继续接流量。

## Preload Cache Modes

`release-documented`：

| Mode | Weight owner | Engine行为 | Daemon行为 | 重启收益 | Sleep关系 |
|---|---|---|---|---|---|
| `zero_copy`（默认） | preload daemon | 直接映射daemon CUDA allocations | engine生命周期内保持alive | 最快，额外copy/显存副本最少 | **不兼容CuMemAllocator weight offload** |
| `copy` | engine worker | clone到自己的GPU allocation | handoff后释放cache | 免disk/post-process但仍有GPU copy | ownership更适合engine管理，仍需目标版本验证 |

> [!warning] `zero_copy`不能与Sleep Mode的weight offload组合。IPC weights属于daemon allocation，不属于engine的Sleep allocator；尝试把daemon-owned权重当作engine-owned释放会破坏ownership合同。

```text
zero_copy:
Daemon GPU weights ══ CUDA IPC mapping ══► Engine tensor views
      │ daemon exits → mappings/lifetime at risk
      └── Sleep allocator does not own these allocations

copy:
Daemon GPU weights ══ GPU copy ══► Engine-owned weights
      └── release daemon cache       └── normal engine ownership
```

v0.31.0 Preload支持CUDA/ROCm、TP/EP/DP及跨节点组合，但daemon不支持PP；CUDA IPC仍是node-local，每个node只服务自己的local GPU shards。具体quantization必须声明支持post-processed weights。

## LoRA 生命周期

```text
base engine READY
   │ add/load LoRA request
   ▼
adapter validate/load → worker LoRA manager → adapter resident/available
   │ requests reference adapter identity
   ▼
in-flight adapter requests complete
   │ remove/unload after no unsafe users
   ▼
adapter capacity returned
```

LoRA preload在这里指`add_lora`提前加载adapter，和CLI `vllm preload` weight-cache daemon不是同一功能。Adapter registry/residency通常随engine process；restart/scale-out后由`external-control-plane`重新声明/加载，不能假设新replica继承内存状态。

Sleep与LoRA的保留行为依实际allocator/tag/backend和版本，属于`integration-dependent`；运维前应通过目标配置验证adapter在wake后仍可用或显式重载。

## Shutdown 与 Restart

```text
remove from external routing
   → stop admission
   → drain/abort according to request contract
   → wait output queues and async transfers
   → unregister/close endpoints
   → stop workers and collectives
   → release KV/weights/graphs/workspaces
   → unlink sockets / terminate daemon if desired
   → process STOPPED

restart
   → choose disk or preload path
   → warm/readiness/smoke
   → re-enter routing
```

`external-control-plane`负责Pod termination ordering、grace period、replacement和Gateway候选传播。SIGTERM不会自动证明client streams已完成；termination grace必须覆盖drain与engine teardown，超时后的强杀应作为显式失败计数。

若使用`zero_copy` Preload，engine restart期间daemon应继续存活；若要释放GPU，则daemon也必须终止。Daemon SIGINT/SIGTERM会终止所有rank、unlink sockets并释放其weights。

## 资源状态矩阵

| 状态/动作 | Scheduler | In-flight requests | GPU weights | CPU backup | KV cache | CUDA Graph | NCCL | Process/Daemon |
|---|---|---|---|---|---|---|---|---|
| Normal serve | running | active | engine/daemon resident | optional | resident | captured/eager | active | engine alive |
| Drain | no new external traffic | finish/abort policy | resident | unchanged | resident | resident | active | alive |
| Sleep L0 | paused | mode-dependent | resident | unchanged | resident | resident | active | alive |
| L0 + release KV | paused | retained work must recompute | resident | unchanged | discarded | resident | active | alive |
| Sleep L1 | paused | safe boundary required | released | full weights retained | discarded | backend/flag-dependent | default remains; main option may suspend | alive |
| Sleep L2 | paused | safe boundary required | discarded | selected buffers/frozen params only | discarded | backend/flag-dependent | default remains; main option may suspend | alive |
| Partial weight wake | paused | none should run | allocated/reloaded | consumed/replaced | absent | not ready | rank-consistent | alive, still sleeping |
| Preload zero-copy | separate | none | daemon-owned | none | none | autotune cache only | daemon group as configured | daemon must live |
| Preload copy handoff | engine loading | none | engine-owned after clone | none | none | later warmup | engine-owned | daemon cache released |
| Shutdown | stopped | drained/failed | released | released | released | released | destroyed | exited |

CUDA Graph/NCCL列故意标出backend/flag差异：不要用一个“Sleep释放率”推断某块memory必然被释放。

## 失败与恢复边界

| 失败 | 可见信号 | 安全行为 |
|---|---|---|
| Preload daemon未ready/socket缺失 | connect timeout、daemon health 503 | 默认disk fallback并告警；若禁止fallback则保持unready |
| Fingerprint/GPU UUID mismatch | cache unusable/mismatch log | 拒绝错误mapping，fallback或fail |
| Sleep前仍有unsafe work | pause/drain未完成、transfer outstanding | 不进入memory release，等待或abort |
| L1 CPU RAM不足 | offload OOM/host pressure | 保持实例隔离，恢复或改用L2/restart |
| Wake OOM | allocation/resume失败 | whole group unready，rollback/restart |
| 一个rank失败 | collective/RPC timeout、rank error | 所有ranks退出routing，不允许partial service |
| Reload layout/version不匹配 | missing/mismatched tensors、collective error | 不恢复scheduling，回滚旧revision或restart |
| Daemon在zero-copy engine期间退出 | IPC allocation lifetime failure/engine error | 隔离engine并restart；不能把mapping当作durable weights |
| Stream已输出后restart | truncated/reset response | 返回中断，不透明replay |

恢复的共同条件是owner确认状态，而不是只看外部Pod仍为Running。

## 外部控制面接口

```text
Gateway / Router
  ··► endpoint admission on/off
Kubernetes / Operator
  ··► Pod lifecycle · readiness · rollout · grace period
Metrics / Observability
  ··► queue · in-flight · sleep state · memory · errors
             │
             ▼
vLLM lifecycle action
  ──► pause/drain/sleep/wake/reload/shutdown
             │ verified state
             └··► readiness/membership update
```

[[model-serving-operator]] 或 AIBrix/Dynamo/llm-d 可以编排这些动作，但不能改变vLLM内部ownership：它们应把engine state反馈到readiness，再决定扩缩/rollout。完整操作顺序由配套production runbook展开。
