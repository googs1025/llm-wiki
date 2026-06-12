---
title: GitHub Stars 下一批摄入候选清单
tags: [github-stars, project-map, backlog, selection]
date: 2026-06-12
sources: [github-stars-googs1025-2026-06-12, src-ai-agent-frameworks-stars, src-k8s-gpu-device-plugins-stars, src-k8s-core-controllers-stars]
related: [[ai-agent-frameworks-map]], [[agent-runtime-sandbox-selection-map]], [[agent-memory-selection-matrix]], [[llm-serving-engine-selection-map]], [[mcp-gateway-tooling-map]], [[code-semantic-search-rag-map]]
---

# GitHub Stars 下一批摄入候选清单

本页整理 2026-06-12 通过 GitHub API 复核 `googs1025` starred repositories 后，值得进入 `llm-wiki` 的 P0-P2 候选项目。这里是 **摄入 backlog**，不是完整架构结论；真正写入 `wiki/sources/` 前仍要逐仓库重新看 README、docs、目录结构、近期 commit/release，并区分 GitHub 当前状态与既有 wiki 旧结论。

## P0：优先摄入

| 项目 | 应进入的 wiki 主线 | 为什么优先 |
|---|---|---|
| `agent-substrate/substrate` | Agent Runtime / Sandbox / Substrate | Kubernetes 上的 agent-like workload substrate：actor/worker multiplexing、suspend/resume、snapshot、traffic routing、gVisor。它补上 [[agent-sandbox]] 和 [[agentcube]] 之间“高密度 stateful agent substrate”层。 |
| `agentscope-ai/agentscope-runtime` | Agent Runtime / Agent-as-a-Service | 和已摄入的 AgentScope framework 互补，重点是生产 runtime、安全工具沙箱、observability、服务化部署。 |
| `mem0ai/mem0` | Agent Memory | 通用 memory layer 代表，适合和 [[claude-mem]]、[[agentmemory]]、[[powermem]]、[[memsearch]]、[[tencentdb-agent-memory]] 横向比较。 |
| `agentscope-ai/ReMe` | Agent Memory | AgentScope 生态 memory management kit，可补“framework 内建 memory kit”维度。 |
| `openai/codex` | Coding Agent / Terminal Agent | Codex CLI 是 Claude Code 之外的关键 terminal coding agent，应进入 [[coding-agent-selection-map]]。 |
| `earendil-works/pi` | Coding Agent / Agent Toolkit | 统一 LLM API、agent loop、TUI、coding agent CLI，适合和 Codex/OpenCode/OpenClaude 对比。 |
| `can1357/oh-my-pi` | Coding Agent / Tool Harness | Hash-anchored edits、LSP、browser、subagents 等工具 harness 方向，适合补 coding agent 执行面。 |
| `multica-ai/multica` | Personal Agent / Agent Teammate | 把 coding agents 产品化成 managed teammate：任务分配、进度、skills compound。 |
| `OpenCoworkAI/open-cowork` | Personal Agent / Desktop Agent OS | 桌面端 agent app，整合 Claude Code、MCP、Skills、sandbox 和 IM。 |
| `vllm-project/aibrix` | LLM Serving / Inference Infrastructure | vLLM 生态的 GenAI inference 基础设施组件，补 Dynamo/SkyPilot 之外的 serving control plane。 |
| `llm-d/llm-d` | LLM Serving on Kubernetes | Kubernetes 上的现代推理栈总入口，适合与 [[dynamo]]、SkyPilot、vLLM production stack 对比。 |
| `llm-d/llm-d-router` | LLM Serving Router | inference request intelligent entry point，适合补 routing/semantic routing 专题。 |
| `llm-d/llm-d-kv-cache` | KV Cache / Serving | 分布式 KV cache scheduling/offloading，直接关联 [[kv-cache-offload]] 和 [[disaggregated-serving]]。 |

> `oceanbase/powermem` 已经摄入为 [[powermem]] / [[src-powermem-architecture]]，后续动作不是新增，而是按 GitHub 当前状态做复查更新。

## P1：专题补强

### Kubernetes AI Assistant / AI Ops

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `kagent-dev/kagent` | 架构源页 + K8s AI assistant 对比 | Cloud Native Agentic AI，和 [[ai-ops]]、[[kubernetes]] 主线相连。 |
| `GoogleCloudPlatform/kubectl-ai` | 架构源页或对比小节 | kubectl 入口的 Kubernetes assistant。 |
| `weibaohui/k8m` | 对比小节 | Mini Kubernetes AI Dashboard，含 MCP/操作权限/多集群。 |
| `kubewall/kubewall` | 对比小节 | 单二进制 K8s dashboard + AI integration。 |

