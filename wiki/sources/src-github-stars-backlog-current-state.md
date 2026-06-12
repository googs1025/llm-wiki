---
title: GitHub Stars P0-P2 当前状态核验
tags: [github-stars, project-map, selection, ai-infra]
date: 2026-06-12
sources: [github-stars-p0-p2-raw-snapshots-2026-06-12]
related: [[github-stars-backlog-implementation-map]], [[github-stars-ingest-candidates]], [[agent-runtime-sandbox-selection-map]], [[agent-memory-selection-matrix]], [[coding-agent-selection-map]], [[llm-serving-engine-selection-map]], [[mcp-gateway-tooling-map]], [[code-semantic-search-rag-map]]
---

# GitHub Stars P0-P2 当前状态核验

本页是 [[github-stars-ingest-candidates]] 的 GitHub 当前状态复核底稿。2026-06-12 通过 GitHub API 重新读取 P0-P2 项目的描述、stars、最近 push、主语言、license 和 topics，并把它们作为 [[github-stars-backlog-implementation-map]] 的事实输入。每个项目的原始核验结果已逐一保存到 `raw/github-stars-p*-*.md`。

它不是新的 backlog。它的作用是把“候选项目”变成可比较的当前项目剖面，供后续按专题理解架构边界和选型差异。

## Raw 快照文件

### P0

- `raw/github-stars-p0-agent-substrate-substrate.md`
- `raw/github-stars-p0-agentscope-runtime.md`
- `raw/github-stars-p0-mem0.md`
- `raw/github-stars-p0-reme.md`
- `raw/github-stars-p0-openai-codex.md`
- `raw/github-stars-p0-pi.md`
- `raw/github-stars-p0-oh-my-pi.md`
- `raw/github-stars-p0-multica.md`
- `raw/github-stars-p0-open-cowork.md`
- `raw/github-stars-p0-aibrix.md`
- `raw/github-stars-p0-llm-d.md`
- `raw/github-stars-p0-llm-d-router.md`
- `raw/github-stars-p0-llm-d-kv-cache.md`

### P1

- `raw/github-stars-p1-kagent.md`
- `raw/github-stars-p1-kubectl-ai.md`
- `raw/github-stars-p1-k8m.md`
- `raw/github-stars-p1-kubewall.md`
- `raw/github-stars-p1-gateway-api-inference-extension.md`
- `raw/github-stars-p1-envoy-ai-gateway.md`
- `raw/github-stars-p1-kgateway.md`
- `raw/github-stars-p1-higress.md`
- `raw/github-stars-p1-semantic-router.md`
- `raw/github-stars-p1-routellm.md`
- `raw/github-stars-p1-plano.md`
- `raw/github-stars-p1-gpustack.md`
- `raw/github-stars-p1-ome.md`
- `raw/github-stars-p1-kserve.md`
- `raw/github-stars-p1-kubeai.md`
- `raw/github-stars-p1-code-review-graph.md`
- `raw/github-stars-p1-gitnexus.md`
- `raw/github-stars-p1-deepwiki-open.md`

### P2

- `raw/github-stars-p2-codex-plugin-cc.md`
- `raw/github-stars-p2-claude-tap.md`
- `raw/github-stars-p2-cc-connect.md`
- `raw/github-stars-p2-tokscale.md`
- `raw/github-stars-p2-hami.md`
- `raw/github-stars-p2-dra-driver-nvidia-gpu.md`
- `raw/github-stars-p2-gpu-operator.md`
- `raw/github-stars-p2-k8s-device-plugin.md`

## P0 项目

