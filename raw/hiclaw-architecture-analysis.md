# HiClaw 架构与设计思路分析

> 仓库：https://github.com/agentscope-ai/HiClaw · 分析日期：2026-05-13 · 版本：v1.1.0 (HEAD e21ac83)

## 一句话定位

HiClaw 是 Kubernetes 原生的**多 Agent 协作平台**：用 CRD 声明 AI 工作者（`Worker` / `Team` / `Human` / `Manager` 四种），controller 把每个 Agent 落成"容器 + Matrix IM 用户 + Higress 网关 consumer"三位一体——人类、Manager Agent、Worker Agents 全在同一组 Matrix 房间里协作，凭据全部托管在 Higress AI Gateway，Worker 只拿到 consumer key 永远见不到真实 API key。架构上是「K8s operator + IM-first 协作面 + 网关化凭据」三件套的有机组合，既可以一行命令 `curl | bash` 装到本地 Docker，也可以 `helm install` 到任意 K8s 集群。

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

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| **CRD 定义层** | `hiclaw-controller/api/v1beta1/types.go` · `helm/hiclaw/crds/*.yaml` | Worker / Team / Human / Manager 四种 CR 的 Go struct 与 OpenAPI schema |
| **应用骨架** | `hiclaw-controller/internal/app/app.go` (715 行) | 7 个 init 步骤组装 controller：scheme / 基础设施客户端 / backend / 控制器管理器 / 字段索引 / 认证 / 服务层 / reconciler / HTTP 服务 |
| **CR 控制器层** | `hiclaw-controller/internal/controller/{worker,team,human,manager}_controller.go` | 每种 CR 一组 controller-runtime Reconciler，对应 `*_reconcile_*.go` 拆分子任务（infra / rooms / container / config / delete / legacy / welcome） |
| **服务编排层** | `hiclaw-controller/internal/service/provisioner.go` (1154 行) · `deployer.go` · `credentials.go` · `worker_env.go` | Reconciler 调用的脏活集中地：Matrix 用户/房间生命周期、Higress consumer 创建、凭据签发与刷新、Pod 模板合并 |
| **容器后端（可插）** | `hiclaw-controller/internal/backend/{docker,kubernetes}.go` · `interface.go` · `registry.go` | `WorkerBackend` 接口 + 两个实现：Docker（单机模式）、Kubernetes（集群模式），由 `app.buildWorkerBackends` 按 config 选择 |
| **基础设施集成** | `internal/matrix/` · `internal/gateway/` · `internal/oss/` · `internal/credprovider/` · `internal/accessresolver/` | 各外部系统的客户端封装：Matrix admin API、Higress（apig-20240327）、MinIO/OSS、阿里云凭据提供者、AccessEntry 解析 |
| **HTTP / CLI 入口** | `internal/server/http.go` · `internal/apiserver/` · `cmd/hiclaw/main.go` · `cmd/controller/main.go` | controller 暴露 HTTP API；`hiclaw` CLI（注入 Manager/Worker 容器内）是该 API 的客户端 |
| **运行模式切换** | `internal/app/app.go::startEmbedded` (`k3s-io/kine` SQLite-backed etcd 跑 in-binary control plane) · `::startInCluster` (标准 KUBECONFIG) | 同一个 controller 二进制既可单机自带 K8s API 跑，也可作为标准 Operator 跑 |
| **Manager Agent** | `manager/agent/SOUL.md` · `TOOLS.md` · `skills/<name>/SKILL.md` × 12 · `workers-registry.json` · `state.json` | 容器化的 orchestrator Agent，用 12 个 skill（task / project / channel / worker / mcp-server / model-switch / file-sync 等）协调 Worker，通过 `hiclaw` CLI 操作 controller |
| **Worker runtime（三选一）** | `openclaw-base/Dockerfile`（Claude-Code 系） · `copaw/src/copaw_worker/`（QwenPaw, Python） · `hermes/src/hermes_worker/`（autonomous coding, Python） | Worker 容器内运行的 Agent 实现；Python runtime 自带 `bridge.py` 做 Matrix sync，OpenClaw 用宿主自身的 hook |
| **部署** | `helm/hiclaw/{Chart.yaml,values.yaml,crds,templates/{controller,element-web,gateway,matrix,secrets,storage}}` · `install/{hiclaw-install.sh,hiclaw-install.ps1,hiclaw-apply.sh,hiclaw-verify.sh}` | K8s Helm chart 一键部署完整栈；Docker 单机用 bash/PowerShell 安装脚本，二者部署形态对齐 |
| **辅助** | `migrate/` · `hack/` · `tests/` · `scripts/` · `blog/` · `changelog/` · `docs/` | 数据迁移、e2e 测试、blog/发版日志、设计文档 |

