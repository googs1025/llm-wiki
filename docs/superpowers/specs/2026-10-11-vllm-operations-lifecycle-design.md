---
title: vLLM 运维生命周期与生产 Runbook 设计
date: 2026-10-11
status: pending-user-review
---

# vLLM 运维生命周期与生产 Runbook 设计

## 1. 目标

本次扩展在现有“请求入口 → vLLM engine → CUDA”学习路径之外，增加“一个 vLLM 实例怎样启动、进入服务、释放资源、恢复、更新和退出”的运维主线。

目标读者是需要理解或操作 vLLM 生产服务的 AI Infra / Serving 工程师。内容同时回答两类问题：

1. 架构问题：每个生命周期动作改变了哪些状态，weights、KV cache、CUDA Graph、NCCL communicator、LoRA、scheduler queue 和 preload daemon 分别由谁拥有。
2. 操作问题：何时可以执行 Sleep/Preload/Reload/Shutdown，怎样 drain 请求，执行后检查什么，失败时如何定位和回滚。

## 2. 成功标准

1. 形成一个从 `STARTING → WARMING → READY → DRAINING/PAUSED → SLEEPING → WAKING → READY/FAILED → STOPPED` 的统一状态模型。
2. 明确普通 model load、`vllm preload`/`ipc_cache`、Sleep Level 0/1/2、partial wake、`reload_weights`、LoRA lifecycle 和 shutdown 的边界。
3. 用资源矩阵说明每个动作对 GPU weights、CPU backup、KV、CUDA Graph、NCCL、scheduler、requests 与 daemon 的影响。
4. 给出可执行的单机与 Kubernetes runbook，包括前置条件、命令、成功信号、失败信号、回滚和验证。
5. 区分 stable release、最新 upstream main、development endpoint 与外部平台/Kubernetes 能力；不把 main-only feature 描述成所有 release 已支持。
6. 使用固定 commit 的官方 vLLM 文档/源码作为版本敏感证据，并与 wiki 中较旧的 raw-backed Source 分开。
7. 新页面有 Index、Entity、Concept 入站链接，HTML/graph 同步，无新增断链和孤儿页。

## 3. 非目标

- 不写完整 Kubernetes operator；只说明 Pod/probe/rollout 与 vLLM process 生命周期的接口。
- 不把 AIBrix、Dynamo、llm-d 的控制面实现复制进 vLLM 页面；只链接它们如何调用 engine lifecycle。
- 不承诺所有 accelerator、executor、quantization、parallelism 或 connector 都支持同一 Sleep/Preload 组合。
- 不把 `vllm preload` 与 Linux `LD_PRELOAD`、LoRA preload、layer prefetch 或 kernel 内 preload 混为一谈。
- 不把 Preload 当作 KV cache、request state 或透明 failover；它只缓存当前实现支持的启动 artifacts，首要对象是模型权重。
- 不提供未经目标版本验证的 production endpoint 暴露建议。Development endpoints 必须保持内部可达，不对不可信用户开放。
- 不修改 `raw/` 或历史 Source 摘要，不在本次扩展中新增图片运行时。

## 4. 设计选择

### 4.1 两页分层

新增两个 Analysis 页面：

```text
[[vllm-operational-lifecycle]]
│  状态、资源所有权、动作语义、版本边界
│
└── [[vllm-production-operations-runbook]]
   命令、Kubernetes 流程、诊断、回滚、验证
```

采用两页而不是单篇超长页面，是为了让稳定心智模型与易变化的命令/endpoint 分开维护。也不拆成多个细页，避免 Sleep、Preload、Reload 与 drain 之间重复资源表和前置条件。

### 4.2 事实分类

每项版本敏感能力使用下列标签之一：

