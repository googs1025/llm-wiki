# AI Agent Frameworks Star 项目清单整理

> 来源：https://github.com/stars/googs1025/lists/ai-agent-frameworks · 抓取日期：2026-06-03 · GitHub list 描述：Claude/LangChain/LangGraph/MCP/Agent SDK · 仓库数：109 · list 更新时间：2026-05-12 15:29:55 UTC

## 一句话定位

这个 Star list 不是单纯的“Agent 框架合集”，而是围绕 AI Agent 工程化的完整生态地图：上层是 OpenClaw / Hermes / Claude Code / OpenCode 这类可直接使用的个人或编码 Agent；中层是 LangChain、LangGraph、Dify、AgentScope、Eino、ADK、Dapr 等 Agent / workflow 框架；底层则延伸到 MCP、Skills、记忆、观测、评测、网关、安全沙箱、Kubernetes runtime 和多云算力。

## 分层地图

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ End-user agents / coding agents                                              │
│ OpenClaw · Hermes · Claude Code · OpenCode · OpenClaude · CodeWhale · Pi     │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Agent frameworks / workflow platforms                                        │
│ LangChain · LangGraph · Dify · AgentScope · Eino · ADK · Dapr · YoMo         │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Tooling protocols / gateway / SDK                                            │
│ MCP SDK · FastMCP · GitHub MCP · Playwright MCP · agentgateway · Plano        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Skills / memory / context / observability                                    │
│ Agent Skills · claude-mem · mem0 · agentmemory · ReMe · Langfuse · AgentOps  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ Runtime / sandbox / cloud-native substrate                                   │
│ agent-sandbox · AgentCube · OpenShell · Docker Agent · SkyPilot · K8s tools  │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 项目分组

### 个人 Agent、Agent OS 与多 Agent Runtime

| 项目 | Stars | 关注点 |
|------|-------|--------|
| openclaw/openclaw | 376311 | 个人 AI assistant，覆盖多 OS / 多平台，是这个 list 中最强的端侧 Agent 信号。 |
| NousResearch/hermes-agent | 177526 | 个人 Agent 方向，强调“会随用户成长”。 |
| Gitlawb/openclaude | 28239 | OpenClaude 系 Agent runtime，定位是可运行在不同环境、接入不同工具。 |
| NVIDIA/NemoClaw | 20852 | 把 Hermes / OpenClaw 放进 NVIDIA OpenShell 中运行，强调托管推理和安全执行。 |
| agentscope-ai/QwenPaw | 17173 | 个人 AI assistant，支持多个 chat app、skills 和 AgentScope runtime。 |
| HKUDS/OpenHarness | 13448 | Open Agent Harness，内置个人 Agent Ohmo。 |
| nearai/ironclaw | 12393 | Agent OS，关注隐私、安全和可扩展。 |
| NVIDIA/OpenShell | 6629 | 自主 Agent 的安全、私有 runtime。 |
| agentscope-ai/HiClaw | 4719 | 基于 Matrix rooms 的协作式多 Agent OS，强调 human-in-the-loop。 |
| openocta/openocta | 2748 | 面向中文团队的开源企业级智能体。 |
| OpenCoworkAI/open-cowork | 1486 | 桌面端 Agent app，一键安装 Claude Code、MCP tools、Skills，并带 sandbox isolation。 |
| swarmclawai/swarmclaw | 542 | 自托管 Agent runtime / multi-agent framework，带 memory、MCP tools、schedule、delegation。 |
| clawwork-ai/ClawWork | 519 | OpenClaw 客户端，用于连接自有 OpenClaw 并做多会话协作。 |
| agent-substrate/substrate | 437 | Agent runtime 基础系统。 |
| 1va7/openclaw-chat-memory | 4 | OpenClaw 群聊记忆和项目记忆系统。 |

### Coding Agent、Claude Code 周边与工程化工作台

