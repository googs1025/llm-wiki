---
title: 操作日志
date: 2026-04-22
---

# 操作日志

## [2026-04-22] init | 知识库初始化

创建基础目录结构和 Schema（CLAUDE.md）。

## [2026-04-22] ingest | Kubernetes v1.36 Sneak Peek

来源：kubernetes.io blog。创建源摘要页，更新 kubernetes 实体页。关键：externalIPs 弃用、gitRepo 移除、SELinux GA、Ingress NGINX 退役。

## [2026-04-22] ingest | HolmesGPT 自动诊断 K8s 告警

来源：CNCF blog。创建源摘要页、ai-ops 概念页。关键发现：Runbook 比模型选择更重要。

## [2026-04-22] ingest | K3s + k0rdent GitOps On-Prem 部署

来源：CNCF blog。创建源摘要页、gitops 概念页。K3s + Proxmox + k0rdent 声明式集群管理。

## [2026-04-22] ingest | AI 驱动的漏洞发现变革

来源：CNCF blog (Greg Castle, Google)。创建源摘要页、cloud-native-security 概念页。AI 同时加速漏洞发现和噪声报告。

## [2026-04-22] ingest | Argo CD 概览

来源：argo-cd.readthedocs.io。创建源摘要页、argocd 实体页。K8s 声明式 GitOps CD 工具。

## [2026-05-12] ingest | claude-mem 架构与设计思路

来源：thedotmack/claude-mem v13.1.0 架构分析。新建源摘要页 + 3 实体页（claude-mem / claude-code / claude-agent-sdk）+ 4 概念页（agent-memory / event-driven-memory-pipeline / three-tier-search-protocol / ai-as-compressor）。核心洞察：AI 作为压缩器而非问答器，边缘轻量 + 后台异步，三层搜索防上下文爆炸。

## [2026-05-12] ingest | Claude Context 架构与 AI Agent 外挂设计原则

来源：zilliztech/claude-context v0.1.13 架构分析。新建源摘要页 + 3 实体页（claude-context / milvus / mcp）+ 4 概念页（code-semantic-search / hybrid-search-rrf / merkle-dag-fingerprint / ai-agent-plugin-patterns）。反向更新 claude-code（加 MCP 客户端能力）、claude-mem（链接 mcp）。核心洞察：9 条 AI Agent 外挂迁移原则（分层 / 接口化 / 降级链 / 内容指纹 / 协议通道纪律 / 协作式取消 / 流式批处理 / 快照自愈 / 混合检索）。
## [2026-05-13] ingest | HiClaw 架构

来源：agentscope-ai/HiClaw v1.1.0 架构分析（HEAD `e21ac83`）。**首次通过新建的 `ingest-codebase` skill 自动产出。** 新建 raw 文件（323 行）+ wiki source 页（226 行），ASCII 自查通过（raw 67 │ ↔ wiki 67 │ byte-identical）。核心洞察：K8s operator 模式套到 AI Agent 运维（CRD = Agent 声明，reconcile = 自愈）；Matrix IM 作协作平面（每个 Agent 是 IM 用户，人在回路天然成立）；Higress AI Gateway 托管真凭据（Worker 永远只持 consumer key 实现 prompt-injection 抗性）；OpenClaw/QwenPaw/Hermes 三 runtime 可插（最近默认从 OpenClaw 切到 QwenPaw）；嵌入式 K8s 走 kine SQLite 让"装上像 Docker，骨子里是 K8s"。

## [2026-05-13] ingest | agent-sandbox 架构

来源：kubernetes-sigs/agent-sandbox v0.4.5+11 架构分析（HEAD `e1d8898`）。`ingest-codebase` skill 第二次产出，整套流程稳定。新建 raw 文件（260+ 行）+ wiki source 页（200+ 行）+ 4 个实体页 stub（agent-sandbox / gvisor / kata-containers）+ 2 个概念页 stub（k8s-operator / k8s-crd / network-policy）。ASCII 自查 raw 86 │ ↔ wiki 81 │（94% 保留，差异来自"安全模型"信任边界图未带到 wiki）。核心洞察：(1) Sandbox CRD 把 "1 stable identity + 持久存储 + 可暂停 + 可调度销毁" 做成第一类 K8s 资源（不是 Deployment 也不是 StatefulSet），`replicas: 0|1` 强制约束承载暂停语义；(2) **隔离机制完全委托** K8s 原语——controller 不强制 gVisor/Kata/NetworkPolicy，全在用户填的 PodTemplate 里透传，最大化基座灵活性；(3) WarmPool + OwnerReference 热转移做出 ~0 启动延迟的 Claim 领养；(4) Template 级默认 NetworkPolicy = deny RFC1918 + deny 云元数据，把"AI Agent 跑用户代码的 SSRF 防御"做成系统约束；(5) 跟 [[HiClaw]] **互补不竞争**——前者基础设施层，后者应用层，HiClaw Worker 理论上可以跑在 agent-sandbox 上。

## [2026-05-14] ingest | PowerMem 架构