**关键约束（散文补充）：**

- **CRD 层不依赖业务层**：`api/v1beta1` 只 import `k8s.io/apimachinery` 与 `apiextensions`，绝不引用 `internal/` 任何包。这让 CRD 可被外部消费者（Manager Agent 也用同一组 struct）安全引用。
- **Reconciler 只编排，不实现**：每个 `*_controller.go` 都只是把 `WorkerBackend` 接口 + `Provisioner` 方法编排起来，**绝不**直接调 Matrix HTTP / Docker API。这让单元测试可 mock service 层（注意 `worker_controller_test.go` / `provisioner_sa_test.go` / `deployer_merge_test.go` 等大量测试）。
- **`provisioner.go` 是脏活集中地**：1154 行 / 29 个公开方法（`ProvisionWorker` / `DeprovisionWorker` / `ProvisionManager` / `ProvisionTeamRooms` / `EnsureRoomMember` / `ReconcileRoomMembership` / `EnsureGatewayAuth` / `RefreshCredentials` / …）。**这是首要的横向拆分候选**——按"Matrix 房间 / Higress 凭据 / Credentials store"切分。

## 关键数据流

### 端到端：管理员说"建一个 Go 代码评审 Worker"

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

### 通信信道（稳态）

```
Worker → LLM:    Worker 容器 ─consumer key→ Higress AI Gateway ─真实 API key→ LLM provider
Worker ↔ Worker: 双方都加入同一 Matrix 房间，消息走 Tuwunel；大文件落 MinIO（节省 token）
Worker ↔ Human:  Matrix 房间（管理员是房间成员，可以随时介入）
Worker → 工具:    Worker 容器 ─consumer key→ Higress ─route→ MCP server（external 或 in-cluster）
Manager → 控制器: Manager 容器内的 hiclaw CLI ─HTTP→ controller ─CR write→ etcd/kine
```

### 错误传递与回退

- **Matrix 创建失败 / 房间已存在**：`provisioner.ProvisionWorker` 内部做幂等（先 GET，再 PUT），失败回 controller-runtime 触发指数退避重试。
- **Higress consumer 创建失败**：reconcile 不进入下一步，`Worker.Status.Phase = Pending`，`Message` 写出原因。
- **容器后端失败**（如 docker daemon 不可达 / k8s API 不可达）：状态停留在 Pending，定期重试；CR 不变，所以重启 controller 后可继续。
- **退出**：`worker_controller` 的 finalizer 调 `Provisioner.DeprovisionWorker`，顺序：退房间 → 删 Matrix user → 撤 Higress consumer → 删 secret → 删容器 → 删 CR finalizer。

## 设计决策与哲学

- **K8s operator 模式套到 AI Agent 运维**：把"管一群 Agent"问题映射成"管一组 CR"，免费拿到 K8s 的 declarative / reconcile / self-healing / 多副本 / RBAC。这是 HiClaw 与 LangGraph/AutoGen/CrewAI 这类「代码中编排 Agent」框架的根本不同——它的 Agent 是**资源**而非**对象**。代码位置：`api/v1beta1/types.go:64` 起的 `Worker` struct 体现这点。

- **IM 协议（Matrix）作为协作平面的 lingua franca**：每个 Agent 都是一个 Matrix 用户，每场协作都是一个 Matrix 房间，人类天然是房间成员——可观测性与人在回路同时拿到。**这避免了"自研 Web UI + 自研事件总线"两个大坑**。代价：所有 Agent 都要做 Matrix 协议适配（`bridge.py` / OpenClaw 宿主 hook）。代码位置：`provisioner.go:285` `ProvisionWorker` 与 `provisioner.go:704` `ReconcileRoomMembership`。

- **凭据零暴露（Higress AI Gateway 为中介）**：Worker **永远拿不到**用户的 LLM API key、GitHub PAT、OSS AccessKey。它只有一个 Higress consumer key，所有外部访问都经 Higress 鉴权和路由。结果：开源/社区 skill 可大胆装载（skills.sh "80,000+ community skills"），因为 Worker 即便被 prompt-injection 攻陷也偷不到真凭据。代码位置：`internal/credprovider/` + `provisioner.go:600` `EnsureWorkerGatewayAuth`。

