# SkyPilot 架构与设计思路分析

> 仓库：https://github.com/googs1025/skypilot · 分析日期：2026-06-02 · 版本：master HEAD `55b9185`（2026-06-01，archive 下载 + GitHub API 校验）

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

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| 用户入口 | `sky/client/cli/command.py`, `sky/__init__.py`, `sky/client/sdk.py`, `sky/client/sdk_async.py` | Click CLI、Python SDK、异步 SDK、公开 API facade。把 shell/YAML/Python 调用变成 `Task`/`Dag` 和 API server request。 |
| 声明模型 | `sky/task.py`, `sky/dag.py`, `sky/resources.py`, `sky/utils/dag_utils.py`, `sky/data/*`, `sky/serve/service_spec.py` | 用户声明的中间表示：任务、DAG、资源、volume、storage、service/pool。负责 YAML schema、env/secrets、workdir、file mounts、autostop、hooks。 |
| API server / 控制面 | `sky/server/server.py`, `sky/server/requests/*`, `sky/server/blob/*`, `sky/server/auth/*`, `sky/users/*`, `sky/workspaces/*` | FastAPI API server、request 排队/执行/日志、blob 上传、鉴权、RBAC、workspace 权限。 |
| 执行编排 | `sky/execution.py`, `sky/core.py`, `sky/backends/backend_utils.py` | 统一执行 stage：validate、optimize、provision、sync、setup、pre_exec、exec、down；维护 cluster 状态、事件和 handle。 |
| 优化器 | `sky/optimizer.py`, `sky/catalog/*`, `sky/clouds/*`, `sky/resources.py` | 把抽象资源要求映射成具体 cloud/region/zone/instance_type，按 cost/time 选择，支持 job group 和 failover blocklist。 |
| 后端 | `sky/backends/cloud_vm_ray_backend.py`, `sky/templates/*-ray.yml.j2`, `sky/skylet/*` | 以 Ray + skylet 作为远端运行时，创建/复用集群、同步文件、运行 setup/run、提交 job、设置 autostop/hook。 |
| provider 实现 | `sky/clouds/*.py`, `sky/provision/*`, `sky/adaptors/*` | 每家云/集群的能力声明、区域/价格/规格查询、实例生命周期 API、Kubernetes/Slurm/SSH 特化实现。 |
| 高层服务 | `sky/jobs/*`, `sky/serve/*`, `sky/batch/*`, `sky/ssh_node_pools/*`, `sky/volumes/*` | 在基础 launch/exec/down 之上实现 managed jobs 自动恢复、SkyServe replica/autoscaler、batch/pools、SSH node pools、volume。 |
| 插件/策略/观测 | `sky/server/plugins.py`, `sky/admin_policy.py`, `sky/utils/plugin_extensions.py`, `sky/metrics/*`, `sky/usage/*` | admin policy、server plugins、RBAC 扩展、Prometheus metrics、usage telemetry、外部故障源。 |

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

- **API server 是所有重操作的边界，而不是 CLI 本地直连云 API**：`sky/client/sdk.py:578-860` 会把 launch 封装成 request，上传 mounts，然后 POST `/launch`；`sky/server/server.py:1783-1794` 把请求排入 executor。这样 CLI 退出、日志断线、多人共享 API server、dashboard/RBAC 都能复用同一套 request 记录。
- **长短请求分队列，避免 `status` 被 `launch` 拖死**：`sky/server/requests/executor.py:1-19` 明确区分 long-running 和 short-running request；`RequestWorker` 再把 request 投递到可取消的执行进程/线程（`executor.py:173-255`）。这是控制面可用性的核心，不是普通 FastAPI handler 直接跑函数。
- **Task/Dag/Resources 是稳定 IR**：CLI 先在 `command.py:980-1070` 把 YAML、shell command、job group、CLI overrides 规整成 `Task` 或 `Dag`；`Resources` 明确自己是“任务资源请求、过滤器、计费对象和 provisioning 输入”（`sky/resources.py:142-220`）。这让 CLI、Python SDK、jobs、serve 都能共享同一套 IR。
- **optimizer 在上层，provider 只回答能力和可行性**：`execution.py:492-533` 在进入 backend 前运行 `Optimizer.optimize()`，并向 backend 注入一个可在 cluster lock 内重新规划的 planner；provider 层通过 `CloudImplementationFeatures`、`regions_with_offering()`、catalog 和 provision hooks 暴露能力。这避免把云厂商差异塞进调度算法。
- **跨云 failover 是 provisioning 失败后的重新优化，而不是固定候选列表盲试**：`CloudVmRayBackend` 的 `RetryingVmProvisioner.provision_with_retries()` 在 `cloud.check_features_are_supported()` 或 `ResourcesUnavailableError` 后，把失败资源加入 blocklist，再重新调用 optimizer（`cloud_vm_ray_backend.py:1748-1928`）。这解释了 SkyPilot 为什么能在 capacity error 后自动换 region/cloud。
- **同名集群有强状态和锁**：`CloudVmRayResourceHandle` 保存 cluster name、cloud name、cluster yaml、IP、资源、skylet metadata（`cloud_vm_ray_backend.py:1949-2011`）；provision 前用 `cluster_status_lock_id()` 和 distributed lock 串行化（`cloud_vm_ray_backend.py:3245-3288`）。这是“复用现有集群”和“避免并发 launch 打架”的基础。
- **远端 runtime 选择 Ray + skylet，而不是每个 provider 手写 job execution**：`CloudVmRayBackend._execute()` 最终做资源匹配、添加 job、按单节点/多节点提交（`cloud_vm_ray_backend.py:4411-4475`）。provider 只负责把机器/Pod/Slurm allocation 弄出来，任务排队、日志、autostop、hooks 由统一 runtime 处理。
- **managed jobs / serve 是控制器模式，不是特殊云类型**：`sky/jobs/server/core.py:648-760` 把用户 DAG 存入 controller 并负责 recovery；`sky/serve/replica_managers.py:49-143` 的 replica launch 仍调用 `sdk.launch()`。控制器层只管理生命周期策略，底层仍走普通 launch/down。
- **安全模型偏“控制面托管 + 细粒度 RBAC”**：`global_user_state.py:1-120` 用 DB 记录 clusters/users/volumes；`users/permission.py` 用 Casbin 初始化/检查角色权限；`users/rbac.py` 的 viewer 是 allowlist 模式，默认新 endpoint 不可见。service-account token 用 JWT，但请求时仍回查 DB row 以支持吊销。