- `release-documented`：目标 stable release 的官方文档明确存在。
- `main-documented`：当前 upstream main 文档/代码存在，但未证明已进入 stable release。
- `development-endpoint`：需要 development mode 才可调用，不应暴露给用户。
- `integration-dependent`：行为取决于 executor、accelerator、connector、parallelism 或外部平台。
- `external-control-plane`：drain、Pod readiness、rollout、replica replacement 等由 Kubernetes/Gateway/operator 补齐。

页面页首记录核验日期、stable release/tag、upstream SHA 和所有 main-only 判断。

## 5. 页面一：`wiki/analysis/vllm-operational-lifecycle.md`

### 5.1 页面职责

建立 vLLM process/engine 的生命周期状态机和资源 ownership。读者读完后应能判断某个操作是在暂停 scheduler、释放 engine-owned GPU memory、缓存 daemon-owned weights、更新权重，还是终止整个 process。

### 5.2 核心章节

1. 当前版本与证据边界。
2. Process / Engine / Worker / Daemon ownership。
3. 启动路径：disk load 与 preload/ipc-cache。
4. Warmup、memory profile、KV allocation、CUDA Graph capture 与 ready。
5. 在线 serving 状态与请求 drain。
6. Sleep Level 0/1/2。
7. Partial wake 与 `tags` 顺序。
8. Weight reload / RLHF update。
9. Preload daemon 与 weight fingerprint。
10. `zero_copy` / `copy` cache modes。
11. LoRA adapter lifecycle。
12. Graceful shutdown / restart / rolling replacement。
13. 资源状态矩阵。
14. 失败状态与恢复边界。
15. 与 AIBrix/Dynamo/llm-d control plane 的接口。

### 5.3 状态机

```text
CREATED
   │ process + distributed init
   ▼
LOADING ── disk loader OR ipc_cache mapping
   │ weights ready
   ▼
WARMING ── memory profile · KV allocation · kernel warmup · graph capture
   │ readiness succeeds
   ▼
READY / SERVING
   │ stop admission + drain/abort/keep policy
   ▼
PAUSED / DRAINING
   ├── level 0 ───────────────► scheduler paused; memory resident
   ├── level 1 ───────────────► weights CPU-backed; KV discarded
   ├── level 2 ───────────────► weights/KV discarded; selected buffers retained
   └── shutdown ──────────────► STOPPED

SLEEPING
   │ partial/full wake + optional reload
   ▼
WAKING ── weights · kv_cache · scheduling tags
   ├── success ───────────────► READY
   └── mismatch/OOM/failure ──► FAILED / rollback
```

“READY” 同时需要 process 存活、model/engine 初始化完成、必要 memory resident 和入口候选状态允许。进程 `/health`、Kubernetes readiness 与外部 router membership 不是同一个状态变量。

### 5.4 资源矩阵

至少覆盖：

| 动作 | Scheduler | In-flight request | GPU weights | CPU weight backup | KV cache | CUDA Graph | NCCL | Process |
|---|---|---|---|---|---|---|---|---|
| Normal serve | running | active | resident | optional/no | resident | captured/eager | active | alive |
| Sleep L0 | paused | abort/wait/keep policy | resident | unchanged | resident unless separately released | resident | active | alive |
| Sleep L1 | paused | must reach safe boundary | released | retained | discarded | configurable | optionally suspended | alive |
| Sleep L2 | paused | must reach safe boundary | discarded | normally no full backup | discarded | configurable | optionally suspended | alive |
| Preload zero-copy | separate from scheduler | none | daemon-owned resident | no | none | autotune cache only | daemon group as needed | daemon alive |
| Preload copy | engine receives copy | none during load | engine-owned after copy | no | none | later engine warmup | engine-owned | daemon may release cache |
| Shutdown | stopped | drained/aborted | released | released | released | released | destroyed | exited |

具体 CUDA Graph/NCCL memory 释放取决于 flags 和 backend，不能把“Sleep 释放 90%+”变成每个配置的保证。

### 5.5 Sleep 与 Preload 的冲突

必须显式说明：

