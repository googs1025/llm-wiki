---
title: AI Agent Frameworks Star 项目清单整理
tags: [ai-agent, agent-framework, claude-code, mcp, skills, memory]
date: 2026-06-03
sources: [ai-agent-frameworks-stars-list.md]
related: ["[[claude-code]]", "[[mcp]]", "[[claude-mem]]", "[[claude-context]]", "[[agentmemory]]", "[[powermem]]", "[[agent-sandbox]]", "[[agentcube]]", "[[agentgateway]]", "[[ai-agent-plugin-patterns]]", "[[agent-memory]]"]
---

# AI Agent Frameworks Star 项目清单整理

> 原文：`raw/ai-agent-frameworks-stars-list.md` · 来源：[googs1025 的 AI Agent Frameworks Stars list](https://github.com/stars/googs1025/lists/ai-agent-frameworks) · 抓取日期：2026-06-03 · 仓库数：109

## 一句话定位

这个 Star list 不是单纯的“Agent 框架合集”，而是围绕 AI Agent 工程化的完整生态地图：上层是 OpenClaw / Hermes / [[claude-code]] / OpenCode 这类可直接使用的个人或编码 Agent；中层是 LangChain、LangGraph、Dify、AgentScope、Eino、ADK、Dapr 等 Agent / workflow 框架；底层则延伸到 [[mcp]]、Skills、[[agent-memory]]、观测、评测、网关、安全沙箱、[[kubernetes]] runtime 和多云算力。

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

## 速读分组

| 分组 | 代表项目 | 价值 |
|------|----------|------|
| 个人 Agent / Agent OS | OpenClaw, Hermes, OpenClaude, NemoClaw, QwenPaw, OpenHarness, IronClaw | 把 Agent 做成可直接使用的个人助手、协作 OS 或多平台运行时。 |
| Coding Agent / Claude Code 生态 | [[claude-code]], OpenCode, ECC, Claw Code, oh-my-openagent, Pi, Multica, claude-code-router | 围绕 terminal coding agent 形成 router、template、memory、skills、trace、token、IM bridge 和 delegation 工具链。 |
| Agent 框架 / Workflow 平台 | LangChain, LangGraph, Dify, AgentScope, Eino, ADK, Dapr, YoMo | 提供 Agent 编排、状态图、workflow、tool calling、部署和应用开发框架。 |
| MCP / SDK / Gateway | FastMCP, MCP Python SDK, GitHub MCP, Playwright MCP, [[agentgateway]], Plano | 统一 tool/resource 接入、代理、治理和协议 SDK。 |
| Skills / Prompt Pack | Anthropic Skills, agent-skills, Matt Pocock skills, awesome-agent-skills, finance/code review skills | 把 Agent 能力从硬编码插件迁移成 Markdown + scripts + workflow 的可复用能力包。 |
| 记忆 / 上下文 / 观测 / 评测 | [[claude-mem]], mem0, [[agentmemory]], ReMe, [[powermem]], [[claude-context]], Langfuse, AgentOps | 为 Agent 增加长期记忆、代码语义上下文、trace、cost、eval 和质量反馈。 |
| Cloud-native runtime | [[agent-sandbox]], [[agentcube]], OpenShell, Docker Agent, SkyPilot, KAgent, kubewizard | 解决 Agent 的隔离、调度、多云算力、K8s 排障和 runtime 管理。 |

## 项目清单

### 个人 Agent、Agent OS 与多 Agent Runtime

- **openclaw/openclaw**：个人 AI assistant，多 OS / 多平台，是这个 list 中最强的端侧 Agent 信号。
- **NousResearch/hermes-agent**：个人 Agent 方向，强调“会随用户成长”。
- **Gitlawb/openclaude**、**NVIDIA/NemoClaw**、**NVIDIA/OpenShell**：OpenClaw / Hermes / OpenClaude 生态的安全 runtime、托管推理和跨环境运行路线。
- **agentscope-ai/QwenPaw**、**HKUDS/OpenHarness**、**nearai/ironclaw**、**agentscope-ai/HiClaw**：个人 assistant、Agent harness、Agent OS、多人协作 Agent runtime。
- **OpenCoworkAI/open-cowork**：桌面端把 [[claude-code]]、[[mcp]] tools、Skills、sandbox 和 IM integration 打包成 end-user app。
- **swarmclawai/swarmclaw**、**clawwork-ai/ClawWork**、**agent-substrate/substrate**：自托管 multi-agent runtime、OpenClaw client 和 Agent substrate。

### Coding Agent、Claude Code 周边与工程化工作台

- **anthropics/claude-code**：Anthropic 官方 terminal agentic coding tool。
- **anomalyco/opencode**、**ultraworkers/claw-code**、**Hmbown/CodeWhale**、**code-yeongyu/oh-my-openagent**：开源 coding agent / agent harness / terminal coding agent 方向。
- **affaan-m/ECC**：跨 [[claude-code]]、Codex、OpenCode、Cursor 的 agent harness 优化系统，覆盖 skills、memory、security、research-first development。
- **garrytan/gstack**、**shanraisshan/claude-code-best-practice**、**davila7/claude-code-templates**：Claude Code 配置、工作流和最佳实践集合。
- **multica-ai/multica**、**earendil-works/pi**、**musistudio/claude-code-router**、**openai/codex-plugin-cc**：coding agents 的托管平台、toolkit、模型路由和任务委托。
- **thedotmack/claude-mem**、**zilliztech/claude-context**、**tirth8205/code-review-graph**：coding agent 长期记忆、代码语义搜索和本地代码图。
- **chenhg5/cc-connect**、**liaohch3/claude-tap**、**junhoyeo/tokscale**：IM bridge、API trace viewer 和 token usage tracker。

### Agent 框架、Workflow 平台与应用开发框架

- **langchain-ai/langchain**、**langchain-ai/langgraph**：Agent engineering platform 和图式 resilient agents 框架。
- **langgenius/dify**：生产级 agentic workflow 平台。
- **agentscope-ai/agentscope**、**agentscope-ai/agentscope-runtime**：可观察、可理解、可信任的 Agent 构建框架与生产 runtime。
- **cloudwego/eino**、**google/adk-go**、**tmc/langchaingo**、**YaoApp/yao**：Go 生态 Agent / LLM app framework。
- **dapr/dapr**、**yomorun/yomo**：事件驱动、workflow、edge / serverless 方向的 Agent-native cloud runtime。
- **TauricResearch/TradingAgents**、**datawhalechina/hello-agents**、**panaversity/learn-agentic-ai**：垂直多 Agent 框架与教程型资源。

### MCP、SDK、Gateway 与工具协议层

- **PrefectHQ/fastmcp**、**modelcontextprotocol/python-sdk**：Python MCP servers / clients 开发基础。
- **github/github-mcp-server**、**microsoft/playwright-mcp**、**rohitg00/kubectl-mcp-server**：GitHub、浏览器自动化和 Kubernetes 的 MCP server。
- **[[agentgateway]]**、**katanemo/plano**：Agent / MCP / LLM 流量的 proxy、data plane、observability、安全和路由治理。
- **anthropics/claude-agent-sdk-python**、**anthropics/anthropic-sdk-go**、**severity1/claude-agent-sdk-go**：Anthropic / Claude Agent SDK 生态。

### Skills、Prompt Pack 与可复用 Agent 能力包

- **anthropics/skills**：Anthropic 官方 Agent Skills 公共仓库，是 Skills 机制的主参考。
- **addyosmani/agent-skills**、**mattpocock/skills**、**libukai/awesome-agent-skills**、**softaworks/agent-toolkit**：面向 AI coding agents 的工程 skills、个人 skills、指南和工具包。
- **Cocoon-AI/architecture-diagram-generator**、**RKiding/Awesome-finance-skills**、**Zhen-Bo/pragmatic-clean-code-reviewer**：架构图、金融分析、代码审查等垂直 skills。
- **googs1025/claude-code-explorer-skill**、**googs1025/clean-code-reviewer-skills**、**googs1025/code-review-skill**：已迁移/可迁移到 Codex 的源码解读与代码审查 skills。

### 记忆、上下文、观测与评测

- **[[claude-mem]]**、**mem0ai/mem0**、**[[agentmemory]]**、**agentscope-ai/ReMe**、**[[powermem]]**：Agent 记忆的多条路线，分别偏 coding-agent session memory、通用 memory layer、持久 memory service、memory kit 和持久化记忆中间件。
- **[[claude-context]]**、**tirth8205/code-review-graph**：代码语义检索和代码图，解决大代码库上下文选择。
- **langfuse/langfuse**、**AgentOps-AI/agentops**、**agentscope-ai/OpenJudge**：Agent / LLM observability、cost tracking、benchmark、eval 和质量奖励。

### Cloud-native / Kubernetes / Infra 边界项目

- **[[agent-sandbox]]**、**[[agentcube]]**、**paperclipinc/openclaw-operator**：Kubernetes 上的 Agent runtime 隔离、有状态会话编排和 OpenClaw operator。
- **skypilot-org/skypilot**：跨 K8s / Slurm / 公有云 / on-prem 的 AI workload 控制平面。
- **kagent-dev/kagent**、**qingwave/kubewizard**、**googs1025/kube-agent-helper**：Kubernetes-native Agentic AI、自动排障 Agent 和 K8s diagnostic assistant。
- **docker/docker-agent**、**armadaproject/armada**、**kubewall/kubewall**、**kubernetes/kube-state-metrics**：Agent builder/runtime、batch queue、K8s dashboard 和 observability substrate。

## 观察

- 这个 list 的核心信号是“Agent 工程开始分层”：可直接使用的 Agent / Agent OS 在上层爆发，底层同时出现 Skills、[[mcp]]、memory、observability、gateway、sandbox 和 cloud-native runtime。
- [[claude-code]] 已形成一个事实生态：官方工具、router、templates、skills、memory、trace viewer、token tracker、IM bridge、Codex plugin、code graph 等项目都围绕同一个 terminal coding agent 扩展。
- OpenClaw / Hermes / OpenClaude / Claw 系项目非常强，说明“个人 Agent + 多平台入口 + sandbox + memory + messaging”正在变成独立产品形态，而不只是框架 demo。
- Agent 框架路线分成三类：LangChain/LangGraph 这类 Python 图/链框架，Dify/AgentScope 这类平台化 runtime，以及 Eino/ADK/langchaingo/Yao 这类 Go 生态 framework。
- [[mcp]] 已经从协议变成基础设施层：官方 SDK、FastMCP、GitHub MCP、Playwright MCP、Kubernetes MCP、[[agentgateway]] / Plano 这类 proxy 都在同一个 tool/resource 接入面上竞争。
- Skills 是新的“可迁移能力包”：Anthropic 官方 skills、Addy Osmani / Matt Pocock / finance / architecture / code review skills 都把 Agent 能力从代码插件转成 Markdown + scripts + workflow 的组合。
- 记忆和上下文正在成为独立产品：[[claude-mem]]、mem0、[[agentmemory]]、ReMe、[[powermem]]、[[claude-context]]、code-review-graph 分别从 session history、universal memory、coding-agent memory、memory kit、RAG/search、code graph 角度切入。
- K8s / cloud-native 项目不是 list 的主体，但很关键：[[agent-sandbox]]、[[agentcube]]、OpenShell、Docker Agent、SkyPilot、KAgent、kubewizard 等说明 Agent runtime 开始需要隔离、调度、观测和多云算力。

## 优先深挖候选

| 优先级 | 项目 | 原因 |
|--------|------|------|
| 1 | openclaw/openclaw | Star 数和生态扩展最强，代表个人 Agent / Agent OS 产品化路线。 |
| 2 | anthropics/skills | Skills 作为 Agent 能力包的官方样板，适合和 Codex skills 迁移实践对照。 |
| 3 | affaan-m/ECC | 同时覆盖 Claude Code / Codex / OpenCode / Cursor 的 harness 优化系统，适合研究跨 Agent 工程模式。 |
| 4 | anomalyco/opencode | 开源 coding agent 主线，适合与 Claude Code / Codex / OpenClaw 对比。 |
| 5 | langchain-ai/langgraph | 图式 Agent runtime 标准参照，适合对比 AgentScope / Dify / Dapr workflow。 |
| 6 | PrefectHQ/fastmcp | MCP server/client 开发的主流 Python 工具。 |
| 7 | [[claude-mem]] | 跨 Agent 持久上下文方向，与 [[agentmemory]] / [[powermem]] / mem0 互补。 |
| 8 | agentscope-ai/agentscope-runtime | 生产级 Agent runtime，带安全 tool sandboxing 和 observability，适合连接 AgentScope / HiClaw / QwenPaw。 |
| 9 | katanemo/plano | Agentic proxy / data plane，和 [[agentgateway]] 共同代表 Agent 网络与治理层。 |
| 10 | OpenCoworkAI/open-cowork | 把 [[claude-code]]、[[mcp]]、Skills、sandbox 和 IM 集成到桌面端，代表 end-user packaging。 |

## 相关页面

- [[claude-code]]
- [[mcp]]
- [[claude-mem]]
- [[claude-context]]
- [[agentmemory]]
- [[powermem]]
- [[agent-memory]]
- [[ai-agent-plugin-patterns]]
- [[agent-sandbox]]
- [[agentcube]]
- [[agentgateway]]