- **运行时三选一可插（OpenClaw / QwenPaw / Hermes）**：`WorkerSpec.Runtime` 字段控制底层 Agent 实现，三者各擅其长——OpenClaw（Claude Code 类，确定性工具调用强）、QwenPaw（基于通义千问 Code，省钱省 token）、Hermes（autonomous coding agent，自主性高）。最近 commit `d3e33e8` 把默认 runtime 从 OpenClaw 切到 QwenPaw，价格敏感倾向明显。代码位置：`api/v1beta1/types.go:73` 与 `internal/backend/registry.go`。

- **容器后端双轨（Docker / Kubernetes）**：`WorkerBackend` 是接口，`docker.go` 与 `kubernetes.go` 各一实现，`app.buildWorkerBackends` 按 config 选择。让"单机 Docker Desktop 上跑 5 个 Worker"和"K8s 集群上跑 500 个 Worker"用同一个 controller 二进制。代码位置：`internal/backend/interface.go` 定义、`internal/app/app.go:693` `buildWorkerBackends`。

- **嵌入式 K8s（kine + 内嵌 controller-manager）**：单机模式下 `startEmbedded` 跑 `k3s-io/kine`（SQLite 后端的 etcd 协议层）于 `127.0.0.1:2379` + 同进程的 controller-manager。**用户感觉是装了 Docker，骨子里跑了一套 K8s API**。这让 CRD/Reconcile/Helm 这一整套机制在没有真 K8s 的环境也成立。代码位置：`internal/app/app.go:519` `startEmbedded`。

- **schema-less 模板字段（AccessEntry.Scope / MCPServer）**：`AccessEntry.Scope` 用 `*apiextensionsv1.JSON` 而不是严格的 struct，并支持 `${self.name}` / `${self.kind}` / `${self.namespace}` 三种运行期变量。CRD 校验不绑死特定 cloud provider 的字段；解析延迟到 `accessresolver`。坏处：错误推迟到 reconcile；好处：CRD 一份适配多 provider。代码位置：`api/v1beta1/types.go:36-40`、`internal/accessresolver/`。

- **四 CRD 而非两 CRD**：Worker（单个 Agent）/ Team（一组 Worker + Leader）/ Manager（系统的唯一管家 Agent）/ Human（管理员的 Matrix 身份），都被建模成 CR。这让"Team 内增减成员"也是 reconcile 而非编程式 API。代码位置：`api/v1beta1/types.go:182-200` `TeamSpec`。

- **`hiclaw` CLI 注入 Worker/Manager 容器内**：Manager Agent 自身不引用 Go SDK，而是通过 fork CLI 来操作 controller HTTP API。**把"Agent 调 controller"做成"shell 命令"**——既复用了 controller 的 RBAC，又让 skill 系统（Manager skill 是 markdown）可以直接生成 `hiclaw worker create …` 这种命令字符串。代码位置：`cmd/hiclaw/main.go`、`manager/agent/skills/worker-management/SKILL.md`。

- **Skill via Nacos 包市场（Worker 维度）**：Worker 的能力（"代码评审" / "数据库迁移" / …）通过 `WorkerSpec.Package` 字段指向 `nacos://…` / `http(s)://…` / `file://…` 加载，Worker 启动时拉取。`hiclaw-find-worker` skill（在 Manager 侧）做的就是 Nacos 搜索 + 导入。**让 Worker 模板可分发**，类似 docker registry 之于镜像。

- **默认四层 label 优先级**：`pod-template < CR metadata.labels < CR spec.labels < controller 系统 label`（`hiclaw.io/controller` 强制由 controller 写入），保证多 controller 实例的事件隔离（`LabelController` 字段）。代码位置：`api/v1beta1/types.go:108-117` + `internal/controller/labels.go`。

## 关键组件深入解读

### Provisioner（`hiclaw-controller/internal/service/provisioner.go`，1154 行）

整个 controller 的"脏活集中地"。29 个公开方法可大致归三组：

