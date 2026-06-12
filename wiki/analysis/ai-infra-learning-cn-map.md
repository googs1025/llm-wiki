---
title: AI Infra 中文学习项目地图
tags: [ai-infra, learning-path, chinese, llm, project-map]
date: 2026-06-12
sources: [src-ai-infra-learning-cn-stars]
related: [[llm-inference]], [[llm-serving-engine-selection-map]], [[ai-agent-frameworks-map]], [[agent-skills-plugin-system-map]], [[github-stars-ingest-candidates]]
---

# AI Infra 中文学习项目地图

这页把 `AI Infra Learning (中文)` star list 整理成实际学习路线。它解决的问题不是“哪个项目最火”，而是：如果目标是快速理解 AI Infra / LLM 工程 / Agent 工程，应该按什么顺序读、哪些项目只作索引、哪些值得后续深挖源码。

## 推荐学习主线

### 1. 先建立 AI 系统全景

优先读 `Infrasys-AI/AISystem`、`Infrasys-AI/AIInfra`、`cr7258/ai-infra-learning`。

这三类材料适合回答“AI Infra 到底包含哪些层”：芯片/加速器、通信、编译器、训练框架、推理引擎、服务编排、LLMOps、Kubernetes 资源管理。学习目标是先建立分层地图，不急着陷入某个框架的 API。

### 2. 补 LLM 基础和开源模型使用

读 `datawhalechina/happy-llm`、`datawhalechina/self-llm`、`AiHubCN/Awesome-Chinese-LLM`、`Hannibal046/Awesome-LLM`。

`happy-llm` 偏原理入门，`self-llm` 偏开源模型微调/部署实操，两个组合起来能覆盖“模型是什么”和“怎么在本地/服务器上跑起来”。Awesome list 只适合作查表，不适合从头读。

### 3. 进入 GPU / CUDA / kernel

顺序建议：`HeKun-NVIDIA/CUDA-Programming-Guide-in-Chinese` → `Tony-Tan/CUDA_Freshman` → `xlite-dev/LeetCUDA` → `a-hamdi/GPU`。

这一层是从“会用模型”走向“理解推理性能”的关键。`LeetCUDA` 最有工程训练价值，因为它覆盖 200+ CUDA kernels、Tensor Cores、HGEMM、FlashAttention 相关 MMA 练习；适合和 [[paged-attention]]、[[radix-attention]]、[[kv-cache-offload]] 的理论页一起读。

### 4. 读推理优化和 serving 论文/代码索引

核心入口是 `xlite-dev/Awesome-LLM-Inference`，再回到本 wiki 的 [[llm-serving-engine-selection-map]]。

这一层关注 FlashAttention、PagedAttention、量化、并行、KV cache、speculative decoding、prefill/decode disaggregation。读法不是把 awesome list 全部扫完，而是围绕问题选论文：吞吐、延迟、显存、长上下文、router、KV offload。

### 5. 做工程化和 LLMOps 横向理解

读 `liguodongiot/llm-action`、`InftyAI/Awesome-LLMOps`、`CalvinXKY/InfraTech`。

`llm-action` 适合建立工程化知识面；`Awesome-LLMOps` 适合作工具查表；`InfraTech` 更适合动手做 PyTorch/vLLM/SGLang 框架入门和性能加速练习。这个阶段可以开始回看 [[dynamo]]、[[vllm]]、[[sglang]]、SkyPilot、K8s AI Serving 相关页面。

### 6. 进入 Agent / Skills / 应用层

读 `datawhalechina/hello-agents`、`panaversity/learn-agentic-ai`、`luzhenqian/ai-coding-lab`、`libukai/awesome-agent-skills`。

`hello-agents` 是 Agent 入门主线；`learn-agentic-ai` 把 OpenAI Agents SDK、Memory、MCP、A2A、Knowledge Graph、Dapr、Kubernetes 串起来，适合连接本 wiki 的 [[mcp]]、[[agent-memory]]、[[agent-skills-plugin-system-map]]；`ai-coding-lab` 偏 AI 编程实战；`awesome-agent-skills` 是 Skills 生态索引。

### 7. 最后用面试材料查漏补缺

读 `WeThinkIn/AIGC-Interview-Book`、`wdndev/llm_interview_note`、`bcefghj/ai-agent-interview-guide`。

这些材料不适合作第一遍学习主线，因为容易把概念碎片化。更适合在读完前六层后，用来补缺：模型基础、推理优化、RAG、Agent、项目表达、简历和 STAR 面试稿。

## 项目取舍

| 类型 | 项目 | 用法 |
|---|---|---|
| 核心教材 | `AISystem`、`AIInfra`、`happy-llm`、`self-llm`、`hello-agents` | 从头读，建立主干 |
| 工程练习 | `InfraTech`、`LeetCUDA`、`CUDA_Freshman`、`GPU`、`ai-coding-lab` | 边读边做，适合沉淀代码实验 |
| 查表索引 | `Awesome-LLM-Inference`、`Awesome-Chinese-LLM`、`Awesome-LLM`、`Awesome-LLMOps`、`awesome-agent-skills` | 不全量阅读，按问题检索 |
| 职业/面试 | `AIGC-Interview-Book`、`llm_interview_note`、`ai-agent-interview-guide` | 用于复盘和表达 |
| 暂缓 | `academicpages`、`ai-briefing`、Java AI 示例、自动驾驶/world model 清单 | 与 AI Infra 主线弱相关，暂不深挖 |

## 最值得后续单独摄入的项目

1. `Infrasys-AI/AISystem`：AI 系统全栈知识体系，适合产出一篇“AI 系统分层”概念页。
2. `Infrasys-AI/AIInfra`：AI Infra 中文材料核心入口，适合做学习源页。
3. `CalvinXKY/InfraTech`：包含 PyTorch/vLLM/SGLang/性能加速练习，适合做工程实践地图。
4. `xlite-dev/LeetCUDA`：CUDA kernel 实战价值高，适合补 GPU kernel 学习路线。
5. `xlite-dev/Awesome-LLM-Inference`：可和 [[llm-inference]]、[[llm-serving-engine-selection-map]] 联动，整理推理优化论文路线。
6. `datawhalechina/self-llm`：中文开源模型微调/部署实战，适合补模型部署入门。
7. `datawhalechina/hello-agents`：Agent 教程主线，可和 [[ai-agent-frameworks-map]]、[[agent-framework-programming-model-map]] 对齐。
8. `nanocoai/nanoclaw`：容器化个人 Agent，和 OpenClaw / OpenCowork / nanobot / OpenShell 有架构对比价值。

## 这条路线和现有 wiki 的连接

- [[llm-inference]]、[[paged-attention]]、[[radix-attention]]、[[kv-cache-offload]]：承接推理优化理论。
- [[llm-serving-engine-selection-map]]：承接 vLLM/SGLang/Dynamo/SkyPilot/llm-d 等工程选型。
- [[ai-agent-frameworks-map]]、[[agent-framework-programming-model-map]]：承接 Agent 应用层。
- [[agent-skills-plugin-system-map]]：承接 Agent Skills 学习材料。
- [[github-stars-ingest-candidates]]：承接后续项目摄入 backlog。