| 项目 | Stars | 关注点 |
|------|-------|--------|
| affaan-m/ECC | 204145 | Agent harness 性能优化系统，覆盖 skills、instincts、memory、security、research-first development，面向 Claude Code / Codex / OpenCode / Cursor。 |
| ultraworkers/claw-code | 193175 | Rust coding agent 方向，围绕 oh-my-codex。 |
| anomalyco/opencode | 168984 | 开源 coding agent。 |
| anthropics/claude-code | 129644 | Anthropic 官方 terminal agentic coding tool。 |
| garrytan/gstack | 106355 | Garry Tan 的 Claude Code setup，23 个 opinionated tools 组成 CEO / Designer / EM / Release / Docs / QA 等角色。 |
| thedotmack/claude-mem | 80289 | 给 Claude Code / OpenClaw / Codex / Gemini / OpenCode 等 Agent 提供跨会话持久上下文。 |
| code-yeongyu/oh-my-openagent | 60746 | 面向复杂代码库的 Agent harness。 |
| earendil-works/pi | 59075 | AI agent toolkit，包含 coding CLI、统一 LLM API、TUI/Web UI、Slack bot 和 vLLM pods。 |
| shanraisshan/claude-code-best-practice | 56103 | Claude Code 最佳实践，从 vibe coding 到 agentic engineering。 |
| Hmbown/CodeWhale | 36729 | Rust terminal coding agent，结合 DeepSeek + MiMo。 |
| multica-ai/multica | 34840 | 托管 coding agents 平台，把 coding agent 作为 teammate 来分配任务、追踪进度、沉淀 skills。 |
| musistudio/claude-code-router | 34648 | Claude Code 模型/路由基础设施，控制模型交互方式同时跟随 Anthropic 更新。 |
| davila7/claude-code-templates | 27733 | Claude Code 配置与监控 CLI。 |
| openai/codex-plugin-cc | 20155 | 在 Claude Code 中调用 Codex 做代码审查或任务委托。 |
| claude-code-best/claude-code | 19362 | Claude Code 可运行、可构建、可调试版本。 |
| tirth8205/code-review-graph | 17921 | 本地优先的代码智能图，用于 MCP / CLI，让 coding tools 只读取相关代码。 |
| NanmiCoder/cc-haha | 12127 | Claude Code 本地可运行版本与 Computer Use 桌面端补齐。 |
| chenhg5/cc-connect | 11410 | 把本地 coding agents 接到飞书、钉钉、Slack、Telegram、Discord、企业微信等 IM。 |
| zilliztech/claude-context | 11687 | Code search MCP，把整个代码库作为 Claude Code / coding agent 的上下文。 |
| junhoyeo/tokscale | 3473 | Coding agents token usage 跟踪 CLI，覆盖 OpenCode、Claude Code、OpenClaw、Codex、Gemini、Cursor 等。 |
| liaohch3/claude-tap | 1272 | 本地 trace viewer / proxy，观察 Claude Code、Codex CLI、Gemini CLI、Cursor CLI、OpenCode 等 API 流量。 |

### Agent 框架、Workflow 平台与应用开发框架

| 项目 | Stars | 关注点 |
|------|-------|--------|
| langgenius/dify | 143589 | 生产级 agentic workflow 平台。 |
| langchain-ai/langchain | 138353 | Agent engineering platform。 |
| TauricResearch/TradingAgents | 82353 | 多 Agent 金融交易框架。 |
| mem0ai/mem0 | 57471 | AI Agent 通用记忆层。 |
| datawhalechina/hello-agents | 55635 | 中文 Agent 原理与实践教程。 |
| langchain-ai/langgraph | 33697 | 构建 resilient agents 的图式运行框架。 |
| agentscope-ai/agentscope | 26036 | 可观察、可理解、可信任的 Agent 构建与运行框架。 |
| dapr/dapr | 25808 | 分布式应用 runtime，事件驱动、workflow 编排和 Agent-native cloud 方向相关。 |
| cloudwego/eino | 11605 | Go 语言 LLM / AI app 开发框架。 |
| tmc/langchaingo | 9356 | Go 版 LangChain。 |
| google/adk-go | 8067 | Go 语言 code-first Agent toolkit，用于构建、评估和部署 Agent。 |
| YaoApp/yao | 7540 | 单二进制构建 AI agents 和 web apps。 |
| OpenCSGs/csghub | 4170 | 类 Hugging Face 的模型、数据集和 Agent 管理平台。 |
| panaversity/learn-agentic-ai | 4202 | Agentic AI 教程，覆盖 OpenAI Agents SDK、Memory、MCP、A2A、Knowledge Graph、Dapr、K8s。 |
| docker/docker-agent | 2979 | Docker Engineering 的 AI Agent Builder and Runtime。 |
| kagent-dev/kagent | 2893 | Cloud Native Agentic AI。 |
| InternLM/lagent | 2255 | 轻量 LLM agent framework。 |
| yomorun/yomo | 1905 | Serverless AI Agent framework，带边缘 AI infra。 |
| viktoriasemaan/multi-agent | 206 | 多 Agent 示例集合。 |
| yeahdongcn/agentman | 19 | AI agents 构建和管理工具。 |

### MCP、SDK、Gateway 与工具协议层