| 项目 | stars | 最近 push | 语言 | license | 当前定位 |
|---|---:|---|---|---|---|
| `agent-substrate/substrate` | 517 | 2026-06-11 | Go | Apache-2.0 | Agent Substrate core system，适合补 [[agent-runtime-sandbox-selection-map]] 的高密度 stateful agent substrate 层。 |
| `agentscope-ai/agentscope-runtime` | 816 | 2026-06-04 | Python | Apache-2.0 | Production-ready agent runtime：secure tool sandboxing、Agent-as-a-Service API、K8s/serverless、observability。 |
| `mem0ai/mem0` | 58393 | 2026-06-12 | Python | Apache-2.0 | Universal memory layer for AI agents，和 [[agent-memory-selection-matrix]] 中的应用级 memory layer 对比价值最高。 |
| `agentscope-ai/ReMe` | 3074 | 2026-06-10 | Python | Apache-2.0 | AgentScope 生态 Memory Management Kit，代表 framework 内建 memory kit 路线。 |
| `openai/codex` | 90546 | 2026-06-12 | Rust | Apache-2.0 | Lightweight terminal coding agent，是 [[coding-agent-selection-map]] 必须纳入的官方 coding loop 产品。 |
| `earendil-works/pi` | 61856 | 2026-06-11 | TypeScript | MIT | AI agent toolkit：unified LLM API、agent loop、TUI、coding agent CLI。 |
| `can1357/oh-my-pi` | 11964 | 2026-06-12 | TypeScript | MIT | Terminal AI coding agent：hash-anchored edits、LSP、browser、subagents、tool harness。 |
| `multica-ai/multica` | 36331 | 2026-06-12 | Go | NOASSERTION | Managed agents platform，把 coding agents 产品化为可分配任务、追踪进度、复合 skills 的 teammate。 |
| `OpenCoworkAI/open-cowork` | 1590 | 2026-06-07 | TypeScript | MIT | Desktop agent app，整合 Claude Code、MCP、Skills、sandbox、IM。 |
| `vllm-project/aibrix` | 4870 | 2026-06-11 | Go | Apache-2.0 | GenAI inference infrastructure components，补 [[llm-serving-engine-selection-map]] 的 serving control plane。 |
| `llm-d/llm-d` | 3346 | 2026-06-12 | Shell | Apache-2.0 | Kubernetes 上的 modern distributed inference stack，总入口。 |
| `llm-d/llm-d-router` | 220 | 2026-06-12 | Go | Apache-2.0 | LLM inference request intelligent entry point，进入 routing 专题。 |
| `llm-d/llm-d-kv-cache` | 155 | 2026-06-11 | Go | Apache-2.0 | Distributed KV cache scheduling and offloading libraries，直接连接 [[kv-cache-offload]]。 |

## P1 项目

