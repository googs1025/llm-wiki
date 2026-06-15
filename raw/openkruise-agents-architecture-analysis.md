# OpenKruise Agents 架构与设计思路分析

> 仓库：https://github.com/openkruise/agents · 分析日期：2026-06-15 · 版本：HEAD `0e58df8`（2026-06-12，fix(keys): replace ticker with informer-driven refresh for secret-backed key storage (#421)）· 获取方式：GitHub API 复核 metadata + 本地 clone 源码扫描。

## 一句话定位

`openkruise/agents` 是 OpenKruise 面向 AI Agent sandbox lifecycle management 的 Kubernetes 原生平台层。它不只是一个 `Sandbox` CRD controller，而是把四类能力放在同一个工程里：

- 用 `Sandbox` / `SandboxSet` / `SandboxClaim` / `SandboxTemplate` 表达可暂停、可预热、可领取、可升级的 Agent sandbox。
- 用 `agent-sandbox-controller` 管 Pod/PVC/template/hash/status/rolling update/warm pool 等生命周期。
- 用 `sandbox-manager` 暴露 E2B-compatible API，把“创建 sandbox / clone checkpoint / pause / resume / route”变成产品 API。
- 用 `traffic-extension` / `sandbox-gateway` 接入 Envoy，把外部请求按 sandbox identity 路由到具体 Pod IP 和端口。

它和 `kubernetes-sigs/agent-sandbox` 的关系更像“上层发行版 + 兼容实现 + 产品化控制面”：README 明确说明会保持与 SIG agent-sandbox API 的兼容，同时在 SIG API 可用前内置 sandbox API 和实现。

## 核心架构图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           User / SDK / Platform API                          │
│                                                                              │
│  E2B SDK / HTTP API        Kubernetes CRD API        Examples / Integrations │
│  /sandboxes /snapshots     Sandbox* resources       Claude Code / Desktop    │
└──────────────┬───────────────────────┬──────────────────────────────┬───────┘
               │                       │                              │
               │ E2B-compatible REST   │ kubectl / GitOps             │
               ▼                       ▼                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                         sandbox-manager (API control plane)                  │
│                                                                              │
│  HTTP mux + auth/key storage + adapter registry + SandboxManager             │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ ClaimSandbox / CloneSandbox / Pause / Resume / DeleteCheckpoint        │  │
│  │ route sync with memberlist peers + proxy refresh                       │  │
│  └──────────────┬───────────────────────────────┬─────────────────────────┘  │
│                 │                               │                            │
│                 │ infra interface               │ route table update         │
│                 ▼                               ▼                            │
│  sandboxcr infra: create/update SandboxClaim    Proxy / peer membership       │
└─────────────────┬───────────────────────────────────────────────┬────────────┘
                  │                                               │
                  │ Kubernetes API                                │ Envoy ext_proc
                  ▼                                               ▼
┌──────────────────────────────────────────────┐   ┌───────────────────────────┐
│ agent-sandbox-controller (K8s control plane) │   │ traffic-extension / gateway│
│                                              │   │                           │
│ Controllers:                                 │   │ - ext_proc gRPC service   │
│ - Sandbox                                    │   │ - Envoy Go HTTP filter    │
│ - SandboxSet                                 │   │ - sandboxID + port lookup │
│ - SandboxClaim                               │   │ - x-envoy-original-dst    │
│ - SandboxUpdateOps                           │   │ - peer route sync         │
│ - SecurityTokenRefresh                       │   └──────────────┬────────────┘
│                                              │                  │
│ Webhooks + indexes + expectations + metrics  │                  │ original dst
└──────────────┬───────────────────────────────┘                  ▼
               │                                        ┌──────────────────────┐
               │ reconcile                              │ Running Sandbox Pod  │
               ▼                                        │                      │
