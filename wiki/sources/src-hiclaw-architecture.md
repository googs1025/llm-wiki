---
title: HiClaw 架构与设计思路分析
tags: [architecture, k8s-operator, multi-agent, ai-infra, agent-platform]
date: 2026-05-13
sources: [hiclaw-architecture-analysis.md]
related: [[HiClaw]], [[claude-code]], [[higress]], [[matrix-protocol]], [[k8s-operator]], [[mcp]], [[declarative-agent-management]], [[agent-credential-isolation]]
---

# HiClaw 架构与设计思路分析

> 原文：`raw/hiclaw-architecture-analysis.md` · 仓库：[agentscope-ai/HiClaw](https://github.com/agentscope-ai/HiClaw) · 分析版本 v1.1.0 (HEAD `e21ac83`)

## 一句话定位

[[HiClaw]] 是把 [[k8s-operator]] 模式套到 AI Agent 运维上的多 Agent 协作平台——用 4 个 CRD（`Worker` / `Team` / `Human` / `Manager`）声明 Agent，controller 把每个 Agent 落成"容器 + [[matrix-protocol|Matrix]] IM 用户 + [[higress|Higress]] consumer"三位一体；人类、Manager、Workers 全在同一组 Matrix 房间里协作；真实 LLM API key 永远不落到 Worker，只发 consumer key（[[agent-credential-isolation|凭据零暴露]]）。一行 `curl | bash` 装到 Docker，或 `helm install` 到 K8s，二者形态对齐。

## 核心架构图

```
┌──────────────────────────  用户接入面（IM-First）  ──────────────────────────┐
│                                                                                │
│       Element Web (http://localhost:18088)  ←──  any Matrix client (mobile)    │
│                              │                                                  │
└──────────────────────────────┼──────────────────────────────────────────────────┘
                               │ Matrix 协议（E2E）
                               ▼
┌────────────────────────  控制平面（hiclaw-controller, Go）  ─────────────────────┐
│  cmd/controller/main.go → internal/app/App                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐    │
│  │  initInfraClients  initBackends  initServiceLayer  initReconcilers       │    │
│  │  initFieldIndexers initAuth      initHTTPServer                          │    │
│  └─────────────────────────────────────────────────────────────────────────┘    │
│                                                                                  │
│  4 个 CRD Reconciler（controller-runtime）                                       │
│   ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────┐                              │
│   │ Worker   │ │ Team   │ │ Human    │ │ Manager  │  (api/v1beta1/types.go)      │
│   └────┬─────┘ └────┬───┘ └────┬─────┘ └────┬─────┘                              │
│        └────────────┴──────────┴────────────┘                                    │
│                    │ ProvisionWorker / DeprovisionWorker                          │
│                    ▼                                                              │
│        internal/service/provisioner.go (1154 行)                                  │
│        ├─ Matrix admin API     (创建/删除 user, 创建/退出 room, 邀请成员)         │
│        ├─ Higress gateway auth (consumer key, MCP route)                          │
│        ├─ Credentials store    (refresh, delete, bootstrap admin token)           │
│        └─ AccessResolver       (object-storage / ai-gateway scope 解析)           │
│                    │                                                              │
│                    ▼                                                              │
│        internal/backend/{docker,kubernetes}.go  (WorkerBackend 接口)              │
│                    │                                                              │
│  HTTP API (server/http.go) ←─── hiclaw CLI (cmd/hiclaw/main.go)                  │
│  运行模式：startEmbedded(kine etcd:2379, in-binary mgr) 或 startInCluster(KUBECONFIG)│
└──────────────────────────────────────────────────────────────────────────────────┘
                               │ container exec
                               ▼
┌─────────────────────  数据/执行平面（容器层）  ───────────────────────────────────┐
│                                                                                    │
│  Manager 容器（一个）             Worker 容器（N 个，按 CR 数量）                  │
│  ┌──────────────────┐             ┌─────────────────────────────────────────────┐ │
│  │ manager/agent/   │  Matrix     │ runtime 三选一：                             │ │
│  │  SOUL.md /       │ ◀────────▶ │   • openclaw-base/  (Claude-Code 类)         │ │
│  │  TOOLS.md /      │             │   • copaw/   (QwenPaw, Python)              │ │
│  │  12 个管理 skill │             │   • hermes/  (autonomous coding, Python)     │ │
│  │  workers-        │             │ 共同套件：                                   │ │
│  │  registry.json   │             │   • mcporter-servers.json (MCP 路由)         │ │
│  └────────┬─────────┘             │   • soul/identity/skills (Worker 人格)       │ │
│           │ hiclaw CLI            │   • bridge.py (Matrix sync, 仅 Python runtime)│ │
│           ▼                       └────┬────────────────────────────────────────┘ │
│   controller HTTP API                  │                                          │
└────────────────────────────────────────┼──────────────────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
   ┌──────────────────┐       ┌────────────────────┐      ┌────────────────────┐
   │ Tuwunel          │       │ Higress AI Gateway │      │ MinIO              │
   │ (Matrix server)  │       │ (LLM/MCP/OSS 凭据  │      │ (Worker 共享文件   │
   │ 房间/用户/消息   │       │ 全部托管在网关侧)  │      │ 系统，跨 Agent 协作)│
   └──────────────────┘       └────────────────────┘      └────────────────────┘

           Helm chart (helm/hiclaw/) 在 K8s 上把上面 4 个组件一并部署
           install/hiclaw-install.sh / .ps1 在 Docker 单机上等价部署
```

## 四个 CRD

| CRD | 表达什么 | 关键 Spec 字段 |
|-----|---------|---------------|
| `Worker` | 单个 AI Agent | `model` · `runtime`（openclaw/copaw/hermes）· `image` · `soul` · `skills` · `mcpServers` · `package`（`file://` / `http(s)://` / `nacos://`）· `expose` · `accessEntries` · `state`（Running/Sleeping/Stopped） |
| `Team` | 一组 Worker + Leader + 房间策略 | `leader` · `workers` · `peerMentions` · `channelPolicy` · `admin` |
| `Manager` | 系统唯一的管家 Agent | model / runtime / soul / skills（含 12 个管理 skill） |
| `Human` | 管理员的 Matrix 身份 | matrixUserID · channel scope |

## 模块分层（简版）

| 层 | 职责 |
|----|------|
| **CRD 定义** | `api/v1beta1/types.go`，仅依赖 `k8s.io/apimachinery`，不引用任何 internal 包 |
| **应用骨架** | `internal/app/App` 用 7-step init 串行装配，扩展只需 append `{name, initFn}` |
| **CR Reconciler** | Worker / Team / Human / Manager 4 套，仅做编排，**绝不**直接调外部 API |
| **服务编排** | `internal/service/provisioner.go`（1154 行，脏活集中地，[[k8s-operator|reconcile]] 的大半在这里） |
| **容器后端** | `WorkerBackend` 接口 + `docker.go` / `kubernetes.go` 两个实现，按 config 选 |
| **基础设施集成** | `internal/{matrix,gateway,oss,credprovider,accessresolver}/` 分别封装 Tuwunel / Higress / MinIO / 阿里云凭据 / 模板解析 |
| **运行模式** | `startEmbedded`（`k3s-io/kine` SQLite-backed etcd 在 127.0.0.1:2379 + 内嵌 mgr）或 `startInCluster`（标准 KUBECONFIG） |
| **Manager Agent** | `manager/agent/` 容器化 orchestrator，12 个管理 skill + `workers-registry.json`，通过 `hiclaw` CLI 操作 controller |
| **Worker runtime** | OpenClaw（[[claude-code]] 系，Dockerfile only）· QwenPaw（Python，`copaw/`）· Hermes（Python，autonomous coding） |
| **部署** | `helm/hiclaw/`（K8s）/ `install/hiclaw-install.{sh,ps1}`（Docker 单机），二者部署形态对齐 |

## 关键数据流：建一个 Worker 端到端

```
管理员（Element Web 中）
      │ 发送 Matrix 消息："帮我建一个 Go 代码评审 Worker"
      ▼
Manager Agent 容器（manager/agent）
      │ 加载 worker-management skill (TOOLS.md 路由)
      │ 决定参数（model / runtime / soul / skills / mcp-servers）
      │ 调 hiclaw CLI: `hiclaw worker create --name go-review …`
      ▼
hiclaw CLI (cmd/hiclaw/main.go) ── HTTP POST ──▶ controller server/http.go
                                                       │
                                                       ▼
                                                 写入 Worker CR
                                          (embedded: kine sqlite / in-cluster: etcd)
      ┌─────────────── controller-runtime watch 触发 ───────────────┐
      ▼
worker_controller.Reconcile()
      │
      ├─[1] Provisioner.ProvisionWorker(ctx, req):
      │      Matrix admin API → 创建 user @go-review:hiclaw.local
      │      Matrix admin API → 创建 1on1 房间，邀请管理员 + Manager
      │      Higress apig API → 注册 consumer + 颁发 consumer key
      │      AccessResolver  → 解析 AccessEntries 模板（${self.name}…）
      │                       → 调 credprovider 申请 MinIO 桶权限
      │      Credentials store → 写入 secret + 设 refresh 时刻
      │
      ├─[2] WorkerBackend.CreateWorker(spec):
      │      docker.go 或 kubernetes.go（依 config）
      │      → 把 PodTemplate + 环境变量 + soul/identity/skills 卷挂上
      │      → 启动 Worker 容器
      │
      ├─[3] member_reconcile.go：
      │      把 Worker Matrix user 加入相关 Team 房间（如有）
      │
      └─[4] 更新 Worker.Status：
            Phase = Running
            MatrixUserID = "@go-review:hiclaw.local"
            RoomID       = "!abc...:hiclaw.local"
            ContainerState = "running"
            ExposedPorts   = [...]   ← 若 Spec.Expose 有端口
      │
      ▼
Worker 容器启动后：
   - Python runtime (copaw/hermes)：bridge.py 用 consumer key 登录 Matrix，订阅自己的房间
   - OpenClaw runtime：宿主 Claude Code 自带 hook 完成同等动作
      │
      ▼
管理员立刻在 Element Web 看到 @go-review 出现并打招呼；后续的代码评审请求可直接 @
```

### 稳态通信信道

```
Worker → LLM:    Worker 容器 ─consumer key→ Higress AI Gateway ─真实 API key→ LLM provider
Worker ↔ Worker: 双方都加入同一 Matrix 房间，消息走 Tuwunel；大文件落 MinIO（节省 token）
Worker ↔ Human:  Matrix 房间（管理员是房间成员，可以随时介入）
Worker → 工具:    Worker 容器 ─consumer key→ Higress ─route→ MCP server（external 或 in-cluster）
Manager → 控制器: Manager 容器内的 hiclaw CLI ─HTTP→ controller ─CR write→ etcd/kine
```

## 设计决策与哲学

- **[[declarative-agent-management|声明式 Agent 运维]]**：Agent 是 CR 不是对象。免费拿到 K8s 的 declarative / reconcile / self-healing / RBAC——这是 HiClaw 与 [[langgraph]] / [[autogen]] / [[crewai]] 这类「代码中编排 Agent」框架的根本不同。

- **IM 协议作为协作平面 lingua franca**：选 [[matrix-protocol|Matrix]] 而非自研 Web UI/事件总线——每个 Agent 是 IM 用户，每场协作是 IM 房间，人类天然是房间成员，**可观测性与人在回路同时拿到**，避免两个大坑。代价：所有 Agent 都要做 Matrix 适配。

- **[[agent-credential-isolation|凭据零暴露]]**：Worker 永远拿不到真实 API key / GitHub PAT / OSS AK，只持 [[higress|Higress]] consumer key。结果：[[mcp|MCP]] 工具市场和 skills 市场可以大胆装载社区作品——即便 Worker 被 prompt injection 攻陷，攻击者拿到的也只是可被即时 revoke 的 consumer key。

- **运行时三选一可插**：`WorkerSpec.Runtime` 字段切换 OpenClaw（[[claude-code]] 系）/ QwenPaw（Qwen Code 系，省钱）/ Hermes（autonomous coding agent，自主）。最近 commit `d3e33e8` 把默认 runtime 从 OpenClaw 切到 QwenPaw，价格敏感倾向明显。

- **容器后端双轨**：`WorkerBackend` 接口 + `docker.go` / `kubernetes.go` 两实现，让"单机 Docker Desktop 跑 5 个 Worker"与"K8s 集群跑 500 个 Worker"共用同一 controller 二进制。

- **嵌入式 K8s（[[kine]] + 内嵌 controller-manager）**：单机模式跑 kine（SQLite-backed etcd）+ 同进程的 controller-manager，于 127.0.0.1:2379。**用户感觉装了 Docker，骨子里是 K8s API**——CRD / Reconcile / Helm 在无真 K8s 环境也成立。

- **schema-less 模板字段**：`AccessEntry.Scope` 用 `*apiextensionsv1.JSON` 而非严格 struct，支持 `${self.name}` / `${self.kind}` / `${self.namespace}` 运行期变量。CRD 不绑死特定 cloud provider；解析延迟到 `accessresolver`。

- **`hiclaw` CLI 注入 Manager / Worker 容器**：Manager Agent 不引用 Go SDK，通过 fork CLI 操作 controller HTTP API——让 skill（markdown 文档）可以直接生成 `hiclaw worker create …` 这种命令字符串。

- **[[mcp|MCP]] via [[nacos|Nacos]] 包市场**：Worker 能力通过 `WorkerSpec.Package` 字段（`nacos://` / `http(s)://` / `file://`）按需加载。Manager 侧的 `hiclaw-find-worker` skill 就是做 Nacos 搜索 + 导入。Worker 模板像 docker 镜像一样可分发。

## 关键组件深入：Provisioner

`internal/service/provisioner.go`（1154 行 / 29 公开方法）是 controller 的脏活集中地，可分三组：

1. **Matrix 编排**（`ProvisionWorker` / `ProvisionTeamRooms` / `EnsureRoomMember` / `ReconcileRoomMembership` …）——通过 Tuwunel admin API 完成 user / room / membership / alias 全生命周期；`MatrixUserID(name)` 与 `roomAliasLocalpart(kind, name)` 是命名规则集中点，保证幂等。
2. **Higress 凭据**（`EnsureManagerGatewayAuth` / `EnsureWorkerGatewayAuth` / `RefreshCredentials` / `DeleteCredentials`）——用 `alibabacloud-go/apig-20240327/v6` 在 Higress 上为每个 Agent 注册 consumer + key。
3. **Manager 引导**（`IsManagerLLMAuthReady` / `IsManagerJoinedDM` / `SendManagerWelcomeMessage`）——容器首启时检查 Manager 是否就绪 + 投递欢迎语（按 `language` / `timezone` 渲染）。

**横向拆分时机已到**：按 Matrix / Higress / Credentials / Manager-bootstrap 四个域拆到独立文件，`Provisioner` 退化为外观。

## 与同类对比

| 维度 | [[HiClaw]] | [[autogen]] | [[langgraph]] | [[crewai]] |
|------|--------|---------|-----------|--------|
| 形态 | K8s operator + 容器化 | Python library | Python library | Python library |
| Agent 表达 | CR (YAML) | Python class | StateGraph node | Crew/Agent class |
| 部署单元 | Pod / Container | 进程 | 进程 | 进程 |
| 协作面 | Matrix 房间 | In-process bus | StateGraph 边 | Crew 内调度 |
| 人在回路 | 默认（房间成员） | 需自接 UI | 需自接 UI | 需自接 UI |
| 凭据模型 | 网关托管 | Agent 持真 key | Agent 持真 key | Agent 持真 key |
| 跨 Agent 文件 | MinIO 桶 | 自实现 | 自实现 | 自实现 |

最大差异：**HiClaw 把 Agent 当 K8s 一等公民资源**，所以是"可被 reconcile 自愈 / 可被 helm 上线 / 可被 RBAC 限定"的东西。其余框架本质是"在你进程里跑一段 Python"，做企业级运维要重头补。代价：学习曲线高、每 Worker 一个容器有 RAM / 镜像开销。

## 演进信号

- 近 30 天最活跃：`install/hiclaw-install.sh`（20）· `internal/service/provisioner.go`（12）· `api/v1beta1/types.go`（12）· `internal/config/config.go`（11）→ 主线是"装上 / 升级体验" + "controller 核心模型稳定"
- 关键 PR：`#780` 默认 runtime → QwenPaw · `#749` `--keep-all` 升级 · `#783` `helm uninstall` 残留清理 · `#785` manager 容器 API 对齐 controller `/api/v1` · `#798` `error()` 多行安全
- v1.0 → v1.1 阶段，下一步看点：Hermes runtime 主线化、多租户 RBAC、kine → 真 etcd 平滑迁移工具

## 相关页面

- [[HiClaw]]
- [[claude-code]]
- [[higress]] · [[matrix-protocol]] · [[mcp]] · [[k8s-operator]]
- [[declarative-agent-management]]
- [[agent-credential-isolation]]
- [[autogen]] · [[langgraph]] · [[crewai]]