- Sleep 管理正在运行的 engine 及其 allocator-owned resources。
- Preload daemon 跨 engine restart 保持 GPU weight artifacts。
- `ipc_cache` 的默认 `zero_copy` mode 让 engine 映射 daemon-owned allocations；官方当前文档明确禁止在此模式使用 CuMemAllocator weight offload 的 Sleep Mode。
- `copy` mode 将 tensor clone 到 engine memory并让 daemon释放cache，ownership 不同，但会失去跨restart zero-copy常驻的主要收益；仍需按目标版本验证 Sleep 组合。

## 6. 页面二：`wiki/analysis/vllm-production-operations-runbook.md`

### 6.1 页面职责

给出按场景执行的操作手册。每个 runbook 使用相同模板：目的、适用版本、前置条件、命令/动作、成功信号、失败信号、回滚、请求语义和资源检查。

### 6.2 Runbook 范围

1. 普通 `vllm serve` 启动前检查。
2. Model artifact / tokenizer / revision / quantization / parallelism 锁定。
3. Weight download/load 与 startup memory profiling。
4. `vllm preload` daemon 启动、health、engine `ipc_cache` 接入和 fallback。
5. Sleep L0 pause、只释放 KV、Sleep L1、Sleep L2。
6. Full/partial wake、weights reload 与恢复 serving。
7. LoRA load/unload 与 capacity boundary。
8. 安全 drain、graceful shutdown、rolling restart/upgrade。
9. Kubernetes startup/readiness/liveness probes。
10. OOM、daemon/socket、fingerprint mismatch、wake failure、KV not restored、NCCL memory、request queue 和 stream interruption 诊断。
11. 回滚与 post-operation verification。

### 6.3 Runbook 示例结构

```text
Operation: Sleep Level 1

PRECHECK
  feature enabled · internal endpoint only · admission stopped
  in-flight policy selected · CPU RAM enough for weights

EXECUTE
  POST /sleep?level=1&mode=<abort|wait|keep>

VERIFY
  scheduler paused · /is_sleeping true
  GPU memory decreases · KV invalidated · process remains healthy

RECOVER
  POST /wake_up
  wait until all allocations resident and scheduling resumed

POSTCHECK
  health/readiness · smoke inference · TTFT warmup effect · no stale requests
```

### 6.4 Kubernetes 顺序

```text
remove from routing / readiness false
   → stop new admission
   → drain or abort by explicit policy
   → wait for stream/transfer cleanup
   → sleep/update/restart process
   → load/warm/wake
   → startup checks
   → readiness true
   → return to routing
```

Probe 设计需要区分：

- liveness：process 是否还活着；不能因模型正在加载就反复重启。
- startup：允许大模型加载、quantization、warmup 和 graph capture 需要的时间。
- readiness：当前是否可以安全接收新请求；sleeping/draining/failed worker 应退出候选集。

## 7. 图表体系

预计新增 12–16 张 ASCII 图：

| 页面 | 图 |
|---|---|
| Lifecycle | 总状态机、进程/daemon ownership、disk vs preload startup、Sleep levels、partial wake、weight update、LoRA、shutdown |
| Runbook | 启动检查、K8s drain/rollout、Sleep L1/L2 sequence、Preload sequence、diagnostic tree、rollback/verification |

图中继续使用现有约定：

- `──►` 请求或同步控制；
- `··►` metrics/readiness/reconcile；
- `══►` weights/KV 等 bulk data；
- `[CPU]`、`[GPU]`、`[NET]` 明确执行/存储位置。

## 8. 与现有 wiki 的连接

修改：

- `wiki/entities/vllm.md`：新增“运维生命周期入口”，不复制 runbook。
- `wiki/concepts/llm-serving-reliability.md`：链接 drain、sleep、restart 和 stream failure 的 vLLM 实例化。
- `wiki/concepts/model-serving-operator.md`：说明 operator/controller 与 engine lifecycle action 的接口。
- `wiki/analysis/vllm-gpu-execution-path.md`：从 worker/allocator 指向 operational lifecycle。
- `wiki/analysis/llm-inference-request-lifecycle.md`：在异步 control path 衔接运维阅读。
- `wiki/index.md`：增加两页和“vLLM 运维”阅读路径。
- `wiki/log.md`：追加一次 query operation。
- 重建 `wiki/html/` 和 graph。