┌────────────────────────────────────────────────────┐   │ agent workload       │
│ OpenKruise Agents CRDs                             │   │ agent-runtime sidecar │
│                                                    │   │ traffic-proxy        │
│ SandboxTemplate ─┐                                 │   │ CSI dynamic mount    │
│ SandboxSet ──────┼─ keep unused pool ready          │   │ security token       │
│ SandboxClaim ────┼─ claim / create / inplace update │   └─────────┬───────────┘
│ Sandbox ─────────┘  pause / resume / checkpoint     │             │
└──────────────┬─────────────────────────────────────┘             │
               │                                                   │
               ▼                                                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ Kubernetes substrate                                                          │
│ Pods + PVC / persistent filesystem + runtimeClass + NetworkPolicy + CSI       │
│ Optional checkpoint / hibernation: IP, memory, filesystem, GPU memory roadmap │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层 / 模块 | 主要目录 / 文件 | 职责 |
|----------|----------------|------|
| CRD API | `api/v1alpha1/*_types.go` | 定义 `Sandbox`、`SandboxSet`、`SandboxClaim`、`SandboxTemplate`，覆盖 pause、persistent contents、runtimes、claim、template、upgrade、dynamic volume mount。 |
| K8s 控制面 | `cmd/agent-sandbox-controller/main.go`、`pkg/controller/*` | controller-runtime manager；注册 Sandbox/SandboxSet/SandboxClaim/SandboxUpdateOps/SecurityTokenRefresh controller、webhook、field index、metrics cleanup。 |
| API 控制面 | `cmd/sandbox-manager/main.go`、`pkg/servers/e2b/*`、`pkg/sandbox-manager/*` | 暴露 E2B-compatible API；把 request adapter、auth/key storage、infra backend、memberlist peer 和 route proxy 组合成 sandbox 管理服务。 |
| Sandbox infra | `pkg/sandbox-manager/infra/*` | 定义抽象 `Infrastructure` / `Sandbox` 接口；`sandboxcr` 实现用 K8s CRD 完成 claim、clone、pause/resume、checkpoint、CSI mount、identity token。 |
| 路由数据面 | `cmd/traffic-extension/main.go`、`pkg/proxy/*`、`cmd/sandbox-gateway/main.go`、`pkg/sandbox-gateway/*` | Envoy ext_proc 或 Go HTTP filter；从请求解析 sandboxID/port，查 route registry，写入 original-dst 元数据并做 peer 同步。 |
| Runtime 扩展 | `pkg/agent-runtime/*`、`pkg/identity/*` | agent-runtime sidecar、CSI volume mount provider、identity provider 和 token propagation 扩展点。 |
| 示例与集成 | `examples/*` | code interpreter、desktop、OpenClaw、Claude Code 等场景，展示如何把热池、E2B SDK、sandbox image 和 session 复用组合起来。 |

## API 与核心对象

### Sandbox

`Sandbox` 是单个运行环境的期望状态。重要字段包括：

- `paused`：把 sandbox 置于暂停/恢复路径。
- `persistentContents`：声明 IP、memory、filesystem 等内容是否需要保留；README/roadmap 还把 GPU memory checkpoint 放在 hibernation 方向。
- `shutdownTime` / `pauseTime`：用时间字段表达生命周期收敛，而不是只依赖外部 GC。
- `runtimes`：内置 `csi`、`agent-runtime`、`traffic-proxy` 等 runtime config。
- `lifecycle`：pre/post upgrade exec hook。
- `upgradePolicy`：控制 template 变化如何影响已有 sandbox。
- `template` / `templateRef` / `volumeClaimTemplates`：把 Pod 模板、模板复用和持久卷模板接入 K8s 原语。

### SandboxSet

`SandboxSet` 维护一组“未被 claim 的可用 sandbox”，本质是 warm pool 和滚动更新控制器：

- `replicas` 表示需要保持的 unused sandboxes 数量；
- status 跟踪 available、updated、current/update revision；
- labels/annotations 表达 pool、template、claim、owner、hash、lock、restore-from、init-runtime request、memberlist url 等协议状态；
- controller 会分组 sandbox、scale up/down、删除 dead sandbox、处理 rolling update。