1. **Matrix 编排**（`ProvisionWorker` / `ProvisionManager` / `ProvisionTeamRooms` / `LeaveAllWorkerRooms` / `DeleteWorkerRoom` / `EnsureRoomMember` / `EnsureRoomNonMember` / `ReconcileRoomMembership` / `DeleteWorkerRoomAlias` / …）：通过 Tuwunel 的 admin API 完成 user / room / membership / alias 的全生命周期。`MatrixUserID(name)` 与 `roomAliasLocalpart(kind, name)` 是命名规则集中点——所有的 `@name:domain` 与 room alias 都由此函数派生，保证幂等。
2. **Higress 凭据**（`EnsureManagerGatewayAuth` / `EnsureWorkerGatewayAuth` / `RefreshCredentials` / `RefreshManagerCredentials` / `DeleteCredentials`）：用 `alibabacloud-go/apig-20240327/v6` 在 Higress 上为每个 Agent 注册 consumer + key，作为它访问 LLM/OSS/MCP 的唯一凭据。Refresh 路径让 key 轮转能透明发生。
3. **Manager 引导**（`IsManagerLLMAuthReady` / `IsManagerJoinedDM` / `SendManagerWelcomeMessage` / `renderManagerWelcomeBody`）：Manager 容器第一次启动时，controller 检查它有没有就绪、有没有加入与管理员的 DM 房间，然后投递一段欢迎语（按 `language` / `timezone` 渲染）。这是"管理员打开 Element 立刻被 Manager 打招呼"的实现。

29 个方法平均 30+ 行，单文件 1154 行。**横向拆分时机已到**：建议按"Matrix"、"Higress"、"Credentials"、"Manager bootstrap" 四个域分到 `service/matrix_provisioner.go` / `gateway_provisioner.go` / `cred_provisioner.go` / `manager_bootstrap.go`，`Provisioner` 退化为外观（facade）。

### App 装配（`hiclaw-controller/internal/app/app.go`，715 行）

7 个 init 步骤串行执行（`App.New` 内的循环），每个对应一个职责：

```go
{"scheme",        a.initScheme},        // 注册 v1beta1 与 clientgoscheme
{"infra-clients", a.initInfraClients},  // matrix / higress / oss / nacos 客户端
{"backends",      a.initBackends},      // 选 docker 还是 kubernetes
{"ctrl-manager",  a.initControllerManager},  // controller-runtime Manager
{"field-indexers", a.initFieldIndexers}, // CR 字段索引（按 label 过滤）
{"auth",          a.initAuth},          // controller HTTP API 的 JWT + admin token
{"service-layer", a.initServiceLayer},  // Provisioner + Deployer 注入
{"reconcilers",   a.initReconcilers},   // 4 个 controller 注册到 Manager
{"http-server",   a.initHTTPServer},    // /api/v1/* 路由
```

`Start` 阶段额外做两件事：

- `startEmbedded` 或 `startInCluster` 之一返回 `*rest.Config`，作为 controller-runtime Manager 的输入
- `bootstrapAdminCLIToken` 提前为容器内 `hiclaw` CLI 写好 admin token（避免首次 reconcile 前 401）

这种"按命名清单循环 init"的写法极易扩展——加新模块只需 append 一个 `{name, initFn}` 对，且失败时能精确报错到哪一步。

### CRD 一族（`api/v1beta1/types.go`）

四种 CR 共享几个值得注意的模式：

- `LabelController = "hiclaw.io/controller"`：用 informer cache 的 label selector 让多 controller 实例不互相 reconcile（多租户隔离的关键）。
- `WorkerSpec.State *string`（`"Running"` / `"Sleeping"` / `"Stopped"`）：声明式的生命周期 desired state，与 K8s Pod 的 actual state 解耦。`DesiredState()` 方法兜底 `"Running"`。
- `WorkerSpec.AccessEntries []AccessEntry`：每条声明一个 service（`object-storage` / `ai-gateway`）+ 一组 permissions + 一个 schema-less Scope（含 `${self.*}` 模板变量）。让"给这个 Worker 一个能写 `agents/<它自己的名字>/*` 的 MinIO 桶"成为声明式语句。
- `WorkerSpec.Expose []ExposePort`：声明哪些容器端口要走 Higress 暴露出来。`Worker.Status.ExposedPorts` 给回 `(port, domain)` 对。这让 Worker 也能反向暴露 HTTP/gRPC 服务（譬如一个开 web UI 的 Worker）。
- `TeamSpec.Leader / Workers / PeerMentions / ChannelPolicy`：Team 表达"一组 Worker + 一个 Leader + 房间策略"，让"@all team-go" 这种语义自动落到正确的 Matrix 房间成员集上。

