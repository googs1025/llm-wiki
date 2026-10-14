---
title: vLLM 生产运维 Runbook：启动、Drain、Sleep、Preload 与升级
tags: [analysis, vllm, llm-serving, operations, runbook, kubernetes, reliability]
date: 2026-10-12
sources: []
related: ["[[vllm-operational-lifecycle]]", "[[vllm]]", "[[llm-serving-reliability]]", "[[model-serving-operator]]", "[[vllm-gpu-execution-path]]", "[[llm-serving-performance]]"]
---

# vLLM 生产运维 Runbook：启动、Drain、Sleep、Preload 与升级

本页把 [[vllm-operational-lifecycle]] 的状态和资源 ownership 变成可执行步骤。命令以 vLLM v0.31.0 为基线；执行前必须用目标镜像的 `vllm --help`、固定版本文档和 staging 验证实际 flags/endpoints。

## 使用方式与版本标签

统一操作模板：

```text
PRECHECK
  → REMOVE FROM ROUTING
  → DRAIN/POLICY
  → EXECUTE
  → VERIFY
  → RECOVER/ROLLBACK
  → POSTCHECK
```

| 标签 | 运维含义 |
|---|---|
| `release-documented` | v0.31.0 tag 有官方文档/实现；仍需检查目标部署版本 |
| `main-documented` | 只按固定 main commit使用；不能直接用于stable image |
| `development-endpoint` | 必须隔离在内部管理面，不能暴露给不可信客户端 |
| `integration-dependent` | accelerator/executor/parallelism/connector决定实际行为 |
| `external-control-plane` | 由Gateway/Kubernetes/operator实现，不是vLLM内建事务 |

每个操作都要回答：当前能否接新请求、已有请求怎样结束、哪些GPU/CPU状态改变、全部ranks是否一致、失败后怎样回到已知状态。

## 启动前检查

### PRECHECK

- 锁定image/vLLM version、model revision、tokenizer revision和chat template。
- 锁定dtype、quantization、load format、TP/PP/DP/EP topology和GPU型号。
- 验证checkpoint完整性、磁盘/网络吞吐、HF token和本地cache权限。
- 预算weights、KV、workspace、CUDA Graph/NCCL与系统保留显存。
- 明确startup timeout；不要用过短liveness把正常model load当成hung。
- 若用P/D或offload，固定connector、KV layout与transfer backend版本。

```text
artifact identity
model + revision + tokenizer + quantization + vLLM version
        │
parallel identity
TP/PP/DP/EP ranks + GPU UUID/topology
        │
memory budget
weights + KV + workspace + graph + NCCL + headroom
        │
        ▼
start is authorized
```

失败策略要在启动前选定：fail fast、fallback disk loader、回滚旧revision，或保持Pod unready等待人工处理。

## 普通启动

`release-documented` 基础形态：

```bash
vllm serve /models/my-model \
  --revision <immutable-revision> \
  --tokenizer-revision <immutable-revision> \
  --tensor-parallel-size <tp> \
  --dtype <dtype> \
  --port 8000
```

### EXECUTE

1. 启动process和distributed ranks。
2. 等待weights load/post-process。
3. 等待memory profile、KV allocation、kernel warmup/graph capture。
4. 只在所有ranks成功且smoke request通过后设为ready。

### VERIFY

- process未退出，所有worker ranks存在且collectives建立；
- `/health`或目标release的等价health检查成功；
- `/v1/models`包含预期model identity；
- deterministic smoke prompt得到非空结果；
- GPU weights/KV capacity与配置匹配，无fallback/OOM/error日志；
- TTFT首轮warmup影响和稳态延迟分别记录。

### RECOVER/ROLLBACK

启动失败时不要反复liveness重启形成下载/加载风暴。先隔离revision，保留日志与GPU OOM/driver evidence；恢复旧image/model/config后重新走完整startup验证。

## Preload Daemon

`release-documented`（v0.31.0）：Preload适合GPU继续专供同一weight artifact、但engine process需要快速restart的场景。

### PRECHECK

- CUDA/ROCm平台；TP/EP/DP按文档支持，v0.31.0 daemon拒绝PP。
- Daemon与engine必须同vLLM version、model/revision、dtype、quantization和rank layout。
- Unix socket目录仅同一可信用户可访问；协议使用pickle，不是远程多租户API。
- 默认`zero_copy`不能与Sleep Mode weight offload组合。

### EXECUTE

```bash
vllm preload \
  --model /models/my-model \
  --tensor-parallel-size 4 \
  --weight-cache-health-port 8100
```