来源：oceanbase/powermem v1.1.1 架构分析（HEAD `2c83b77`，2026-05-13）。`ingest-codebase` skill 第四次产出。新建 raw 文件（约 290 行）+ wiki source 页（约 230 行），ASCII 自查 raw 107 │ ↔ wiki 107 │（byte-identical 100%）。Phase 2 串行追踪 9 个核心文件（README/pyproject/docs/architecture/overview/`__init__`/core/memory/intelligence/manager/storage/oceanbase/server/main 等），未启用 subagent —— 官方架构文档结构清晰，无需并行。核心洞察：(1) **跨形态统一中间件**：一个 `.env` 同时供 SDK / CLI / FastAPI / [[mcp]] / Dashboard / [[claude-code-plugin]] / VS Code 扩展，不复制状态给客户端；(2) **认知科学抽象 + 存储解耦**：working/short/long 三层 + [[ebbinghaus-forgetting-curve]] `R = e^(-t/S)`，Intelligence 不直接改库只在 metadata 写分数，`MemoryOptimizer` 离线扫描 —— 避免每次写都跑昂贵 LLM；(3) **[[hybrid-search-rrf]] + 自适应权重归一化是检索灵魂**：3 路（向量/全文/稀疏）并发后 `_normalize_weights_adaptively` 按实际命中路径重新归一权重，是 LOCOMO 78.7% 准确率（vs 52.9% baseline）+ p95 1.44s（vs 17.12s，11.8 倍）的算法贡献；(4) **[[oceanbase]] 优先但不绑死**：`VectorStoreFactory + StorageAdapter` 解耦，v1.1.0 引入嵌入式 SeekDB（`pyseekdb`）让用户用 OceanBase 语义但零部署；(5) **Provider 插件矩阵**：15 embedder + 12 LLM + 4 reranker，每个一文件一 config 类，跑通"Qwen + DashScope + OceanBase 全栈国产化"路径；(6) **Dashboard 打包进 wheel**：FastAPI 静态文件挂载 `/dashboard/`，`pip install` 即可用 Web UI；(7) **[[claude-code-plugin]] 用 Go 二进制做 hook**：跨平台原生编译无 Python 依赖，`UserPromptSubmit` 自动检索注入 `additionalContext`。

## [2026-05-13] ingest | agentgateway 架构

来源：agentgateway/agentgateway v1.2.0-alpha.2+24 架构分析（HEAD `9ca3e04`）。`ingest-codebase` skill 第三次产出。新建 raw 文件（约 360 行）+ wiki source 页（约 280 行），ASCII 自查 raw 134 │ ↔ wiki 130 │（98% 保留，2% 差距过关）。Phase 2 用 3 个并行 Explore subagent 分头扫 Rust 数据面 / 三协议网关 / Go 控制面。核心洞察：(1) **Istio 控制面骨架 + Rust 数据面**：Gateway API + KRT + xDS + HBONE 全套复用 mesh 基建，只把数据面换成专为 AI 协议优化的 Rust 代理，Day 1 获得完整 mesh 兼容性 + 控制面/数据面解耦；(2) **三协议（LLM / MCP / A2A）共享同一条 pipeline**：Route → Policy → Backend → CEL 求值，差别只在 Backend.kind 决定走哪个 provider 适配器，带来单一策略语言 + 统一观测；(3) **CEL 作策略 IR**：所有授权/转换/限流都编译成 CEL 表达式存到 Policy.spec.expression，controller 不预编译（避免 Go/Rust CEL 差异），用 cel-fork + celx 因为原生 cel-rust 缺 HTTP 集成；(4) **凭据托管堵 prompt injection**：LLM provider 真凭据放 backend secret，Agent 只面对 gateway 自身认证（与 [[HiClaw]] 哲学一致）；(5) **跟 [[agent-sandbox]] 互补**——前者运行时隔离，后者出口流量治理，并集 = AI 工作负载完整治理面。

## [2026-05-20] ingest | nanobot 架构

来源：googs1025/nanobot v0.2.0 架构分析（fork 自 HKUDS/nanobot）。`ingest-codebase` skill 第六次产出。新建 raw 文件（约 220 行）+ wiki source 页（约 200 行），ASCII 自查 raw 83 │ ↔ wiki 83 │（byte-identical 100%）。Phase 2 串行追踪 11 个核心文件（`__main__` / `nanobot.py` / `agent/loop.py` / `agent/runner.py` / `agent/context.py` / `agent/skills.py` / `channels/base.py` / `channels/registry.py` / `channels/manager.py` / `bus/{events,queue}.py` / `providers/{factory,fallback_provider,base}.py` / `command/router.py` / `cron/service.py` / `heartbeat/service.py` / `session/manager.py`），未启用 subagent —— 16k 行 Python 项目结构清晰，串行可控。核心洞察：(1) **事件驱动 8 态状态机替代单巨函数**：`TurnState{RESTORE,COMPACT,COMMAND,BUILD,RUN,SAVE,RESPOND,DONE}` + `_TRANSITIONS` 跳转表，让 `/stop → checkpoint → 下次 RESTORE 续接` 成为状态机一等公民；(2) **2-Queue MessageBus 解耦 channel 与 agent**：两条 `asyncio.Queue` 是唯一桥梁，channel 不 import agent、agent 不 import channel；(3) **channel pkgutil 自动发现 + entry_points 插件**：built-in 优先 shadow 外部插件，新增 channel 不动主代码；(4) **Provider 级 Failover 而非 Agent 级**：`FallbackProvider` 自身实现 `LLMProvider` 接口对 Agent 透明，`has_streamed` 跟踪防已吐字后跨模型拼接错乱，3 次失败 × 60s 熔断器，`_NON_FALLBACK_ERROR_KINDS` 区分"换模型救不了"提前短路；(5) **告别 litellm 回归原生 SDK**（2026-03-21 commit `3dfdab7`）—— `openai>=2.8` + `anthropic>=0.45` 原生 SDK + 自家 `openai_compat_provider` 走 OpenAI 协议方言，以代码量换控制力（精细处理 reasoning_content、Anthropic thinking_blocks、各家结构化错误码）；(6) **Mid-turn 注入**：每会话 `asyncio.Queue(maxsize=20)` 让用户在 Agent 工作时再发的消息塞队列而非抢锁，`_MAX_INJECTIONS_PER_TURN=3` 防失控，task 取消时残留消息重新 publish_inbound 不丢；(7) **Outbound 合并 + 去重**：`_coalesce_stream_deltas` 贪心合并连续 `_stream_delta`，SHA1 内容指纹 + `origin_message_id` 防重发；(8) **DM 配对码代替静默拒绝**：未授权 sender 私聊收到一次性配对码而非被无视；(9) **Skills/Memory/Dream/Heartbeat 是上下文层而非编排层**——`ContextBuilder` 把 `AGENTS.md`/`SOUL.md`/`USER.md`/`TOOLS.md`/MEMORY/skills 拼成 system prompt，`HeartbeatService` 让 LLM 通过虚拟 `heartbeat` tool 决定 skip/run；(10) **Per-session 串行 + Cross-session 并行**：`_session_locks` + `Semaphore(NANOBOT_MAX_CONCURRENT_REQUESTS=3)` 让多群 / 多人场景既不互相死等也不打爆 provider 配额。设计哲学贯穿 [[ai-agent-plugin-patterns]] 的"Markdown 即接口"+"pkgutil 自动发现"，与 [[claude-code]] 的 hook plugin 思路一脉相承。

