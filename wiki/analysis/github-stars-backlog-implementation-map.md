---
title: GitHub Stars P0-P2 实现地图
tags: [github-stars, project-map, selection, ai-infra]
date: 2026-06-12
sources: [src-github-stars-backlog-current-state, github-stars-ingest-candidates]
related: [[agent-runtime-sandbox-selection-map]], [[agent-memory-selection-matrix]], [[coding-agent-selection-map]], [[llm-serving-engine-selection-map]], [[mcp-gateway-tooling-map]], [[code-semantic-search-rag-map]], [[ai-ops]], [[kv-cache-offload]]
---

# GitHub Stars P0-P2 实现地图

这页把 [[github-stars-ingest-candidates]] 从“摄入候选清单”落实为正式分析地图：P0-P2 不再只是待办，而是被放进当前 wiki 的选型结构里，说明每个项目应该如何理解、和已有项目差在哪里、后续如果单独 ingest 应该看什么。

GitHub 当前状态见 [[src-github-stars-backlog-current-state]]。

## 总体分层

```
Coding agent / personal agent product
        ↓
agent runtime / sandbox / substrate
        ↓
memory / skills / observability / IM bridge
        ↓
tool gateway / AI gateway / model router
        ↓
LLM serving control plane / inference operator
        ↓
GPU operator / device plugin / DRA / GPU sharing
        ↓
code graph / repo wiki / code intelligence
```

这批 backlog 项目的核心价值不是“再多几个开源项目”，而是把已有 wiki 的几条主线补完整：Agent 从 CLI 产品向 managed teammate 和 runtime substrate 扩展；LLM serving 从 vLLM/SGLang/Dynamo 向 K8s control plane、router 和 KV cache library 扩展；Code RAG 从搜索插件向代码图和 repo wiki 扩展；GPU 栈从 star list 进入 serving 选型的基础设施层。

## P0：正式进入选型主线

| 主线 | 纳入项目 | 和已有 wiki 的差异 |
|---|---|---|
| Agent Runtime / Substrate | `agent-substrate/substrate`, `agentscope-ai/agentscope-runtime` | 现有 [[agent-runtime-sandbox-selection-map]] 主要覆盖 sandbox primitive、OpenShell runtime、AgentScope framework、agentgateway。Substrate 补“高密度 stateful agent workload substrate”，AgentScope Runtime 补“framework app 到生产 runtime / Agent-as-a-Service”的中间层。 |
| Agent Memory | `mem0ai/mem0`, `agentscope-ai/ReMe` | 现有 [[agent-memory-selection-matrix]] 偏 Claude/Coding agent 插件、Markdown truth、OceanBase memory。mem0 是通用应用 memory layer，ReMe 是 AgentScope 生态内建 memory kit。 |
| Coding Agent 执行面 | `openai/codex`, `earendil-works/pi`, `can1357/oh-my-pi` | 现有 [[coding-agent-selection-map]] 以 Claude Code/OpenCode/NemoClaw/nanobot 为骨架。Codex 是官方 Rust terminal agent；Pi 是 toolkit + TUI + coding CLI；oh-my-pi 代表 hash-anchored edits、LSP、browser、subagents 的 tool harness。 |
| Managed / Desktop Agent | `multica-ai/multica`, `OpenCoworkAI/open-cowork` | 它们不是底层 framework，而是把 coding agent 包成 teammate 或 desktop app，和 [[nanobot]] 的个人多渠道内核形成产品层对照。 |
| LLM Serving on K8s | `vllm-project/aibrix`, `llm-d/llm-d`, `llm-d/llm-d-router`, `llm-d/llm-d-kv-cache` | 现有 [[llm-serving-engine-selection-map]] 主要讲 vLLM/SGLang/Dynamo/SkyPilot。AIBrix 和 llm-d 把重点推到 K8s inference control plane、Gateway API、router 和分布式 KV cache。 |

## Runtime / Sandbox 补层

