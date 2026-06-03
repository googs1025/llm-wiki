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