## [2026-05-16] ingest | NVIDIA Dynamo 架构

来源：ai-dynamo/dynamo v1.2.0 架构分析（HEAD `7997117`）。`ingest-codebase` skill 第五次产出。新建 raw 文件（约 350 行）+ wiki source 页（约 250 行），ASCII 自查 raw 91 │ ↔ wiki 86 │（94.5% 保留，过关）。Phase 2 用 **6 个并行 Explore subagent** 分头扫前端/请求路径 / KV-aware router / KVBM 七 crate / 分布式 runtime / Python 组件 + Planner + PyO3 / 设计文档 + K8s operator + Grove —— 仓库太大（22 个 Rust crate + 896 个 .py + 258 个 .go），不并行根本读不完。核心洞察：(1) **三平面解耦**——请求平面（TCP/NATS Core）/ 控制平面（etcd/K8s/file Discovery trait）/ 存储事件平面（NATS JetStream + Object Store）独立演进，事件平面持久化保证 router 副本重启可 replay；(2) **Rust 内核 + Python 适配 + Go 控制器**三语言协作，性能敏感全在 Rust（HTTP、tokenize、路由、KVBM），backend 适配薄到"engine.generate + publish KV events"，K8s CRD 控制循环用 Go；(3) **请求迁移是默认能力**——`RetryManager` 让 worker 死亡对客户端透明，guided decoding/n>1 因状态机不可复制被显式排除，这是 Dynamo 区别于 [[vllm]]/[[sglang]] 这类单机推理引擎的根本特征；(4) **KV 块的全局身份 = SequenceHash**（128-bit PositionalLineageHash，XXH3 seed=1337，LoRA id 混入），让块在 GPU/CPU/SSD/S3 + 多 worker 之间有同一个名字，consolidator 去重、router 前缀匹配、KVBM 升降级都基于它；(5) **KVBM 四级层次（G1-G4）+ NIXL 统一传输**——LRU 管 G1→G2、TinyLFU+presence 管 G2→G3、所有层包装成 NIXL MemType 让 GPUDirect RDMA/NVMe-oF/S3 路径同形；(6) **KV-aware 路由 ≠ 最大化命中率**——cost function 同时惩罚 overlap 不足和负载，softmax(−cost) 采样而非 argmin，多 router 副本经 JetStream 同步 AddRequest/MarkPrefillCompleted/Free 事件；(7) **AIConfigurator → Planner → Operator 三段式 SLA 闭环** 是 1.0 "zero-config DGDR" 的实现基础——离线扫 10K+ 配置选 Pareto 前沿 → 在线决策扩缩 → K8s 资源物化；(8) **拓扑感知外包给 Grove**——operator 不做 NVL72/rack placement，翻译成 PodCliqueSet/PodCliqueScalingGroup 交给外部 scheduler。

## [2026-05-21] ingest | agentmemory 架构（v0.9.21）

Rohit Ghumare 出品的本地化跨 Agent 持久记忆服务。TS + iii-engine（钉 v0.11.2）+ SQLite，三流（BM25+Vector+Graph）RRF 检索 + 零 LLM 启发式压缩默认 + 12 个 Claude Code hooks + 53 MCP tools（默认仅暴露 8）+ 124 REST endpoints + 实时 viewer。关键设计：iii-engine 强制总线 / 向量维度守卫（不匹配拒绝启动）/ Context injection 默认关（#143 token 杀手）/ 多层记忆（32+ KV scope + Ebbinghaus 衰减）。与 claude-mem / powermem 互为镜像（同问题三种实现）。

## [2026-06-01] ingest | AgentCube 架构