Daemon本身必须从disk加载，不能给`vllm preload`传`--load-format ipc_cache`。

确认daemon ready后启动engine：

```bash
vllm serve /models/my-model \
  --tensor-parallel-size 4 \
  --load-format ipc_cache \
  --model-loader-extra-config '{"mode":"zero_copy","fallback":true}'
```

```text
daemon ranks load/post-process
   │ all ranks ready + sockets bound
   ▼
daemon /health = 200
   │
engine requests cached tensors
   ├── fingerprint/GPU UUID match → map/copy
   └── unavailable/mismatch → disk fallback or fail
   │
engine warmup/readiness
```

### VERIFY

- Daemon parent health 200且所有rank processes存活；
- engine日志明确显示mapped tensor数量和mode；
- 没有`Weight cache unusable ... falling back to disk loading`告警；若允许fallback，必须把fallback计为性能事件；
- engine与daemon GPU UUID/socket owner正确；
- restart latency相对普通load符合预期，但输出正确性不依赖startup更快这一点。

### RECOVER/ROLLBACK

- socket/daemon未ready：修复daemon；或接受disk fallback。
- fingerprint mismatch：不要绕过校验；统一配置/revision后重启。
- `zero_copy` daemon退出：立刻移除engine流量并重启engine/daemon组合。
- 需要释放daemon GPU memory：先停止依赖它的zero-copy engines，再终止daemon。

## Health、Startup 与 Readiness

```text
liveness
  process/event-loop alive?
        │ independent
startup
  weights + warmup + all ranks + smoke ready before timeout?
        │ gates
readiness
  safe to accept NEW traffic now?
        │
router membership
  has endpoint removal/addition propagated?
```

### Kubernetes probe原则

- startup probe覆盖最长合法model load、quantization、compile和graph capture。
- liveness只检测不可恢复process failure；loading或sleeping不应被当作dead loop。
- readiness在STARTING、DRAINING、PAUSED、SLEEPING、WAKING、FAILED时为false。
- `/health`成功不自动代表业务ready；用wrapper/sidecar/operator组合engine lifecycle state。
- Preload daemon有独立health；daemon ready不代表engine ready。

`external-control-plane`需要把readiness变化先传播到Gateway/Service endpoints，再开始释放memory或终止process。

## 安全 Drain

### REMOVE FROM ROUTING

先把endpoint设为不接新流量，并等待Gateway/EndpointSlice/LB传播；仅修改本地变量而不停止外部选点会继续收到新请求。

### DRAIN/POLICY

选择一种语义并记录：

- `wait/drain`：已接受请求完成，适合滚动升级；受最长output/deadline约束。
- `abort`：显式终止请求，适合紧急回收；客户端看到失败/断流。
- `keep/pause`：保留scheduler state只适用于实现支持的重算/恢复路径；KV被释放后必须重算。

```text
readiness=false / endpoint removed
   │ wait propagation
   ▼
new request count → 0
   │
in-flight requests ──► drain OR abort OR documented keep
   │
output queue + P/D transfer + GPU work safe
   ▼
lifecycle mutation allowed
```

已输出token的stream不能在restart后透明续传。若被中断，应让client看到truncated/error stream，并用request/attempt ID关联。

## Sleep Level 0

用途：暂停scheduler但保持GPU memory resident，常作为只释放KV前置步骤或短暂停流。

### EXECUTE

Python API：

```python
llm.sleep(level=0, mode="keep")
```

Online server的Sleep API属于`development-endpoint`：

```bash
VLLM_SERVER_DEV_MODE=1 vllm serve /models/my-model --enable-sleep-mode
curl -X POST 'http://127.0.0.1:8000/sleep?level=0&mode=keep'
```

Development endpoints包含可导致DoS或执行collective RPC的能力，只能绑定/授权在可信管理面。

### VERIFY

- scheduler pause完成而非仅请求已发送；
-新请求不执行；根据mode验证已有请求状态；
- GPU weights/KV仍resident，显存不应显著下降。

### RECOVER/ROLLBACK

```bash
curl -X POST 'http://127.0.0.1:8000/wake_up?tags=scheduling'
```

恢复外部readiness前运行smoke request。

## 只释放 KV Cache

用途：保留weights，释放KV physical memory；比L1更少搬运weights。

### PRECHECK

- 已完成`level=0, mode=keep` pause；
- executor所有其他memory仍resident；
- backend支持selective KV discard；
- 接受被保留requests醒来后重算KV。