### AI Gateway / Inference Routing

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `kubernetes-sigs/gateway-api-inference-extension` | 架构源页 | Gateway API 进入 inference routing 的关键扩展。 |
| `envoyproxy/ai-gateway` | 架构源页 | Envoy Gateway 上的 GenAI access control/routing。 |
| `kgateway-dev/kgateway` | 对比小节 | Cloud-native API Gateway + AI Gateway。 |
| `higress-group/higress` | 架构源页或实体页 | HiClaw 凭据托管与 AI 网关背景依赖。 |
| `vllm-project/semantic-router` | 对比小节 | Mixture-of-Models 智能路由。 |
| `lm-sys/RouteLLM` | 对比小节 | 成本/质量路由基线。 |
| `katanemo/plano` | 已在 [[mcp-gateway-tooling-map]] 提及，建议补源页 | Agentic proxy/data plane，和 [[agentgateway]] 对比价值高。 |

### Model Serving / GPU Cluster

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `gpustack/gpustack` | 架构源页 | GPU cluster manager，编排 vLLM/SGLang。 |
| `ome-projects/ome` | 架构源页 | Open Model Engine，K8s operator for LLM serving/GPU scheduling/model lifecycle。 |
| `kserve/kserve` | 对比源页 | 标准化分布式推理平台，传统 model serving 与 GenAI serving 交界。 |
| `kubeai-project/kubeai` | 对比源页 | AI inference operator，覆盖 LLM/VLM/embedding/speech-to-text。 |

### Code Graph / Repo Wiki / Code Intelligence

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `tirth8205/code-review-graph` | 架构源页 | 本地优先 code intelligence graph for MCP/CLI，适合扩展 [[code-semantic-search-rag-map]]。 |
| `abhigyanpatwari/GitNexus` | 对比小节 | 浏览器端 repo knowledge graph + Graph RAG Agent。 |
| `AsyncFuncAI/deepwiki-open` | 架构源页 | Open Source DeepWiki，和本项目 wiki 生成工作流也有镜像价值。 |

## P2：先进入待建池

### Claude Code / Codex 生态插件

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `openai/codex-plugin-cc` | 插件生态小节 | Claude Code 调用 Codex 的 delegation plugin。 |
| `liaohch3/claude-tap` | 观测小节 | 拦截/检查 coding agent API traffic，本地 trace viewer。 |
| `chenhg5/cc-connect` | IM bridge 小节 | 把 Claude Code/Codex/Gemini CLI 等接入 Feishu/Lark/Slack/Telegram 等。 |
| `junhoyeo/tokscale` | 成本观测小节 | OpenCode/Claude Code/OpenClaw/Pi/Codex/Gemini 等 token usage tracker。 |

### Kubernetes GPU / DRA / Device Plugin

| 项目 | 建议产物 | 关注点 |
|---|---|---|
| `Project-HAMi/HAMi` | GPU sharing 源页 | Kubernetes heterogeneous GPU sharing。 |
| `kubernetes-sigs/dra-driver-nvidia-gpu` | DRA 源页 | NVIDIA GPU DRA driver，适合补 DRA/CDI 主线。 |
| `NVIDIA/gpu-operator` | GPU 基座源页 | GPU driver/runtime/operator 管理基座。 |
| `NVIDIA/k8s-device-plugin` | GPU 基座源页 | Kubernetes NVIDIA device plugin 核心项目。 |

## 推荐执行顺序

1. 先 ingest `agent-substrate/substrate`：它直接补齐现有 Runtime/Sandbox 分层缺口，并且与 [[agent-sandbox]]、[[agentcube]]、OpenShell/NemoClaw 的关系最需要澄清。
2. 再 ingest `agentscope-ai/agentscope-runtime`：把 AgentScope 从 framework 延伸到 production runtime。
3. 然后做 `mem0ai/mem0` + `agentscope-ai/ReMe`：补通用 memory layer 与 framework memory kit。
4. 接着做 `openai/codex` + `earendil-works/pi` + `can1357/oh-my-pi`：补 Coding Agent 执行面。
5. 最后按专题批量做 LLM Serving、AI Gateway、K8s AI Ops、Code Graph 和 GPU/DRA。

## 摄入时的检查清单

- GitHub 当前状态：default branch、最近 push、license、language、stars、release/tag、README 与 docs。
- 架构边界：这是 SDK、runtime、gateway、operator、plugin、memory layer、serving engine 还是 control plane。
- 数据/控制流：入口、状态源、调度/路由路径、持久化、观测和失败恢复。
- 与已有 wiki 的关系：新增实体页、补 source 页、扩写对比页，还是只进入待建页面。
- 成熟度风险：alpha/实验性、API 不稳定、单人项目、fork/镜像、是否有生产案例。