来源：volcano-sh/agentcube HEAD `208da32`（2026-06-01）。`ingest-codebase` skill Codex 版首次实战产出。新建 raw 文件 + wiki source 页 + [[agentcube]] 实体页，并按用户要求重点补充与 [[agent-sandbox]] 的结合关系。核心洞察：(1) AgentCube 不是替代 agent-sandbox，而是把 `Sandbox` / `SandboxClaim` / `SandboxTemplate` / `SandboxWarmPool` 包成 `AgentRuntime` / `CodeInterpreter` + Router + WorkloadManager + SDK 的会话编排层；(2) Router/WorkloadManager 分平面：Router 走 `x-agentcube-session-id` 做高频反向代理，WorkloadManager 负责 K8s 创建、Ready 等待、entrypoint probe 和 GC；(3) CodeInterpreter 的 `warmPoolSize` 直接驱动 agent-sandbox WarmPool，首次调用创建 `SandboxClaim` 领取预热 Pod；(4) PicoD 用 HTTP + Router-signed JWT 替代 SSH，当前代码安全模型已从旧文档的"客户端私钥签名"演进到 Router→PicoD trust chain；(5) Redis/ValKey 只做 session registry，不做复杂任务队列。

## [2026-06-02] ingest | SkyPilot 架构

来源：googs1025/skypilot master HEAD `55b9185`（2026-06-01）。由于 git clone 传输超时，本次使用 GitHub archive 下载源码，并用 GitHub API 校验 HEAD。新建 raw 文件 + wiki source 页，重点梳理 SkyPilot 作为 AI/ML 多云算力控制平面的分层：CLI/SDK/YAML → API server request 队列 → execution stage runner → Optimizer → CloudVmRayBackend → cloud/provision provider。核心洞察：(1) API server 是所有重操作边界，CLI 只提交 request_id 和流式日志；(2) Task/Dag/Resources 是稳定 IR，隔离用户声明和云 API；(3) failover 是 provisioning 失败后带 blocked_resources 的重新优化；(4) managed jobs / SkyServe / pools 都是控制器模式，复用普通 `sdk.launch()` / `sdk.down()`；(5) 安全模型集中在 API server auth、Casbin RBAC、workspace permission 和状态 DB。

## [2026-06-03] ingest | AI Agent Frameworks Star 项目清单

来源：GitHub Stars list `googs1025/lists/ai-agent-frameworks`（109 个仓库，描述为“Claude/LangChain/LangGraph/MCP/Agent SDK”）。新建 raw 清单 + wiki source 页，按个人 Agent / Agent OS、Coding Agent / Claude Code 生态、Agent framework / workflow 平台、MCP / SDK / gateway、Skills / prompt pack、记忆 / 上下文 / 观测 / 评测、cloud-native runtime 七层整理。核心洞察：(1) Agent 工程开始明显分层，上层是可直接使用的 Agent / Agent OS，底层是 Skills、MCP、memory、observability、gateway、sandbox 和 cloud-native runtime；(2) Claude Code 形成事实生态，router、templates、skills、memory、trace viewer、token tracker、IM bridge、Codex plugin、code graph 都围绕 terminal coding agent 扩展；(3) OpenClaw / Hermes / OpenClaude / Claw 系项目说明“个人 Agent + 多平台入口 + sandbox + memory + messaging”正在产品化；(4) MCP 从协议变成基础设施层，FastMCP、GitHub MCP、Playwright MCP、Kubernetes MCP、agentgateway / Plano 都在同一个 tool/resource 接入面上竞争；(5) Skills 成为新的可迁移能力包，适合继续和 Codex skills 迁移实践对照。

## [2026-06-02] ingest | AgentScope 架构

来源：agentscope-ai/agentscope main HEAD `e129177`（2026-06-01）。完整 clone 因 GitHub HTTP/2 framing 失败，本次使用 HTTP/1.1 浅克隆完成源码分析。新建 raw 文件 + wiki source 页，重点梳理 AgentScope 2.0 作为 Python 多 Agent 应用框架的分层：Agent 事件流 ReAct loop → ChatModelBase/Formatter provider 适配 → Toolkit/MCP/Skill → PermissionEngine → Workspace/offload → FastAPI ChatService/session/storage。核心洞察：(1) `AgentEvent` / `Msg` 是 SDK、SSE、存储和 UI 的统一协议；(2) 人类确认和外部执行是一等 continuation 状态，不阻塞进程；(3) 工具执行拆成 permission/context lifecycle 与 raw I/O，让 middleware 只拦截安全边界后的工具流；(4) Workspace 同时承接 tools/MCP/skills 和 context/tool-result offload，是 Local/Docker/E2B 后端的统一抽象；(5) 服务层每轮从 storage/session/workspace 重新组装 Agent，慢工具通过 `ToolOffloadMiddleware` 后台化并在完成后重新注入 reasoning。

## [2026-06-04] ingest | K8s GPU & Device Plugins Star 项目清单

来源：GitHub Stars list `googs1025/lists/k8s-gpu-device-plugins`（36 个仓库，描述为“GPU/异构、device-plugin、DRA、vGPU”）。新建 raw 清单 + wiki source 页，按 NVIDIA GPU 基座、GPU sharing/vGPU、DRA/CDI 标准化、可观测/诊断/测试替身、GPU workload 边界整理。核心洞察：(1) Kubernetes GPU 资源层已经从 device plugin 扩展成 driver/runtime/operator、feature discovery、metrics、diagnostics、sharing 和 DRA 的完整栈；(2) GPU sharing 仍有 gpushare、TKE gpu-manager、4paradigm vgpu-scheduler、HAMi、Volcano vGPU 多条路线；(3) DRA/CDI 是下一代设备资源抽象主线；(4) LLM serving 让 KV cache、GPU sharing 和资源调度开始交叉。