整个 types.go 约 ~300 行，几乎全是数据契约，没有逻辑——非常健康。

### Worker runtime 三态（`copaw/` / `hermes/` / `openclaw-base/`）

- **OpenClaw**：仅一个 `Dockerfile`（基础镜像），实际的 Agent 行为靠宿主 Claude Code 自身完成（Hook + Skill 系统）。Worker 容器内挂上 `soul.md` / `identity.md` / `skills/` / `mcporter-servers.json`，启动后 Claude Code 自然读取并行动。
- **QwenPaw**（`copaw/src/copaw_worker/`）：Python 实现，结构是 `cli.py` + `worker.py` + `bridge.py`（Matrix sync）+ `sync.py`（MinIO sync）+ `config.py`（配置加载）+ `templates/`（消息模板）+ 独立的 `matrix/` 子包做协议适配。
- **Hermes**（`hermes/src/hermes_worker/`）：与 QwenPaw 高度同构（`cli.py` / `worker.py` / `bridge.py` / `sync.py` / `config.py`），但底层使用 Hermes autonomous coding agent 的执行引擎，自主性更强。

**同构是有意的**：Python runtime 共享一套"bridge + sync + config" 的骨架，仅"调谁来生成下一句话"不同。新接入第四个 runtime 的成本理论上只是"换一个 LLM 调用客户端"。

## 与同类对比

| 维度 | HiClaw | AutoGen (Microsoft) | LangGraph | CrewAI |
|------|--------|---------------------|-----------|--------|
| 形态 | K8s operator + 容器化 Agent | Python library | Python library + LangChain | Python library |
| Agent 表达 | CR (YAML) | Python class | StateGraph node | Crew/Agent class |
| 部署单元 | Pod / Docker container | 进程 | 进程 | 进程 |
| 协作面 | Matrix 房间（IM）| In-process message bus | 显式 StateGraph 边 | Crew 内调度 |
| 人在回路 | 默认（房间成员） | 需自己接 UI | 需自己接 UI | 需自己接 UI |
| 凭据模型 | 网关托管，Agent 见不到真 key | Agent 直接持 API key | Agent 直接持 API key | Agent 直接持 API key |
| 跨 Agent 文件 | MinIO 共享桶 | 自己实现 | 自己实现 | 自己实现 |
| 工具调用 | MCP（mcporter-servers.json）| function calling | tool node | tool 列表 |
| 适合场景 | 多 Agent 长期跑、企业内部 | 研究 / 单进程内编排 | 复杂 DAG 工作流 | 角色化任务团队 |

最大差异是**部署形态**：HiClaw 把 Agent 当成 K8s 一等公民资源，所以 Agent 是"可被 reconcile 自愈、可被 helm 上线下线、可被 RBAC 限定可见性"的东西。其它三家本质上是"在你自己进程里跑一段 Python"，要做企业级运维要重头补。

代价：HiClaw 学习曲线显著更高（要懂 K8s + Matrix + Helm），且每个 Agent 一个容器有 RAM / 镜像下载开销——README 给的最低配置 2C/4G 仅适合 1-2 个 Worker。

## 性能 / 资源开销

| 项 | 数值 / 说明 | 数据来源 |
|---|---|---|
| 单机最低 | 2 CPU / 4 GB RAM | README："Resources: 2 CPU cores + 4 GB RAM minimum" |
| 多 Worker 推荐 | 4 CPU / 8 GB RAM | README："For multiple Workers, 4 cores + 8 GB recommended" |
| 镜像精简 | v1.1.0 较前版本缩减 1.7 GB | News：「1.7 GB image shrink」 |
| 控制平面状态 | embedded 模式走 kine + SQLite | `internal/app/app.go:519` 起 `ListenAddress: "127.0.0.1:2379"` |
| Reconcile 间隔 | controller-runtime 默认（指数退避，1s 起） | 未自定义，看不到 `RateLimiter` 覆盖 |
| Provisioner 单体 | 1154 行 / 29 方法 | 直接 `wc -l` |

**未测**：实际 reconcile 延迟、Matrix 房间数上限、kine SQLite 在多 Worker 下的写吞吐。

## 安全模型

**信任边界（从外向内）：**