## 关键组件深入解读

### CLI / SDK / API Server 边界（`sky/client/cli/command.py`, `sky/client/sdk.py`, `sky/server/server.py`）

`sky` console entry point 来自 `setup.py` 的 `sky = sky.cli:cli`。CLI 的 `launch()` 不直接创建云资源，而是先调用 `_make_task_or_dag_from_entrypoint_with_overrides()`：如果入口是 YAML，走 `dag_utils.load_chain_dag_from_yaml()` 或 `load_job_group_from_yaml()`；如果不是 YAML，就把 shell command 包成 `Task(name='sky-cmd', run=...)`。CLI flags 中的 cloud/region/gpus/cpus/memory/ports/env/secrets 会转成 override params 写回 task。

`sdk.launch()` 是客户端/服务端分界。它把 task 转成 DAG，做 client-side admin policy 和 confirmation，再调用 `client_common.upload_mounts_to_api_server()` 上传 workdir/file mounts blob，最后构造 `LaunchBody` POST 到 `/launch`。server 端 FastAPI handler 只是调度：`executor.schedule_request_async(..., ScheduleType.LONG, func=execution.launch)`，真正重活在 request worker 里执行。这个设计让本地 CLI、dashboard、远端 API server、async SDK 都围绕 request_id 和日志流工作。

### 执行编排（`sky/execution.py`）

`execution._execute()` 是 SkyPilot 的 stage runner。它先把 entrypoint 规整成 DAG，再在 server side 重新跑 admin policy、volume/secrets resolve 和 storage construct。`_execute_dag()` 目前断言普通 launch 只支持单 task；job group 是 managed jobs 的特殊路径。stage 默认包含 OPTIMIZE、PROVISION、SYNC_WORKDIR、SYNC_FILE_MOUNTS、SETUP、PRE_EXEC、EXEC、DOWN。

关键细节是 optimizer 与 backend 的分工：普通情况下 `_execute_dag()` 在进入 backend 前跑 `Optimizer.optimize()`；但它也把一个 `planner` 回调注入 `backend.register_info()`，供 backend 在拿到 cluster lock 后、发现原先状态已经过期时重新规划。这样避免了把 optimizer 移进 backend，同时降低“锁外优化、锁内状态变化”的竞态。

### CloudVmRayBackend 与 failover（`sky/backends/cloud_vm_ray_backend.py`）

`CloudVmRayBackend` 是核心后端，名字里的 Ray 不是装饰：远端执行的统一语义来自 Ray cluster + skylet + job queue。它保存 run log dir、DAG、optimize target、requested features、managed/controller context 和 planner。`provision()` 先检查 rsync、owner identity，再拿同名 cluster lock；锁内 `_check_existing_cluster()` 决定复用/重建/新建，随后 build SkyPilot wheel，并交给 `RetryingVmProvisioner`。