## [2026-06-04] ingest | K8s Core & Controllers Star 项目清单

来源：GitHub Stars list `googs1025/lists/k8s-core-controllers`（359 个仓库，描述为“K8s 主线、controllers、operator SDK、CRD、kubectl、client-go”）。新建 raw 清单 + wiki source 页，按 K8s 主线与本地集群、Controller/Operator SDK、API machinery、调度与弹性、多集群/虚拟集群/边缘、网络/存储/备份、安全/策略/准入、可观测/诊断/AI Ops 整理。核心洞察：(1) 这是 Kubernetes 平台工程学习路径图，而不是普通项目集合；(2) `client-go` / `controller-runtime` / `kubebuilder` / sample-controller 构成 controller 开发主线；(3) 生产控制器已从 Operator CRUD 扩展到调度、队列、资源经济、多集群和诊断；(4) k8sgpt/kubectl-ai/krr/kubewizard/kube-agent-helper 说明 AI Ops 正进入 K8s controller 生态。

## [2026-06-05] ingest | NemoClaw 架构

来源：NVIDIA/NemoClaw HEAD `3c0340a`（2026-06-05）。新建 raw 架构分析 + wiki source 页 + HTML baseline，重点梳理 NemoClaw 作为 OpenShell sandbox 内 always-on AI Agent 的 host-side CLI 控制面：sandbox-first CLI public dispatcher、thin commands、onboard FSM、OpenShell gateway 托管凭证、`inference.local` 统一推理路由、manifest-driven messaging、deny-by-default policy presets 与 host-side shields。核心洞察：(1) 项目不是推理引擎，而是把 host/gateway/sandbox/agent/provider 边界显式编排；(2) Onboard 正在从巨型流程向可恢复 FSM result 演进；(3) 凭证 system-of-record 在 OpenShell gateway，NemoClaw 只做进程 env staging；(4) messaging channel 通过 serializable plan 扩展，避免继续膨胀主 onboard 流程。

## [2026-06-05] ingest | OpenShell 架构

来源：NVIDIA/OpenShell HEAD `97986d9`（2026-06-05）。完整 clone 因网络传输超时，本次使用 GitHub codeload archive，并用 GitHub API 校验 HEAD 与近期提交。新建 raw 架构分析 + wiki source 页 + HTML baseline，重点梳理 OpenShell 作为 AI Agent 安全私有运行时的边界：Gateway 控制面、compute driver、sandbox Supervisor、policy proxy、provider credential 与 `inference.local` 路由。核心洞察：(1) Gateway owns desired state，Supervisor owns runtime enforcement；(2) sandbox 通过 outbound supervisor session 连接 Gateway，connect/exec/file sync 走 reverse relay；(3) proxy 以 `/proc/net/tcp` + binary identity + OPA 做网络决策，并叠加 SSRF、TLS/L7、credential rewrite；(4) policy proposal 由 Z3 prover 审核 delta，默认人工审批；(5) 项目仍在 alpha/快速迭代，最近修复集中在 startup resume、Kubernetes hardening、bootstrap 可复现性和 CLI 体验。

## [2026-06-06] ingest | agent-recall 架构

来源：mnardit/agent-recall main HEAD `dcf21b5`（2026-04-03）。新建 raw 架构分析 + wiki source 页 + [[agent-recall]] 实体页，重点梳理本地优先 MCP-native Agent 记忆库：FastMCP tools / CLI / Claude hooks → MCPBridge scope enforcement → SQLite MemoryStore → context_gen AI briefing cache。核心洞察：(1) Store 明确不做 scope enforcement，MCPBridge 是多 Agent 权限边界；(2) scope hierarchy + bitemporal slots 支撑同一实体在不同客户/项目下的不同事实；(3) MCP server instructions 把“主动保存记忆”嵌进协议入口；(4) AI briefing 是可缓存压缩层，不是数据真相层；(5) Hook 设计偏轻量，优先读 cache，写入后只做 stale marker / vault regen。

## [2026-06-07] ingest | memsearch 架构

来源：zilliztech/memsearch v0.4.6 / HEAD `018a85f`（2026-06-01）。新建 raw 架构分析 + wiki source 页 + [[memsearch]] 实体页，并补齐已有引用缺失的 [[milvus]] 实体页。重点梳理跨平台 AI coding agent 语义记忆：Claude Code / Codex / OpenCode / OpenClaw hooks → `.memsearch/memory/*.md` Markdown source-of-truth → Scanner/Chunker/composite chunk ID → Milvus dense + BM25 sparse + RRF → search/expand/transcript progressive recall。核心洞察：(1) Milvus 是可重建 shadow index，事实保存在 Markdown；(2) chunk 主键绑定 source/line/content/model，支撑增量索引和模型隔离；(3) 平台插件只处理宿主 hook/transcript，Python core 只处理 Markdown；(4) `expand` 把检索结果回源到完整 heading section，防上下文爆炸；(5) Codex 插件首次体验偏 ONNX + Milvus Lite，同时保留 Server/Zilliz Cloud 和多 embedding provider 路径。

## [2026-06-07] ingest | TencentDB-Agent-Memory 架构