不新建泛化 Concept，因为现有 `[[llm-serving-reliability]]` 与 `[[model-serving-operator]]` 已能承载跨项目稳定机制；新页面聚焦 vLLM-specific operational contracts。

## 9. 证据策略

实施时重新解析：

- official `vllm-project/vllm` stable release/tag；
- official upstream main commit；
- `docs/features/sleep_mode.md`；
- `docs/features/preload.md`；
- sleep API/EngineCore/GPUWorker/SleepModeBackend；
- preload CLI/weight cache daemon/IPC cache loader；
- health/readiness/server lifecycle、weight reload、LoRA management、distributed shutdown 相关代码和文档。

每个页面页首列出 release 与 main 两条证据。Main-only 功能必须带 `main-documented`，不能仅因代码在 main 就写成“当前稳定版默认支持”。

## 10. 正确性边界

- Sleep 暂停/释放 engine resources，不等于 Pod/进程自动退出路由候选。
- `/health` 成功不必然等于 ready to accept new inference；外部 readiness 必须包含生命周期状态。
- Sleep L1 丢弃 KV，wake 后旧 prefix/request state不能继续当作有效。
- Sleep L2 不保留旧 weights，wake 后需要 reload/new weight path；partial wake顺序用于控制峰值显存。
- Preload cache权重，不缓存KV、request queue、sampling state或TCP stream。
- `zero_copy` IPC weights归daemon所有，daemon生命周期影响engine mappings。
- Fingerprint mismatch时默认fallback到disk不等于用户一定察觉；runbook必须检查日志和startup latency。
- Rolling upgrade需要先drain/退出routing，再处理engine；Kubernetes termination本身不保证请求语义。
- 已输出token的request在restart后不能假设透明继续。
- 多rank操作需要所有相关workers一致完成；部分rank sleep/wake/reload失败必须整体隔离。

## 11. 验证策略

### 11.1 内容契约

- 两个新页面frontmatter完整，date与固定证据存在。
- Lifecycle页包含状态机、ownership表、Sleep L0/L1/L2、partial wake、reload、preload modes与冲突说明。
- Runbook页包含startup、health/readiness、drain、Sleep、Preload、reload、shutdown、Kubernetes、diagnostics、rollback和postcheck。
- 至少12张ASCII图，每张有前置条件和正文解释。
- 所有命令标注适用版本/模式，不把dev endpoints包装成默认production API。

### 11.2 自动测试

扩展 `wiki/html-assets/test_request_to_cuda.py` 或新增聚焦的 operations test，验证：

- 必需headings、术语、版本标签和resource matrix；
- `zero_copy` + Sleep incompatibility warning；
- Index/Entity/Concept入站链接；
- 无新增missing wikilink；
- raw与hand-crafted HTML保持；
- 生成HTML存在且本地links/graph edges有效。

### 11.3 构建与人工检查

- 使用最新 main builder 声明的 `uv` 环境运行测试和构建。
- 连续构建两次，输出hash一致。
- 桌面/窄屏检查状态图、命令块、资源矩阵和diagnostic tree。
- `git diff --check`，PR保持mergeable，CI build通过。

## 12. 提交与 PR 边界

设计、计划和实现提交位于独立分支 `feature/vllm-operations-lifecycle`，完成后创建一个以最新 `main` 为 base 的新 PR。PR #49 已合并且不承载本扩展。实现完成后的 durable commit 使用：

```text
query: Add vLLM operations lifecycle and runbook
```

不force-push已合并的main历史；只正常追加提交。若main在实施期间前进，完成前再次fetch/rebase并用`--force-with-lease`更新新feature branch。
