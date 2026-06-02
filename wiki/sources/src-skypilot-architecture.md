---
title: SkyPilot 架构与设计思路分析
tags: [architecture, ai-infra, gpu, kubernetes, serving]
date: 2026-06-02
sources: [skypilot-architecture-analysis.md]
related: ["[[kubernetes]]", "[[vllm]]", "[[sglang]]", "[[dynamo]]", "[[llm-inference]]", "[[disaggregated-serving]]"]
---

# SkyPilot 架构与设计思路分析

> 原文：`raw/skypilot-architecture-analysis.md` · 仓库：[googs1025/skypilot](https://github.com/googs1025/skypilot) · 分析版本 master HEAD `55b9185`（2026-06-01）

## 一句话定位

SkyPilot 是一个面向 AI/ML 工作负载的多云算力控制平面：用户用 YAML / Python API 声明 `Task`、`Dag`、`Resources`，SkyPilot 负责选择可用且便宜的 GPU/CPU/TPU 基础设施，完成 provisioning、文件同步、setup、run、日志流和自动回收。它的关键手段是把“用户声明”和“云厂商细节”之间拆成 API server request 队列、optimizer、CloudVmRayBackend、cloud/provision provider 接口、controller（managed jobs / serve / pools）几层。

## 核心架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ User surface                                                                 │
│  sky CLI (Click) · Python SDK · YAML recipes · Agent skill                   │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ Task / Dag / Resources / service / pool / job_group
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Client side                                                                  │
│  sky/client/cli/command.py                                                    │
│    ├─ YAML/command parsing, CLI overrides, env/secrets merge                 │
│    └─ sky.client.sdk.*                                                       │
│  sky/client/sdk.py                                                            │
│    ├─ local admin policy + confirmation                                      │
│    ├─ upload workdir/file_mounts blob                                        │
│    └─ POST /launch, /jobs/*, /serve/* + stream request logs                  │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ authenticated REST request + request_id
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ API server                                                                   │
│  FastAPI server.py                                                           │
│    ├─ auth: loopback / oauth2-proxy / service-account JWT / basic auth       │
│    ├─ RBAC + workspace permission                                            │
│    ├─ request DB + blob storage + log streaming                              │
│    └─ executor: LONG queue vs SHORT queue                                    │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ scheduled long-running request
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Execution orchestration                                                      │
│  sky/execution.py                                                            │
│    ├─ validate + admin policy + secrets/volumes resolve                      │
│    ├─ OPTIMIZE: Optimizer.optimize / optimize_job_group                      │
│    ├─ PROVISION: CloudVmRayBackend.provision                                 │
│    ├─ SYNC_WORKDIR / SYNC_FILE_MOUNTS / SETUP                                │
│    ├─ PRE_EXEC: autostop/hooks/skylet                                        │
│    └─ EXEC: submit task to cluster job queue                                 │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ launchable Resources
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Provider substrate                                                           │
│  optimizer.py + resources.py + clouds/*.py + provision/*                    │
│    ├─ catalog/pricing/accelerator offering                                   │
│    ├─ Cloud feature gates: spot, ports, docker, autostop, HA controller      │
│    ├─ SkyPilot provisioner or Ray autoscaler template                        │
│    └─ cloud APIs: Kubernetes, Slurm, AWS, GCP, Azure, OCI, RunPod, ...       │
└───────────────┬─────────────────────────────────────────────────────────────┘
                │ VMs / Pods / Slurm allocations
                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Remote runtime                                                               │
│  Ray cluster + skylet + job queue + logs + autostop hooks                    │
│  Optional controllers: managed jobs controller, SkyServe controller, pools   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| 用户入口 | Click CLI、Python SDK、异步 SDK、公开 API facade。把 shell/YAML/Python 调用变成 `Task`/`Dag` 和 API server request。 |
| 声明模型 | 用户声明的中间表示：任务、DAG、资源、volume、storage、service/pool。负责 YAML schema、env/secrets、workdir、file mounts、autostop、hooks。 |
| API server / 控制面 | FastAPI API server、request 排队/执行/日志、blob 上传、鉴权、RBAC、workspace 权限。 |
| 执行编排 | 统一执行 stage：validate、optimize、provision、sync、setup、pre_exec、exec、down；维护 cluster 状态、事件和 handle。 |
| 优化器 | 把抽象资源要求映射成具体 cloud/region/zone/instance_type，按 cost/time 选择，支持 job group 和 failover blocklist。 |
| 后端 | 以 Ray + skylet 作为远端运行时，创建/复用集群、同步文件、运行 setup/run、提交 job、设置 autostop/hook。 |
| provider 实现 | 每家云/集群的能力声明、区域/价格/规格查询、实例生命周期 API、[[kubernetes]]/Slurm/SSH 特化实现。 |
| 高层服务 | 在基础 launch/exec/down 之上实现 managed jobs 自动恢复、SkyServe replica/autoscaler、batch/pools、SSH node pools、volume。 |
| 插件/策略/观测 | admin policy、server plugins、RBAC 扩展、Prometheus metrics、usage telemetry、外部故障源。 |

关键约束是：`Task`/`Resources` 只表达用户需求，不做云 API 调用；`Cloud` 类描述能力和候选资源，不直接成为长期状态对象；`provision/*` 做具体生命周期；`CloudVmRayBackend` 负责把 optimizer 选出的 launchable resources 落到远端 runtime；API server 负责请求排队和鉴权，不把所有重任务塞在 FastAPI event loop 上。

## 关键数据流

### `sky launch` 主链路

```
sky launch task.yaml
    │
    ▼
command.py:_make_task_or_dag_from_entrypoint_with_overrides()
    │  ├─ detect YAML vs shell command
    │  ├─ load_chain_dag_from_yaml / load_job_group_from_yaml
    │  └─ apply CLI resource/env/secret/workdir overrides
    ▼
command.py:launch()
    │  └─ sdk.launch(task, cluster_name, backend=CloudVmRayBackend, ...)
    ▼
sdk.py:launch()
    │  ├─ convert_entrypoint_to_dag()
    │  ├─ apply client-side admin policy
    │  ├─ upload_mounts_to_api_server()
    │  └─ POST /launch -> request_id
    ▼
server.py:/launch
    │  └─ executor.schedule_request_async(..., func=execution.launch, LONG)
    ▼
execution.py:launch() / _execute_dag()
    │  ├─ validate, resolve volumes/secrets
    │  ├─ Optimizer.optimize()
    │  ├─ backend.register_info(dag, requested_features, planner)
    │  ├─ backend.provision()
    │  ├─ backend.sync_workdir() / sync_file_mounts()
    │  ├─ backend.setup()
    │  ├─ backend.set_autostop()
    │  └─ backend.execute()
    ▼
CloudVmRayBackend
    │  ├─ distributed cluster lock
    │  ├─ RetryingVmProvisioner.provision_with_retries()
    │  ├─ cloud/provision provider APIs
    │  └─ Ray job queue + skylet + logs
    ▼
Remote VM / Pod / Slurm allocation
```

错误和回退路径很关键：如果第一次 optimizer 无可行资源，`ResourcesUnavailableError.failover_history` 为空；如果 cloud feature check、region/zone provisioning 或 capacity 失败，`RetryingVmProvisioner` 会把失败资源加入 blocklist，调用 `Optimizer.optimize(..., blocked_resources=...)` 重新选资源，再继续尝试。

### Managed Jobs / Serve 控制器路径

```
                      ┌───────────────────────┐
sky jobs launch ─────▶│ Jobs controller cluster │
                      │  JobController         │
                      │  ├─ load DAG from DB   │
                      │  ├─ scheduler/recovery │
                      │  ├─ sky.launch(task)   │
                      │  └─ monitor/log/cleanup│
                      └───────────┬───────────┘
                                  │ launches task clusters or pools
                                  ▼
                            CloudVmRayBackend

                      ┌────────────────────────┐
sky serve up ────────▶│ SkyServe controller     │
                      │  ├─ ReplicaManager      │
                      │  ├─ Autoscaler          │
                      │  ├─ FastAPI control API │
                      │  └─ Load balancer sync  │
                      └───────────┬────────────┘
                                  │ launches replica clusters via sdk.launch()
                                  ▼
                            replica VM/Pod clusters
```

Managed jobs 与 serve 都不是直接改底层后端，而是复用同一套 `sdk.launch()` / `CloudVmRayBackend`。区别是它们把自己变成“控制器集群”上的长期进程，维护 job/service 状态，并用恢复/扩缩容策略反复发起普通 launch/down。

## 设计决策与哲学

- **API server 是所有重操作的边界**：用户侧 `sky.client.sdk.launch()` 上传 mounts 后 POST `/launch`，server 只调度 request，真正执行在 request worker 中。这个边界让 CLI、dashboard、远端 API server、async SDK 都围绕 request_id 和日志流工作。
- **长短请求分队列**：API server 明确区分 cluster launch / job submission 这类 LONG request 和 status/logs 这类 SHORT request，避免长 provisioning 阻塞控制面读请求。
- **Task/Dag/Resources 是稳定 IR**：CLI 会先把 YAML、shell command、JobGroup、CLI overrides 规整成统一声明模型；[[kubernetes]]、Slurm、AWS/GCP/Azure 等 provider 不直接影响用户接口。
- **optimizer 在上层，provider 只回答能力和可行性**：执行层先调用 optimizer，再把可重新规划的 planner 注入 backend；provider 层通过 feature gates、catalog 和 provision hooks 暴露能力。
- **跨云 failover 是失败反馈后的重新优化**：capacity/feature/identity 失败后，backend 把失败 resources 加入 blocklist，再重新调用 optimizer，而不是固定候选列表盲试。
- **managed jobs / serve 是控制器模式**：jobs controller 和 SkyServe controller 都通过 `sdk.launch()` / `sdk.down()` 管理实际集群，自己只维护恢复、扩缩容、状态和日志策略。
- **安全模型偏控制面托管 + RBAC**：状态库记录 clusters/users/volumes/events；API server 支持 OAuth2 proxy、basic auth、service-account JWT、Casbin RBAC 和 workspace permission。viewer 是 allowlist，新 endpoint 默认不可见。

## 关键组件深入解读

### `sky launch` 执行编排

`execution._execute()` 是 SkyPilot 的 stage runner：validate、admin policy、volume/secrets resolve、storage construct 后，进入 `_execute_dag()`。普通 launch 目前只支持单 task；stage 默认包含 OPTIMIZE、PROVISION、SYNC_WORKDIR、SYNC_FILE_MOUNTS、SETUP、PRE_EXEC、EXEC、DOWN。它先在锁外运行 `Optimizer.optimize()`，同时把一个 planner 回调注入 backend，供 backend 在拿到同名 cluster lock 后按最新状态重新规划，降低并发状态变化带来的竞态。

### CloudVmRayBackend 与 failover

`CloudVmRayBackend` 是核心后端：远端执行语义来自 Ray cluster + skylet + job queue。provision 前检查 rsync 和 owner identity，再拿同名 cluster lock；锁内决定复用/重建/新建，随后 build SkyPilot wheel 并交给 `RetryingVmProvisioner`。如果 provisioning 失败且允许 failover，它会把当前资源加入 blocklist，再调用 optimizer 重新选择 `best_resources`，这就是 SkyPilot 能在 capacity error 后自动换 region/cloud 的关键。

## 与 [[dynamo]] / [[vllm]] / [[sglang]] 的关系

SkyPilot 不是推理引擎，也不直接实现 [[llm-inference]] 的 batching、KV cache 或模型执行。它更像 AI compute control plane：可以用统一 YAML 启动 [[vllm]]、[[sglang]]、训练任务、RAG app、Jupyter、batch inference 或 [[disaggregated-serving]] 相关组件，并在 [[kubernetes]]、Slurm、公有云 GPU provider 之间做资源选择、failover 和生命周期治理。

## 相关页面

- [[kubernetes]]
- [[vllm]]
- [[sglang]]
- [[dynamo]]
- [[llm-inference]]
- [[disaggregated-serving]]