来源：TencentCloud/TencentDB-Agent-Memory v0.3.6 / HEAD `f92b102`（2026-06-04）。新建 raw 架构分析 + wiki source 页 + [[tencentdb-agent-memory]] 实体页，重点梳理 OpenClaw / Hermes Agent 记忆插件：OpenClaw hooks/tools 或 Hermes Python provider → host-neutral `TdaiCore` → L0 Conversation / L1 Atom / L2 Scenario / L3 Persona → SQLite + sqlite-vec/FTS5 或 Tencent Cloud VectorDB → auto-recall 与主动工具下钻；同时梳理 context offload：工具日志写 refs，L1/L1.5/L2 生成 Mermaid MMD，L3 按 token 阈值压缩。核心洞察：(1) 宿主适配器和 core 分离，让 in-process 插件与 HTTP sidecar 复用同一套 pipeline；(2) 长期记忆不是平铺向量，而是低层证据 + 中层场景 + 高层 persona；(3) auto-recall 把动态 L1 和稳定 L2/L3 分开注入以利于 prompt cache；(4) SQLite 路径本地优先，TCVDB 路径走 server-side embedding + native hybridSearch；(5) Gateway auth/CORS 默认兼容旧部署但启动时显式提示暴露风险。

## [2026-06-07] query | Agent Memory 项目地图

整理当前知识库里已摄入的 memory 相关项目，新增 [[agent-memory-project-map]] 分析页。横向对比 [[claude-mem]]、[[agent-recall]]、[[agentmemory]]、[[powermem]]、[[memsearch]]、[[tencentdb-agent-memory]] 的宿主入口、事实源、采集方式、压缩策略、检索路径、注入方式、强项和代价；并归纳 source-of-truth、自动捕获 vs 主动记忆、LLM 压缩成本、[[hybrid-search-rrf]]、[[three-tier-search-protocol]] 等共同设计轴。

## [2026-06-09] query | Agent Memory 项目地图深化

按工程架构深挖方向扩写 [[agent-memory-project-map]]。新增架构交叉矩阵，细化 hook-worker、MCP tool、truth store/shadow index、hybrid retrieval 等共同模式；系统比较 memory 写入方式（被动事件捕获、主动工具写入、SDK 写入、Markdown append、L0→L3 分层管线、briefing cache、context offload）；补充六个项目的工程剖面和核心难点，包括写入质量、延迟隔离、索引一致性、事实冲突、scope 权限、上下文注入、RRF 融合和可观测恢复。

## [2026-06-09] query | 三篇项目地图补全

根据现有 wiki 聚类，新增三篇横向分析页：[[agent-runtime-sandbox-project-map]]、[[llm-inference-serving-project-map]]、[[ai-agent-frameworks-map]]。第一篇整理 [[agent-sandbox]]、[[agentcube]]、OpenShell、NemoClaw、[[HiClaw]]、AgentScope、[[agentgateway]] 的 runtime/sandbox/control-plane 分层；第二篇整理 [[vllm]]、[[sglang]]、[[dynamo]]、SkyPilot 与 K8s GPU stack 的 serving 分层；第三篇整理 coding agent、Agent framework、MCP/gateway、skills、memory/context、runtime substrate 的 Agent 生态分层。同步更新 Wiki 索引的 Analysis 区和待建条目。

## [2026-06-11] query | 八篇项目选型对比地图

按用户要求把可继续横向对比的方向扩成 8 篇细分分析页，并在写作前重新通过 GitHub API 复核相关仓库的 default branch、最近 push、语言、license 与 stars，避免只沿用旧文章结论。新增 [[coding-agent-selection-map]]、[[agent-memory-selection-matrix]]、[[agent-runtime-sandbox-selection-map]]、[[llm-serving-engine-selection-map]]、[[mcp-gateway-tooling-map]]、[[agent-skills-plugin-system-map]]、[[code-semantic-search-rag-map]]、[[agent-framework-programming-model-map]]。重点从项目定位、架构边界、控制流/数据流、依赖面、成熟度、取舍和选型入口解释差异，帮助快速理解项目与技术选型。

## [2026-06-12] query | GitHub Stars P0-P2 摄入候选清单

按用户要求把 GitHub Stars 中 P0-P2 候选项目全部加入 wiki backlog，新增 [[github-stars-ingest-candidates]]。本次通过 GitHub API 复核 `googs1025` starred repositories 当前列表，并把候选按 Agent Runtime/Substrate、Agent Memory、Coding Agent、Personal Agent、LLM Serving、AI Gateway、K8s AI Ops、Code Graph、GPU/DRA 分组；其中 `agent-substrate/substrate` 标为 P0 最高优先级，`oceanbase/powermem` 标记为已摄入、后续只需复查更新。

## [2026-06-12] query | AI Infra Learning 中文学习项目整理

根据用户给出的 GitHub Stars list `googs1025/lists/ai-infra-learning-中文`，通过 GitHub GraphQL API 复核 32 个仓库条目，新增 [[src-ai-infra-learning-cn-stars]] 和 [[ai-infra-learning-cn-map]]。本次不是 backlog 占位，而是把学习项目正式整理成 AI 系统全景、LLM 基础/开源模型、CUDA/GPU kernel、LLM 推理优化、工程化/LLMOps、Agent/Skills、面试材料七层路线，并标出最值得后续单独摄入的项目：AISystem、AIInfra、InfraTech、LeetCUDA、Awesome-LLM-Inference、self-llm、hello-agents、nanoclaw。

## [2026-06-12] query | GitHub Stars P0-P2 backlog 实现