| 项目 | 应放的位置 | 关键架构问题 |
|---|---|---|
| `agent-substrate/substrate` | [[agent-runtime-sandbox-selection-map]] 的 substrate 层 | actor/worker multiplexing、suspend/resume、snapshot、traffic routing、gVisor 如何组合成高密度 agent workload 基座。 |
| `agentscope-ai/agentscope-runtime` | Agent framework 到 runtime 的服务化层 | secure tool sandboxing、Agent-as-a-Service API、observability、K8s/serverless 部署如何承接 AgentScope app。 |
| `multica-ai/multica` | managed teammate 产品层 | coding agent task assignment、progress tracking、compound skills 如何产品化，不是 sandbox primitive。 |
| `OpenCoworkAI/open-cowork` | desktop Agent OS / agent host | Claude Code、MCP tools、skills、sandbox、IM 集成在桌面端如何形成用户入口。 |

选型判断：如果问题是“Agent 进程怎么安全/高密度运行”，看 `agent-substrate/substrate` 和 [[src-openshell-architecture|OpenShell]]；如果问题是“Agent app 怎么服务化”，看 `agentscope-runtime`；如果问题是“用户如何把 agent 当同事用”，看 `multica` / `open-cowork`。

## Memory 补层

| 项目 | 对比对象 | 关键差异 |
|---|---|---|
| `mem0ai/mem0` | [[powermem]], [[agentmemory]], [[memsearch]] | 更像通用应用 memory layer，stars 和生态信号强，适合补“产品/应用内用户记忆”的主流开源基线。 |
| `agentscope-ai/ReMe` | [[src-agentscope-architecture|AgentScope]], [[agent-memory-selection-matrix]] | framework 内部 memory kit，重点不是通用服务，而是和 AgentScope agent/tool/workflow 生态耦合。 |

这两个项目应更新 [[agent-memory-selection-matrix]] 的分类：`mem0` 进入“通用 memory layer”，`ReMe` 进入“framework memory kit”。它们和 [[memsearch]] 的 Markdown truth 路线不同，也和 [[tencentdb-agent-memory]] 的 L0-L3 语义金字塔不同。

## Coding Agent 执行面与生态配套

| 层 | 项目 | 作用 |
|---|---|---|
| Terminal coding agent | `openai/codex` | 官方轻量 terminal coding agent，Rust 实现，和 [[claude-code]]、OpenCode 同层。 |
| Agent toolkit / TUI | `earendil-works/pi` | unified LLM API + agent loop + TUI + coding agent CLI，适合看 agent runtime/tool loop 抽象。 |
| Tool harness | `can1357/oh-my-pi` | hash-anchored edits、LSP、browser、subagents，适合拆“可靠改代码”的执行面。 |
| Delegation plugin | `openai/codex-plugin-cc` | Claude Code 调用 Codex，属于 cross-agent delegation。 |
| Trace viewer | `liaohch3/claude-tap` | 拦截并查看 coding agent API traffic，属于可观测层。 |
| IM bridge | `chenhg5/cc-connect` | 把本地 coding agent 接入 Feishu/Lark/Slack/Telegram 等 IM，属于远程入口层。 |
| Token cost | `junhoyeo/tokscale` | 多 agent token usage tracker，属于成本/用量观测层。 |

选型时不要把这些混成“coding agent”。Codex / Pi / oh-my-pi 是执行 loop；codex-plugin-cc、claude-tap、cc-connect、tokscale 是围绕执行 loop 的 delegation、trace、IM 和 cost 层。

## LLM Serving / AI Gateway / GPU 基座