| 项目 | stars | 最近 push | 语言 | license | 当前定位 |
|---|---:|---|---|---|---|
| `kagent-dev/kagent` | 2979 | 2026-06-12 | Go | Apache-2.0 | Cloud Native Agentic AI，把 [[ai-ops]]、K8s agent 和 MCP 接到一起。 |
| `GoogleCloudPlatform/kubectl-ai` | 7494 | 2026-05-08 | Go | Apache-2.0 | AI powered Kubernetes Assistant，kubectl 入口。 |
| `weibaohui/k8m` | 829 | 2026-06-04 | Go | MIT | Mini Kubernetes AI Dashboard，含 MCP、操作权限、多集群、异常检测。 |
| `kubewall/kubewall` | 1903 | 2026-05-19 | TypeScript | Apache-2.0 | Single-binary Kubernetes dashboard + AI integration。 |
| `kubernetes-sigs/gateway-api-inference-extension` | 690 | 2026-06-11 | Go | Apache-2.0 | Gateway API Inference Extension，是 inference routing 进入 K8s Gateway API 的标准化入口。 |
| `envoyproxy/ai-gateway` | 1742 | 2026-06-11 | Go | Apache-2.0 | Envoy Gateway 上的 GenAI access/routing 管理。 |
| `kgateway-dev/kgateway` | 5559 | 2026-06-12 | Go | Apache-2.0 | Cloud-native API Gateway and AI Gateway。 |
| `higress-group/higress` | 8624 | 2026-06-07 | Go | Apache-2.0 | AI Native API Gateway，和 [[agent-credential-isolation]]、HiClaw 凭据托管背景相关。 |
| `vllm-project/semantic-router` | 4321 | 2026-06-12 | Go | Apache-2.0 | System-level intelligent router for mixture-of-models，连接 AI Gateway 和模型路由。 |
| `lm-sys/RouteLLM` | 5011 | 2024-08-10 | Python | Apache-2.0 | LLM router serving/evaluation framework，偏成本/质量路由算法基线。 |
| `katanemo/plano` | 6585 | 2026-06-09 | Rust | Apache-2.0 | AI-native proxy and data plane，和 [[agentgateway]] 属于 gateway/data plane 层。 |
| `gpustack/gpustack` | 5145 | 2026-06-12 | Python | Apache-2.0 | GPU cluster manager，编排 vLLM/SGLang 推理引擎。 |
| `ome-projects/ome` | 464 | 2026-06-12 | Go | Apache-2.0 | Open Model Engine，K8s operator for LLM serving、GPU scheduling、model lifecycle。 |
| `kserve/kserve` | 5563 | 2026-06-12 | Go | Apache-2.0 | Standardized distributed generative and predictive AI inference platform on Kubernetes。 |
| `kubeai-project/kubeai` | 1209 | 2026-06-10 | Go | Apache-2.0 | AI inference operator，覆盖 LLM/VLM/embedding/speech-to-text。 |
| `tirth8205/code-review-graph` | 18405 | 2026-06-10 | Python | MIT | Local-first code intelligence graph for MCP/CLI。 |
| `abhigyanpatwari/GitNexus` | 41980 | 2026-06-12 | TypeScript | NOASSERTION | Browser-side repo knowledge graph + Graph RAG agent。 |
| `AsyncFuncAI/deepwiki-open` | 16855 | 2026-06-03 | Python | MIT | Open-source DeepWiki，AI-powered wiki generator for repos。 |

## P2 项目

| 项目 | stars | 最近 push | 语言 | license | 当前定位 |
|---|---:|---|---|---|---|
| `openai/codex-plugin-cc` | 20740 | 2026-04-18 | JavaScript | Apache-2.0 | Claude Code 调用 Codex 的 delegation plugin。 |
| `liaohch3/claude-tap` | 1671 | 2026-06-12 | Python | MIT | Coding agent API traffic trace viewer，覆盖 Claude Code、Codex、Gemini、Cursor、OpenCode、Pi、Hermes。 |
| `chenhg5/cc-connect` | 12197 | 2026-06-11 | Go | NOASSERTION | 把本地 coding agents 接到 Feishu/Lark、Slack、Telegram、Discord、企业微信等 IM。 |
| `junhoyeo/tokscale` | 3680 | 2026-06-11 | Rust | MIT | 多 coding agent token usage tracker + leaderboard/graph。 |
| `Project-HAMi/HAMi` | 3558 | 2026-06-11 | Go | Apache-2.0 | Heterogeneous GPU sharing on Kubernetes。 |
| `kubernetes-sigs/dra-driver-nvidia-gpu` | 654 | 2026-06-11 | Go | Apache-2.0 | NVIDIA GPU DRA driver。 |
| `NVIDIA/gpu-operator` | 2732 | 2026-06-12 | Go | Apache-2.0 | Kubernetes GPU driver/runtime/operator 管理基座。 |
| `NVIDIA/k8s-device-plugin` | 3786 | 2026-06-11 | Go | Apache-2.0 | Kubernetes NVIDIA device plugin 核心项目。 |

## 核验结论

- P0 不应再只是待办：它们分别补齐 runtime substrate、memory layer、coding agent 执行面、personal agent productization 和 K8s inference control plane。
- P1 是专题补强：K8s AI assistant、AI Gateway/routing、model serving operator、code intelligence/wiki generator 都可以直接进入横向地图。
- P2 不是低价值，而是更像生态配套层：coding agent plugin/observability/IM bridge/token cost，以及 GPU/DRA/device plugin 基座。
- `lm-sys/RouteLLM` 最近 push 停在 2024-08-10，仍有算法基线价值，但不应按同等活跃度对待。