根据用户要求“不只是加入 backlog，而是实现这部分”，重新通过 GitHub API 核对 [[github-stars-ingest-candidates]] 里的 P0-P2 共 39 个项目，新增 [[src-github-stars-backlog-current-state]] 和 [[github-stars-backlog-implementation-map]]。本次把候选项目正式放入 runtime/substrate、agent memory、coding agent 执行面、managed/desktop agent、LLM serving on K8s、AI Gateway/routing、K8s AI assistant、Code Graph/Repo Wiki、GPU/DRA/device plugin 九条选型主线，并在原 backlog 页标注实现状态。

## [2026-06-12] query | GitHub Stars P0-P2 raw 快照补齐

根据用户追问“为何没有一个个加到 raw 里面”，补齐 [[github-stars-ingest-candidates]] 对应 P0-P2 共 39 个项目的 `raw/github-stars-p*-*.md` GitHub 当前状态快照，并更新 [[src-github-stars-backlog-current-state]] 标明 raw 追溯文件清单。当前这些 raw 文件是 GitHub API 元数据快照，不冒充完整源码架构分析；后续逐仓库深挖时再生成 `raw/*-architecture-analysis.md`。

## [2026-06-12] ingest | Agent Substrate 架构

按用户要求开始用 `ingest-codebase` 补 P0-P2 项目的逐仓库源码架构分析，首个项目为 `agent-substrate/substrate`。由于 git clone 先后遇到 GitHub HTTP/2 framing 和 443 连接失败，本次使用 GitHub codeload tarball 获取源码，并用 GitHub API 校验 HEAD `a3f4474`。新增 `raw/substrate-architecture-analysis.md`、[[src-substrate-architecture]] 和对应 HTML。核心结论：Substrate 把 K8s 用作低频容量/模板控制面，把高频 Actor/Worker 状态放入 Redis/ValKey；ActorTemplate 生成 golden snapshot；atenet 通过 actor DNS + Envoy ext_proc 唤醒 actor；atelet/ateom-gvisor 负责 runsc snapshot/restore 和 link-local veth/nftables 网络桥。

## [2026-06-12] ingest | AgentScope Runtime 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `agentscope-ai/agentscope-runtime`，HEAD `22072fd`（2026-06-04）。
- 新增 `raw/agentscope-runtime-architecture-analysis.md` 与 `wiki/sources/src-agentscope-runtime-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | mem0 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `mem0ai/mem0`，HEAD `2c796d1`（2026-06-12）。
- 新增 `raw/mem0-architecture-analysis.md` 与 `wiki/sources/src-mem0-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | ReMe 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `agentscope-ai/ReMe`，HEAD `f458566`（2026-06-10）。
- 新增 `raw/reme-architecture-analysis.md` 与 `wiki/sources/src-reme-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | OpenAI Codex CLI 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `openai/codex`，HEAD `bf667c7`（2026-06-12）。
- 新增 `raw/codex-architecture-analysis.md` 与 `wiki/sources/src-codex-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | Pi Agent Harness 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `earendil-works/pi`，HEAD `3f44d3e`（2026-06-12）。
- 新增 `raw/pi-architecture-analysis.md` 与 `wiki/sources/src-pi-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | oh-my-pi 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `can1357/oh-my-pi`，HEAD `12290e0`（2026-06-12）。
- 新增 `raw/oh-my-pi-architecture-analysis.md` 与 `wiki/sources/src-oh-my-pi-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | Multica 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `multica-ai/multica`，HEAD `99afb82`（2026-06-12）。
- 新增 `raw/multica-architecture-analysis.md` 与 `wiki/sources/src-multica-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | Open Cowork 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `OpenCoworkAI/open-cowork`，HEAD `8e60460`（2026-06-07）。
- 新增 `raw/open-cowork-architecture-analysis.md` 与 `wiki/sources/src-open-cowork-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | AIBrix 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `vllm-project/aibrix`，HEAD `ac2c161`（2026-06-11）。
- 新增 `raw/aibrix-architecture-analysis.md` 与 `wiki/sources/src-aibrix-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | llm-d 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `llm-d/llm-d`，HEAD `2734681`（2026-06-12）。
- 新增 `raw/llm-d-architecture-analysis.md` 与 `wiki/sources/src-llm-d-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | llm-d Router 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `llm-d/llm-d-router`，HEAD `a0173a7`（2026-06-12）。
- 新增 `raw/llm-d-router-architecture-analysis.md` 与 `wiki/sources/src-llm-d-router-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | llm-d KV Cache 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + codeload tarball 重新扫描 `llm-d/llm-d-kv-cache`，HEAD `26e2b6f`（2026-06-11）。
- 新增 `raw/llm-d-kv-cache-architecture-analysis.md` 与 `wiki/sources/src-llm-d-kv-cache-architecture.md`，用于把 P0 backlog 从 metadata snapshot 升级为正式源码架构页。

## [2026-06-12] ingest | kagent 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kagent-dev/kagent`，HEAD `feb8cf9`（2026-06-12）。
- 新增 `raw/kagent-architecture-analysis.md` 与 `wiki/sources/src-kagent-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | kubectl-ai 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `GoogleCloudPlatform/kubectl-ai`，HEAD `08cf256`（2026-03-25）。
- 新增 `raw/kubectl-ai-architecture-analysis.md` 与 `wiki/sources/src-kubectl-ai-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | k8m 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `weibaohui/k8m`，HEAD `718e894`（2026-04-10）。
- 新增 `raw/k8m-architecture-analysis.md` 与 `wiki/sources/src-k8m-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | kubewall 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kubewall/kubewall`，HEAD `fd575ff`（2026-05-19）。
- 新增 `raw/kubewall-architecture-analysis.md` 与 `wiki/sources/src-kubewall-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | Gateway API Inference Extension 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kubernetes-sigs/gateway-api-inference-extension`，HEAD `974d27c`（2026-06-11）。
- 新增 `raw/gateway-api-inference-extension-architecture-analysis.md` 与 `wiki/sources/src-gateway-api-inference-extension-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | Envoy AI Gateway 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `envoyproxy/ai-gateway`，HEAD `9a4b02c`（2026-06-12）。
- 新增 `raw/ai-gateway-architecture-analysis.md` 与 `wiki/sources/src-ai-gateway-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | kgateway 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kgateway-dev/kgateway`，HEAD `1560573`（2026-06-11）。
- 新增 `raw/kgateway-architecture-analysis.md` 与 `wiki/sources/src-kgateway-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | Higress 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `higress-group/higress`，HEAD `2897c1e`（2026-06-07）。
- 新增 `raw/higress-architecture-analysis.md` 与 `wiki/sources/src-higress-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | vLLM Semantic Router 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `vllm-project/semantic-router`，HEAD `9893c2c`（2026-06-11）。
- 新增 `raw/semantic-router-architecture-analysis.md` 与 `wiki/sources/src-semantic-router-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | RouteLLM 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `lm-sys/RouteLLM`，HEAD `0b64fda`（2024-08-09）。
- 新增 `raw/routellm-architecture-analysis.md` 与 `wiki/sources/src-routellm-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | Plano 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `katanemo/plano`，HEAD `2e38f7f`（2026-06-09）。
- 新增 `raw/plano-architecture-analysis.md` 与 `wiki/sources/src-plano-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | GPUStack 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `gpustack/gpustack`，HEAD `05d56cd`（2026-06-12）。
- 新增 `raw/gpustack-architecture-analysis.md` 与 `wiki/sources/src-gpustack-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | OME 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `ome-projects/ome`，HEAD `e91ed23`（2026-06-09）。
- 新增 `raw/ome-architecture-analysis.md` 与 `wiki/sources/src-ome-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | KServe 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kserve/kserve`，HEAD `ccf1d3d`（2026-06-12）。
- 新增 `raw/kserve-architecture-analysis.md` 与 `wiki/sources/src-kserve-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | KubeAI 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kubeai-project/kubeai`，HEAD `1fe298d`（2026-03-31）。
- 新增 `raw/kubeai-architecture-analysis.md` 与 `wiki/sources/src-kubeai-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | code-review-graph 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `tirth8205/code-review-graph`，HEAD `b72413c`（2026-06-10）。
- 新增 `raw/code-review-graph-architecture-analysis.md` 与 `wiki/sources/src-code-review-graph-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | GitNexus 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `abhigyanpatwari/GitNexus`，HEAD `14397dd`（2026-06-12）。
- 新增 `raw/gitnexus-architecture-analysis.md` 与 `wiki/sources/src-gitnexus-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | deepwiki-open 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `AsyncFuncAI/deepwiki-open`，HEAD `16f35a0`（2026-06-03）。
- 新增 `raw/deepwiki-open-architecture-analysis.md` 与 `wiki/sources/src-deepwiki-open-architecture.md`，将 P1 backlog 升级为正式源码架构页。