| 项目 | Stars | 关注点 |
|------|-------|--------|
| microsoft/playwright-mcp | 33377 | Playwright MCP server，把浏览器自动化接入 MCP。 |
| github/github-mcp-server | 30377 | GitHub 官方 MCP server。 |
| katanemo/plano | 6563 | AI-native proxy / data plane，带 orchestration、safety、observability 和 smart LLM routing。 |
| PrefectHQ/fastmcp | 25447 | Pythonic MCP servers / clients 构建工具。 |
| modelcontextprotocol/python-sdk | 23208 | MCP 官方 Python SDK。 |
| agentgateway/agentgateway | 2990 | Agentic proxy，面向 AI Agents 和 MCP servers。 |
| rohitg00/kubectl-mcp-server | 902 | Kubernetes MCP server。 |
| anthropics/claude-agent-sdk-python | 7165 | Anthropic Claude Agent SDK Python 版。 |
| anthropics/anthropic-sdk-go | 1078 | Anthropic Go SDK。 |
| severity1/claude-agent-sdk-go | 156 | 非官方 Claude Agent SDK Go 版。 |
| Wei-Shaw/sub2api | 24959 | Claude / OpenAI / Gemini 等订阅统一 API proxy。 |

### Skills、Prompt Pack 与可复用 Agent 能力包

| 项目 | Stars | 关注点 |
|------|-------|--------|
| anthropics/skills | 145713 | Anthropic 官方 Agent Skills 公共仓库。 |
| mattpocock/skills | 115361 | 工程师个人 Claude skills 集合。 |
| addyosmani/agent-skills | 47832 | 面向 AI coding agents 的生产级工程 skills。 |
| ashishpatel26/500-AI-Agents-Projects | 31599 | 500 个 AI Agent use cases / projects 集合。 |
| libukai/awesome-agent-skills | 4576 | Agent Skills 入门、资源和精选技能指南。 |
| RKiding/Awesome-finance-skills | 2399 | 金融分析 Agent Skills。 |
| softaworks/agent-toolkit | 1945 | AI coding agents skills 工具包。 |
| Cocoon-AI/architecture-diagram-generator | 5508 | Claude AI skill：生成系统架构图。 |
| Zhen-Bo/pragmatic-clean-code-reviewer | 187 | 基于 Clean Code / Clean Architecture / Pragmatic Programmer 的 Claude Code review skill。 |
| StepfenShawn/ShitCodify | 132 | 面向遗留代码重构/反向重构的实验性 Agent skill。 |
| sgaunet/claude-plugins | 13 | Claude Code plugins / skills / commands 集合。 |
| googs1025/claude-code-explorer-skill | 8 | 源码解读 Skill，支持 Go/Python/JS/TS。 |
| googs1025/clean-code-reviewer-skills | 3 | 中文代码审查 Claude Code Skill。 |
| googs1025/code-review-skill | 1 | 结构化开源代码审查 Skill。 |

### 记忆、上下文、观测与评测

| 项目 | Stars | 关注点 |
|------|-------|--------|
| langfuse/langfuse | 28395 | LLM engineering observability、metrics、evals、prompt management。 |
| rohitg00/agentmemory | 20786 | 面向 AI coding agents 的持久记忆服务。 |
| agentscope-ai/ReMe | 3035 | Agent memory management kit。 |
| AgentOps-AI/agentops | 5591 | Agent monitoring、LLM cost tracking、benchmarking、evals。 |
| agentscope-ai/OpenJudge | 635 | Agent 评测和质量奖励框架。 |
| oceanbase/powermem | 688 | AI Memory Plugin，强调准确、敏捷、低成本。 |
| peterskoett/self-improving-agent | 631 | Self-improving agent 实验项目。 |
| meta-pytorch/KernelAgent | 436 | 用 deep agents 自动生成和优化 GPU kernel。 |

### Cloud-native / Kubernetes / Infra 边界项目