1. **管理员 ↔ Element Web**：HTTPS + Matrix 登录密码 / SSO（Element 自身能力）。
2. **Element Web ↔ Tuwunel**：Matrix client-server API，可启用 E2E 加密。
3. **Tuwunel ↔ Worker bridge.py / OpenClaw hook**：consumer key（来自 Higress）做 access_token，仅能访问"自己被邀请加入的房间"。
4. **Worker ↔ Higress**：consumer key 鉴权。Higress 上配置 route 决定该 key 能访问哪些 LLM 路径 / MCP server / OSS 桶。
5. **Higress ↔ LLM / OSS / MCP**：真实凭据（OpenAI API key、阿里云 AK、GitHub PAT、…）只存在于 Higress 的 secret 里，所有 Worker 见不到。
6. **Controller ↔ K8s API / kine**：embedded 时是 in-process；in-cluster 时用 ServiceAccount + RBAC。

**主要攻击面：**

- **Worker prompt injection**：是 HiClaw 设计核心要防的场景。即便 Worker 被劫持，攻击者拿到的也只是 consumer key——可被立即在 Higress 侧 revoke，且只能访问被 route 限定的资源。这是 HiClaw 与其它框架的最大差别（其它框架被劫持 = 真 API key 泄漏）。
- **Matrix 房间侧信道**：Worker 会发什么消息到房间，房间成员会全部看到——这是设计而非漏洞（人在回路就靠这个）。但若把敏感数据塞进 prompt，会被房间审计成员看到。
- **Higress 自身**：成为单点目标，必须做好 Higress 控制面访问控制（README 提到 `gateway.publicURL` 配置）。
- **install 脚本 `curl | bash`**：标准社会工程攻击面。`install/hiclaw-install.sh` 加入了 `non-interactive deep-defense guards`（commit `6cbec18`）做一定缓解，但本质风险用户自担。
- **kine 单文件 SQLite**：embedded 模式所有 CR 状态压在一个文件里，文件损坏 = 状态丢失。建议生产用 in-cluster 模式。

**凭据 / 密钥存放：**

| 凭据 | 存放位置 | 谁能读 |
|------|----------|--------|
| 用户的 LLM API key | Higress secret（K8s Secret 或 docker volume）| Higress 本身 |
| GitHub PAT / 其它 token | 同上 | 同上 |
| Worker 的 Matrix access_token | controller credentials store（K8s Secret） | controller、Worker 容器自己 |
| Worker 的 Higress consumer key | controller credentials store | controller、Worker 容器自己 |
| admin CLI token | controller initializer 引导（`bootstrapAdminCLIToken`） | Manager / Worker 容器内的 `hiclaw` CLI |

## 代码统计（粗略）

- Go：153 个 `.go` 文件，主要在 `hiclaw-controller/`
- Python：30 个 `.py` 文件，主要在 `copaw/src/` 与 `hermes/src/`
- Markdown：151 个 `.md`，是 `manager/agent/skills/` 与 `docs/` 占大头
- `provisioner.go` 1154 行（最大单文件）；`app.go` 715 行（次大）
- 主要贡献者（近期）：澄潭（51）/ Jingze（17）/ CYJiang（10）/ YuFeng（5）/ johnlanni（4）

## 演进信号（最近 30 天 git 活动）

- `changelog/current.md`（37 次提交）→ 持续打磨发版细节
- `install/hiclaw-install.sh` 20 次 + `.ps1` 12 次 → "一行命令装上"是当前最高优先级
- `hiclaw-controller/internal/service/provisioner.go` 12 次 + `api/v1beta1/types.go` 12 次 + `config/config.go` 11 次 → controller 核心模型在快速迭代
- `helm/hiclaw/crds/workers.hiclaw.io.yaml` 10 次 → CRD schema 还在小步快迭，未冻结
- 关键 PR：`#780` 切默认 runtime 为 QwenPaw、`#749` 支持 `--keep-all` 升级模式、`#783` 修 `helm uninstall` 残留 pod、`#785` 修 manager 容器 API 路径对齐 controller `/api/v1`、`#798` 修 `error()` 在多行场景下意外退出
- 整体：v1.0 → v1.1 阶段，主线是"装上 / 升级 / 卸载体验"和"controller 凭据/房间稳定性"。下一步可能：Hermes runtime 主线化、多租户 RBAC 强化、kine → 真 etcd 平滑迁移工具