`RetryingVmProvisioner.provision_with_retries()` 是多云弹性的关键。每次尝试前检查 cloud user identity、feature support、cluster name，然后进入 `_retry_zones()`；如果失败且允许 failover，就把当前 resources 加入 blocked_resources，并调用 optimizer 重新选择 `best_resources`。也就是说 failover 是“失败反馈 -> 重新优化”，而不是提前把所有 provider 机械枚举。

### Provider 抽象（`sky/clouds/*.py`, `sky/provision/*`）

SkyPilot 把 provider 拆成两层：`Cloud` 子类负责可用区域、规格/accelerator offering、feature support、状态查询能力；`provision/*` 负责实际生命周期函数，如 `run_instances`、`terminate_instances`、`query_instances`、volume、network。`sky/provision/__init__.py` 的 `_route_to_cloud_impl` 按 provider name 分发到内置模块或插件注册的 provisioner，插件 provisioner 优先于静态模块。这样的好处是 optimizer 可以只关心“哪些资源可行、多少钱、支持什么特性”，backend 只关心“请把这个 launchable resource 启起来”。

### Managed Jobs / SkyServe / Pools

Managed jobs 的本质是 controller cluster 上的 job controller：它加载保存的 DAG，调度每个 job，调用 `sky.launch()` 创建/复用任务集群，监控日志和状态，并通过 `recovery_strategy.StrategyExecutor` 处理失败、preemption 和重启。JobGroup 还会先在 API server 侧做一次 `Optimizer.optimize_job_group()`，把并行任务的 cloud/region 固化后发给 controller，避免 controller 上各任务各自重新优化到不同 infra。

SkyServe 则是 service controller + replica manager + autoscaler。`serve up` 要求 YAML 里有 `service` 段，并校验 service port 与 replica resources ports 一致。controller 运行一个 FastAPI control API，autoscaler 周期读取 replica state 生成 scale up/down 决策；replica manager 用 `sdk.launch()` 启动 replica cluster，用 `sdk.down()` 终止，load balancer 周期上报 inflight 请求给 autoscaler。

## 与同类对比

| 维度 | SkyPilot | Kubernetes 原生 Job/Deployment | Slurm | Ray Jobs |
|------|----------|-------------------------------|-------|----------|
| 用户接口 | YAML/Python API，面向 AI 资源需求 | Pod/Job/Deployment，偏底层容器语义 | sbatch/srun，HPC 队列语义 | Ray runtime 内部任务语义 |
| 资源选择 | 多云/多 region/多实例 optimizer + failover | 依赖单集群 scheduler | 单集群/分区调度 | 依赖已有 Ray cluster |
| Provisioning | 自己创建/复用 VM、Pod、Slurm allocation | 只在 K8s 集群内 | 只在 Slurm 集群内 | 通常不负责创建底层机器 |
| 运行时 | Ray + skylet + job queue | kubelet/container runtime | Slurm daemon | Ray |
| 高层控制面 | managed jobs、serve、pools、dashboard、RBAC | 需要外部系统拼装 | 通常靠 scheduler/accounting | Ray Dashboard/Jobs API |

## 性能 / 资源开销

源码没有给出本地可复现的端到端性能数字。能从架构上确认的资源策略包括：

- API server 把 request 分成 LONG/SHORT 队列，避免 cluster launch 这种长任务阻塞 status/logs 等短请求。
- 文件上传按约 95 MB chunk 拆分，规避 NGINX/Cloudflare upload limit。
- `fast` launch 路径会复用 UP cluster，并通过 config hash 跳过不必要 provisioning/setup。
- failover 时重新优化会增加控制面时间，但换来跨云 capacity resilience。

## 安全模型

SkyPilot 的安全边界主要在 API server 和用户云账号：

- **BYOC**：README 明确“一切在用户自己的 cloud accounts / VPCs / clusters 内启动”，SkyPilot 控制面不拥有基础设施资源本身。
- **API server auth**：server 支持 loopback、本地/外部 OAuth2 proxy、basic auth、service-account JWT；service-account JWT 由 DB 中的 secret 签发，请求时仍回查 token row 以支持吊销。
- **RBAC**：Casbin 权限服务读取默认角色、workspace policy 和插件规则。viewer 角色是 allowlist，新 endpoint 默认不可访问。
- **状态库**：clusters/users/volumes/events 存在 `global_user_state` DB，request 状态和日志另有 request DB；SQLite 可用 WAL，也支持 PostgreSQL 方言。
- **云凭据风险**：controller task 如果使用会过期的本地云凭据，`RetryingVmProvisioner` 会告警可能导致资源泄漏，建议用不失效凭据或 service account。
- **远端执行风险**：用户 setup/run 本质是在用户云资源里执行任意 shell；SkyPilot 负责调度和日志，不替代 workload sandbox。Kubernetes/Slurm/云网络隔离仍需用户/平台配置。