### EXECUTE

```bash
curl -X POST 'http://127.0.0.1:8000/release_kv_cache_memory'
```

### VERIFY

- 返回`kv_cache_released`或目标版本等价成功；
- GPU memory下降与配置的KV capacity相符；
- repeated release/full sleep/partial wake中的非法调用被拒绝。

### RECOVER/ROLLBACK

```bash
curl -X POST 'http://127.0.0.1:8000/wake_up?tags=kv_cache'
```

确认KV重新分配、保留请求按实现重算、prefix cache不报告旧内容。

## Sleep Level 1

用途：同一模型稍后恢复；weights备份到CPU，KV丢弃。

### PRECHECK

- 已从外部路由移除并完成请求策略；
- host RAM足以存放weights backup；
- load format不是`ipc_cache`默认`zero_copy`。

> [!warning] `zero_copy`不能与Sleep Mode weight offload组合：weights由preload daemon拥有，engine的CuMemAllocator无权备份/释放这些IPC allocations。

### EXECUTE

```bash
curl -X POST 'http://127.0.0.1:8000/sleep?level=1&mode=abort'
```

### VERIFY

- `/is_sleeping`为true；
- GPU weight/KV allocations释放，CPU RAM上升符合weight size；
- process和所有rank仍alive；
- KV/prefix state视为无效。

### RECOVER/ROLLBACK

```bash
curl -X POST 'http://127.0.0.1:8000/wake_up'
```

若任何单个rank恢复失败，整个实例组必须退出routing并重启或回滚；不能让部分rank继续服务。

## Sleep Level 2 与权重更新

用途：丢弃旧weights/KV，加载不同或更新后的weights，避免完整weights CPU backup。

### EXECUTE

```bash
curl -X POST 'http://127.0.0.1:8000/sleep?level=2&mode=abort'
curl -X POST 'http://127.0.0.1:8000/wake_up?tags=weights'
curl -X POST 'http://127.0.0.1:8000/collective_rpc' \
  -H 'Content-Type: application/json' \
  -d '{"method":"reload_weights"}'
curl -X POST 'http://127.0.0.1:8000/wake_up?tags=kv_cache'
```

### VERIFY

- partial weight wake时scheduler仍不接请求；
- reload在所有ranks使用同revision/layout并全部成功；
- KV是新分配的空cache；
- model identity/checksum/smoke output与目标revision一致；
- `/is_sleeping`只在全部必要components恢复后转false。

### RECOVER/ROLLBACK

保留旧immutable artifact/image。任意rank reload失败时，整个serving group unready，终止本轮update并用旧revision完整restart；不要混合新旧rank权重。

## Wake 与恢复流量

```text
wake/allocate/reload all ranks
   │
   ├── resource verification
   ├── health + is_sleeping/is_paused state
   ├── deterministic smoke
   ├── optional warmup and latency sample
   └── no stale KV/request assumptions
           │
           ▼
readiness=true
   │ wait endpoint propagation
   ▼
gradual traffic → observe errors/TTFT/ITL/memory
```

### POSTCHECK

- 用低流量canary而非一次性全量恢复；
- 观察request queue、GPU memory、KV utilization、worker/rank errors；
- 区分first-request warmup latency与稳态；
- 确认旧sleep/daemon sockets、CPU backups和temporary artifacts已清理。

## LoRA 运维

`release-documented`，但runtime load/unload具有安全风险且默认关闭。需要：

```bash
VLLM_ALLOW_RUNTIME_LORA_UPDATING=True \
vllm serve /models/base --enable-lora
```

内部管理面加载：

```bash
curl -X POST http://127.0.0.1:8000/v1/load_lora_adapter \
  -H 'Content-Type: application/json' \
  -d '{"lora_name":"adapter-a","lora_path":"/models/adapter-a"}'
```

卸载前先停止新请求引用该adapter并等待in-flight完成，再调用`/v1/unload_lora_adapter`。验证`/v1/models`、adapter smoke和显存/capacity。Scale-out/restart后由外部控制面重新加载；不要假设adapter memory自动复制到新Pod。

## Graceful Shutdown

```text
REMOVE FROM ROUTING
  → DRAIN/POLICY
  → wait output/transfer/worker queues
  → SIGTERM engine process
  → worker/rank/collective teardown
  → release GPU/CPU/socket resources
  → verify process exit and endpoint removal
```

不要先发送SIGKILL再期待stream完成。Termination deadline到期后的强制退出应产生独立metric/log，标出受影响request IDs和是否已输出token。