### SandboxClaim

`SandboxClaim` 是把“用户请求一个 sandbox”变成控制面协议的关键对象：

- `templateName` 指向 `SandboxSet` / `SandboxTemplate`；
- `createOnNoStock` 决定 warm pool 没库存时是否冷创建；
- `claimTimeout` / `waitReadyTimeout` / `ttlAfterCompleted` 控制领取和清理；
- `inplaceUpdate` 当前支持 image 与 CPU resources；
- `dynamicVolumesMount` 支持请求时挂载 CSI volume；
- `reserveFailedSandbox` 让失败 sandbox 可保留用于 debug；
- `skipInitRuntime` 可跳过 agent-runtime 初始化。

## 关键数据流

### E2B API 创建 sandbox

```
E2B SDK / Client
    │
    │ POST /sandboxes
    ▼
sandbox-manager routes.go
    │
    ├─ CheckApiKey / team permission / namespace mapping
    ├─ CreateSandbox parses template / metadata / timeout / init runtime
    └─ choose path:
          │
          ├─ template exists ──► ClaimSandbox
          │
          └─ checkpoint exists ──► CloneSandbox
                    │
                    ▼
SandboxManager
    │
    ├─ infra.ClaimSandbox or infra.CloneSandbox
    ├─ metrics + route sync
    └─ refresh local proxy and memberlist peers
                    │
                    ▼
sandboxcr infra
    │
    ├─ pick available Sandbox / create / speculate
    ├─ lock and update Sandbox or create SandboxClaim
    ├─ wait ready when requested
    ├─ init agent-runtime when requested
    ├─ issue and propagate identity token when feature enabled
    └─ mount CSI dynamic volumes when requested
```

### 请求路由到 sandbox

```
Client request
    │
    ▼
Envoy listener
    │
    ├─ traffic-extension ext_proc
    │      ├─ parse sandboxID / port through adapter
    │      ├─ route registry lookup
    │      ├─ require route state = running
    │      └─ set x-envoy-original-dst-host = route.IP:port
    │
    └─ or sandbox-gateway Go filter
           ├─ parse sandboxID / port
           ├─ route registry lookup
           └─ set dynamic metadata envoy.lb.original_dst.host
                    │
                    ▼
            Envoy original dst cluster
                    │
                    ▼
              Sandbox Pod IP:port
```

### Warm pool / claim 生命周期

```
SandboxTemplate
      │
      ▼
SandboxSet(replicas = unused capacity)
      │
      ├─ create available Sandboxes
      ├─ keep template hash / revision status
      └─ rolling update pool when template changes

SandboxClaim(templateName)
      │
      ├─ select available Sandbox from matching SandboxSet
      ├─ lock and mark claimed / owner / timestamp
      ├─ apply labels, annotations, env vars and inplace update
      ├─ optionally initialize runtime and dynamic CSI mount
      └─ wait ready -> Completed
```

## 设计决策与哲学

- **把 warm pool 做成声明式资源，而不是进程内队列**：`SandboxSet` 让“保持 N 个可用 sandbox”由 K8s controller 持续收敛；`SandboxClaim` 则把领取动作显式化，便于处理并发、超时、失败保留和 owner/label 不变量。

- **E2B API 是产品入口，CRD 是平台入口**：开发者可以通过 E2B SDK 创建/暂停/恢复 sandbox，平台团队也可以通过 `Sandbox*` CRD 做 GitOps、RBAC、namespace、多租户和控制面调试。这比只提供 SDK 或只提供 YAML 都更容易落地。

- **数据面和控制面解耦**：`sandbox-manager` 负责创建、clone、pause、resume 和 route sync；Envoy ext_proc / Go filter 只负责把请求映射到已知 sandbox route。高频请求不直接打 Kubernetes API。