| 项目 | Stars | 关注点 |
|------|-------|--------|
| skypilot-org/skypilot | 10054 | 跨 Kubernetes / Slurm / 公有云 / on-prem 的 AI workload 运行、管理和扩缩。 |
| kubernetes/kube-state-metrics | 6133 | K8s cluster-level metrics exporter。 |
| kubewall/kubewall | 1901 | 单二进制 Kubernetes dashboard，带 AI integration。 |
| jenkinsci/kubernetes-plugin | 2306 | Jenkins 在 Kubernetes / Docker 上运行 dynamic agents。 |
| armadaproject/armada | 599 | 多集群 batch queue，用于高吞吐 workload。 |
| kubewharf/katalyst-core | 554 | 云资源利用率和成本优化系统，含多个 agents 与 centralized components。 |
| paperclipinc/openclaw-operator | 367 | 部署和管理 OpenClaw Agent instances 的 Kubernetes operator。 |
| Winson-030/dify-kubernetes | 363 | Dify on Kubernetes 部署配置。 |
| cprobe/cprobe | 335 | vmagent + exporters 组合的监控工具。 |
| kubernetes-sigs/agent-sandbox | 2707 | 隔离、有状态、singleton workloads 管理，适合 AI Agent runtimes。 |
| kubernetes-sigs/dra-example-driver | 131 | Kubernetes DRA driver 示例。 |
| castai/k8s-agent | 83 | K8s agent 项目。 |
| kubernetes-sigs/crdify | 42 | 比较 CRD 并识别 breaking changes 的 CLI。 |
| qingwave/kubewizard | 32 | 基于 LangChain 和 K8s tools 的 Kubernetes 自动排障 Agent。 |
| googs1025/kube-agent-helper | 1 | Kubernetes-native AI diagnostic assistant，基于 Claude Agent SDK + SKILL.md。 |

## 观察

- 这个 list 的核心信号是“Agent 工程开始分层”：可直接使用的 Agent / Agent OS 在上层爆发，底层同时出现 Skills、MCP、memory、observability、gateway、sandbox 和 cloud-native runtime。
- Claude Code 已形成一个事实生态：官方工具、router、templates、skills、memory、trace viewer、token tracker、IM bridge、Codex plugin、code graph 等项目都围绕同一个 terminal coding agent 扩展。
- OpenClaw / Hermes / OpenClaude / Claw 系项目非常强，说明“个人 Agent + 多平台入口 + sandbox + memory + messaging”正在变成独立产品形态，而不只是框架 demo。
- Agent 框架路线分成三类：LangChain/LangGraph 这类 Python 图/链框架，Dify/AgentScope 这类平台化 runtime，以及 Eino/ADK/langchaingo/Yao 这类 Go 生态 framework。
- MCP 已经从协议变成基础设施层：官方 SDK、FastMCP、GitHub MCP、Playwright MCP、Kubernetes MCP、agentgateway / Plano 这类 proxy 都在同一个 tool/resource 接入面上竞争。
- Skills 是新的“可迁移能力包”：Anthropic 官方 skills、Addy Osmani / Matt Pocock / finance / architecture / code review skills 都把 Agent 能力从代码插件转成 Markdown + scripts + workflow 的组合。
- 记忆和上下文正在成为独立产品：claude-mem、mem0、agentmemory、ReMe、PowerMem、claude-context、code-review-graph 分别从 session history、universal memory、coding-agent memory、memory kit、RAG/search、code graph 角度切入。
- K8s / cloud-native 项目不是 list 的主体，但很关键：agent-sandbox、AgentCube、OpenShell、Docker Agent、SkyPilot、KAgent、kubewizard 等说明 Agent runtime 开始需要隔离、调度、观测和多云算力。

## 优先深挖候选

| 优先级 | 项目 | 原因 |
|--------|------|------|
| 1 | openclaw/openclaw | Star 数和生态扩展最强，代表个人 Agent / Agent OS 产品化路线。 |
| 2 | anthropics/skills | Skills 作为 Agent 能力包的官方样板，适合和 Codex skills 迁移实践对照。 |
| 3 | affaan-m/ECC | 同时覆盖 Claude Code / Codex / OpenCode / Cursor 的 harness 优化系统，适合研究跨 Agent 工程模式。 |
| 4 | anomalyco/opencode | 开源 coding agent 主线，适合与 Claude Code / Codex / OpenClaw 对比。 |
| 5 | langchain-ai/langgraph | 图式 Agent runtime 标准参照，适合对比 AgentScope / Dify / Dapr workflow。 |
| 6 | PrefectHQ/fastmcp | MCP server/client 开发的主流 Python 工具。 |
| 7 | thedotmack/claude-mem | 跨 Agent 持久上下文方向，与 agentmemory / powermem / mem0 互补。 |
| 8 | agentscope-ai/agentscope-runtime | 生产级 Agent runtime，带安全 tool sandboxing 和 observability，适合连接 AgentScope / HiClaw / QwenPaw。 |
| 9 | katanemo/plano | Agentic proxy / data plane，和 agentgateway 共同代表 Agent 网络与治理层。 |
| 10 | OpenCoworkAI/open-cowork | 把 Claude Code、MCP、Skills、sandbox 和 IM 集成到桌面端，代表 end-user packaging。 |