## [2026-06-12] ingest | Codex Plugin for Claude Code 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `openai/codex-plugin-cc`，HEAD `807e03a`（2026-04-18）。
- 新增 `raw/codex-plugin-cc-architecture-analysis.md` 与 `wiki/sources/src-codex-plugin-cc-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | claude-tap 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `liaohch3/claude-tap`，HEAD `a11231b`（2026-06-12）。
- 新增 `raw/claude-tap-architecture-analysis.md` 与 `wiki/sources/src-claude-tap-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | cc-connect 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `chenhg5/cc-connect`，HEAD `c53f545`（2026-06-10）。
- 新增 `raw/cc-connect-architecture-analysis.md` 与 `wiki/sources/src-cc-connect-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | Tokscale 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `junhoyeo/tokscale`，HEAD `aebe4ea`（2026-06-10）。
- 新增 `raw/tokscale-architecture-analysis.md` 与 `wiki/sources/src-tokscale-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | HAMi 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `Project-HAMi/HAMi`，HEAD `5dca58e`（2026-06-11）。
- 新增 `raw/hami-architecture-analysis.md` 与 `wiki/sources/src-hami-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | DRA Driver for NVIDIA GPUs 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `kubernetes-sigs/dra-driver-nvidia-gpu`，HEAD `749a743`（2026-06-11）。
- 新增 `raw/dra-driver-nvidia-gpu-architecture-analysis.md` 与 `wiki/sources/src-dra-driver-nvidia-gpu-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | NVIDIA GPU Operator 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `NVIDIA/gpu-operator`，HEAD `0219120`（2026-06-11）。
- 新增 `raw/gpu-operator-architecture-analysis.md` 与 `wiki/sources/src-gpu-operator-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。

## [2026-06-12] ingest | NVIDIA k8s-device-plugin 架构

- 使用 `$ingest-codebase` 方式从 GitHub API + tarball 重新扫描 `NVIDIA/k8s-device-plugin`，HEAD `8688949`（2026-06-10）。
- 新增 `raw/k8s-device-plugin-architecture-analysis.md` 与 `wiki/sources/src-k8s-device-plugin-architecture.md`，将 P2 backlog 升级为正式源码架构页，并补充同类架构差异与选型提示。