| 子域 | 项目 | 放入地图后的含义 |
|---|---|---|
| Serving control plane | `vllm-project/aibrix`, `llm-d/llm-d` | 补 [[llm-serving-engine-selection-map]] 中“单引擎之外”的 K8s GenAI infrastructure。 |
| Inference router | `llm-d/llm-d-router`, `vllm-project/semantic-router`, `lm-sys/RouteLLM` | 前者偏 K8s/Gateway API 请求入口，semantic-router 偏 mixture-of-models 系统路由，RouteLLM 偏成本/质量路由算法基线。 |
| KV cache library | `llm-d/llm-d-kv-cache` | 让 [[kv-cache-offload]] 从 Dynamo 结论扩展到 llm-d 生态的分布式 KV cache scheduling/offloading。 |
| Gateway API / AI Gateway | `kubernetes-sigs/gateway-api-inference-extension`, `envoyproxy/ai-gateway`, `kgateway-dev/kgateway`, `higress-group/higress`, `katanemo/plano` | 这些项目把 [[mcp-gateway-tooling-map]] 和 [[agentgateway]] 的 gateway 讨论扩展到 GenAI access control、model routing 和 Gateway API 标准化。 |
| Model serving operator | `gpustack/gpustack`, `ome-projects/ome`, `kserve/kserve`, `kubeai-project/kubeai` | 它们不是 vLLM/SGLang 替代品，而是在 K8s 上编排模型、GPU、autoscaling、OpenAI-compatible endpoint。 |
| GPU / DRA / device plugin | `Project-HAMi/HAMi`, `kubernetes-sigs/dra-driver-nvidia-gpu`, `NVIDIA/gpu-operator`, `NVIDIA/k8s-device-plugin` | 把 [[src-k8s-gpu-device-plugins-stars]] 里的基础设施项目升格为 serving 选型必须看的资源层。 |

关键取舍：vLLM/SGLang 是 engine；Dynamo/AIBrix/llm-d 是 serving system；Gateway API Inference Extension/Envoy AI Gateway/kgateway/Higress/Plano 是入口和治理；GPU Operator/device plugin/DRA/HAMi 是设备与资源分配层。

## Kubernetes AI Assistant / AI Ops

| 项目 | 用户入口 | 适合回答的问题 |
|---|---|---|
| `kagent-dev/kagent` | Cloud-native agentic AI / MCP | 如何把 K8s/DevOps 工作流包装成 agentic 操作系统。 |
| `GoogleCloudPlatform/kubectl-ai` | kubectl CLI | 如何在命令行里做 K8s assistant。 |
| `weibaohui/k8m` | Mini K8s AI dashboard | 如何把多集群、权限、MCP、异常检测合进轻量 dashboard。 |
| `kubewall/kubewall` | Single-binary dashboard | 如何把 AI integration 放进 K8s dashboard 管理体验。 |

这四个项目应该进入 [[ai-ops]] / K8s assistant 专题，而不是和通用 Agent framework 混放。它们的关键差异是入口：CLI、dashboard、agentic workflow、MCP/权限模型。

## Code Graph / Repo Wiki / Code Intelligence

| 项目 | 路线 | 和 [[code-semantic-search-rag-map]] 的关系 |
|---|---|---|
| `tirth8205/code-review-graph` | local-first code intelligence graph for MCP/CLI | 从 vector search 扩展到持久代码图，目标是让 coding tools 只读相关上下文。 |
| `abhigyanpatwari/GitNexus` | browser-side knowledge graph + Graph RAG | 零服务器、浏览器端 repo 图谱，适合对照本地优先/隐私/交互式探索。 |
| `AsyncFuncAI/deepwiki-open` | AI-powered repo wiki generator | 和 llm-wiki 自身工作流有镜像价值：自动总结 repo，生成结构化 wiki。 |

这条线说明 Code RAG 不只是 search MCP。它正在分成三类：代码搜索、代码图谱、自动 repo wiki。后续单独 ingest 时应重点看 incremental graph、truth source、line-level evidence、repo scale 和生成内容的可审计性。

## 后续单独 ingest 优先级

如果继续从这批项目中做完整源码架构页，优先级应调整为：

1. `agent-substrate/substrate`：补 runtime substrate 缺口。
2. `openai/codex`：补官方 terminal coding agent 执行 loop。
3. `mem0ai/mem0`：补通用 memory layer 主流基线。
4. `vllm-project/aibrix` 或 `llm-d/llm-d`：补 K8s GenAI inference control plane。
5. `kubernetes-sigs/gateway-api-inference-extension`：补 inference routing 标准化入口。
6. `tirth8205/code-review-graph` 或 `AsyncFuncAI/deepwiki-open`：补 Code Graph / Repo Wiki 实现路线。

其余项目已经在本页进入正式对比结构；是否单独 ingest 取决于你下一步要深挖哪条主线。