使用Preload zero-copy时，engine shutdown后daemon可以继续，为下一engine restart保留weights；只有确认没有依赖mapping后才能终止daemon释放GPU。

## Kubernetes Rolling Upgrade

`external-control-plane`通用顺序：

```text
new revision Pod
  STARTING → startup probe → engine smoke → readiness=true
        │ capacity available
        ▼
old revision Pod
  readiness=false → endpoint propagation → drain → SIGTERM
        │ graceful teardown
        ▼
next Pod / continue rollout
```

生产要点：

- `maxUnavailable`/surge必须结合GPU容量和模型load时间，不照搬CPU service。
- startup probe预算覆盖artifact download、quantization、warmup与graph capture。
- terminationGracePeriod覆盖最长允许stream/drain，不等于无限等待。
- Preload daemon若作为独立process/sidecar，升级顺序必须匹配engine version/fingerprint。
- P/D部署分别维护Prefill/Decode容量，不能同时drain导致无完整pair。
- readiness false后等待routing cache传播，不能只看Pod condition立即sleep/free。

## 故障诊断树

```text
instance unavailable / slow
  ├─ process dead?
  │    └─ inspect exit/OOM/driver; restart known-good revision
  ├─ process alive but not ready?
  │    ├─ loading/warmup → startup budget/artifact/GPU memory
  │    ├─ sleeping/partial wake → tags/rank state
  │    └─ distributed rank failure → whole group unready
  ├─ Preload path?
  │    ├─ daemon health/socket owner/permissions
  │    ├─ fingerprint or GPU UUID mismatch
  │    ├─ fallback-to-disk warning
  │    └─ zero-copy daemon lifetime
  ├─ GPU memory not released?
  │    ├─ weights/KV/graphs/NCCL/workspace ownership
  │    └─ main-only graph/NCCL flags vs stable version
  └─ requests failing?
       ├─ admission/readiness propagation
       ├─ aborted/drained stream phase
       └─ stale KV/adapter/model identity
```

### 常见检查

| 现象 | 优先证据 | 安全动作 |
|---|---|---|
| Engine启动仍很慢 | preload mapped log、fallback warning、warmup timeline | 修复cache mismatch；不要掩盖disk fallback |
| Sleep后显存仍高 | allocator tags、CUDA Graph、NCCL、daemon-owned weights | 识别owner；不要重复free外部allocation |
| Wake卡住 | per-rank RPC、collective、OOM、is_sleeping | whole group unready，超时后restart |
| L1 host OOM | CPU RSS/available RAM、weight size | 回滚/重启或改用L2策略 |
| 只有部分rank成功 | rank logs/collective errors | 隔离整个实例组，不允许partial traffic |
| 更新后输出异常 | revision/tokenizer/template/quant/layout | 立即退出routing并回滚immutable bundle |

## 回滚

回滚对象必须是完整bundle：image、vLLM version、model/tokenizer revisions、quantization、parallel layout、loader/connector配置和chat template。

```text
failure detected
  → readiness=false / stop traffic
  → capture logs, rank state, memory and request phase
  → abort unsafe partial update
  → stop/recreate entire serving group
  → restore immutable previous bundle
  → startup + smoke + canary
  → readiness=true
```

不要只回滚单个rank或只替换checkpoint路径。Preload daemon与engine version不一致时，先替换/重建daemon cache，再启动engine。

## Post-operation Checklist

### VERIFY

- [ ] 全部process/ranks处于预期状态，无partial success。
- [ ] model/tokenizer/revision/adapter identity正确。
- [ ] weights、KV、CUDA Graph、NCCL和daemon memory ownership符合矩阵。
- [ ] `/health`、`/is_sleeping`或等价内部状态符合预期。
- [ ] readiness与router membership已传播。
- [ ] smoke request、streaming、usage/finish reason正确。
- [ ] TTFT/ITL、queue、GPU memory、KV capacity无异常回归。
- [ ] 已输出token的中断请求被明确报告，没有透明重复输出。
- [ ] fallback、fingerprint mismatch、OOM、rank错误为零或已解释。
- [ ] old Pod/process/socket/CPU backup/daemon artifact已按设计清理。

### POSTCHECK

至少观察一个正常流量窗口，并把操作版本、开始/结束时间、request failures、memory delta、warmup latency和rollback point写入变更记录。状态/ownership原理回到 [[vllm-operational-lifecycle]]，通用故障语义见 [[llm-serving-reliability]]。