- **路由协议围绕 sandbox identity**：请求解析出 sandboxID 和 port 后，route registry 给出 Pod IP 和运行状态。route 同步通过 peer/memberlist 在多个 manager/gateway 实例间传播，避免单实例内存表成为唯一控制点。

- **runtime 扩展是可插拔而不是硬编码**：`runtimes` 字段和 `agent-runtime`、`csi`、`traffic-proxy` config 让 sidecar、动态存储、流量代理成为可声明能力；identity provider 接口也允许社区默认 token 与企业级 HTTPS provider/propagator 分开演进。

- **身份安全还在工程化演进中**：最近提交把 secret-backed key storage 的 ticker 刷新改成 informer-driven refresh，说明 E2B API key / token 生命周期已经成为真实控制面问题。生产采用时要重点看 key storage backend、namespace-scoped team、token propagation、audit 和 revoke。

## 与同类项目的区别

| 项目 | 主要抽象 | 与 OpenKruise Agents 的区别 |
|------|----------|-----------------------------|
| `kubernetes-sigs/agent-sandbox` | Sandbox CRD 原语 | 更偏 SIG 级基础 API；OpenKruise Agents 把 warm pool、E2B API、route proxy、identity/CSI/runtime 扩展也产品化进同一发行版。 |
| `volcano-sh/agentcube` | AgentRuntime / CodeInterpreter session orchestration | AgentCube 用 Router + WorkloadManager 把 agent-sandbox 包成 invocation API；OpenKruise Agents 直接提供 E2B-compatible API 和更完整的 sandbox lifecycle/runtime 扩展。 |
| `agent-substrate/substrate` | WorkerPool / ActorTemplate 高密度 actor substrate | Substrate 更强调 actor multiplexing、wake routing、snapshot；OpenKruise Agents 更贴近 K8s CRD + E2B sandbox 管理。 |
| AgentScope Runtime | AgentApp / Runner / deployer | AgentScope Runtime 是 Python app 服务化壳；OpenKruise Agents 是 Kubernetes sandbox lifecycle substrate，可作为 workspace/E2B 后端。 |
| OpenShell | Gateway + supervisor + policy proxy | OpenShell 的强项是 sandbox 内 runtime enforcement 和 policy；OpenKruise Agents 的强项是 K8s 生命周期、热池、E2B API 和路由控制面。 |

## 采用建议

- 如果目标是“在 Kubernetes 上提供 E2B-like sandbox 服务”，OpenKruise Agents 比单独 `agent-sandbox` 更接近完整产品面。
- 如果目标只是学习最小 CRD 原语，先读 `kubernetes-sigs/agent-sandbox`；OpenKruise Agents 需要同时理解 controller、manager、gateway、runtime sidecar 和 identity/CSI。
- 如果已经有 Agent framework，需要一个远端 workspace/sandbox backend，优先验证 E2B API 兼容范围、template 管理、timeout、文件/命令 API 和路由行为。
- 如果是高风险不可信代码执行，仍要额外验证 runtimeClass、NetworkPolicy、seccomp/AppArmor、egress gateway、token revoke 和 audit；OpenKruise Agents 提供扩展点，但不是自动替代强 runtime enforcement。

## 风险与待验证点

- API 仍处在快速演进期，README/roadmap 显示 pool、storage、network、runtime、scheduling、observability、SDK 都有大量后续事项。
- `SandboxClaim` 并发领取、create-on-no-stock、speculate、lock 和 expectations 是正确性关键，需要用压力测试验证。
- 路由表同步依赖 manager/gateway peer 状态，生产要验证实例重启、网络分区和 route stale 时的 fail-close 行为。
- E2B API key storage 支持 secret/mysql，MySQL backend 需要正确配置 hash pepper；secret backend 已有 informer-driven refresh，但要验证 revoke 延迟。
- checkpoint/hibernation 的 memory/filesystem/GPU memory 能力要按具体 runtime 和存储后端验证，不能只看字段设计。
