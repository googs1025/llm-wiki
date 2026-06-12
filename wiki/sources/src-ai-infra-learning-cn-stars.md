---
title: AI Infra Learning 中文 Star 项目清单整理
tags: [ai-infra, learning, chinese, llm, stars]
date: 2026-06-12
sources: [github-stars-ai-infra-learning-cn]
related: [[ai-infra-learning-cn-map]], [[llm-inference]], [[ai-agent-frameworks-map]], [[llm-serving-engine-selection-map]], [[agent-skills-plugin-system-map]]
---

# AI Infra Learning 中文 Star 项目清单整理

来源：GitHub Stars list `googs1025/lists/ai-infra-learning-中文`，描述为“中文 AI infra/LLM 教程与 awesome list”。本次通过 GitHub GraphQL API 于 2026-06-12 复核，列表共 32 个仓库。

这组项目不是单一技术栈，而是一条中文 AI Infra 学习路径：从 LLM 基础、AI 系统/基础设施、CUDA kernel、推理优化、模型部署、Agent 应用，到面试/项目材料。它更适合整理成学习路线与项目地图，而不是逐个都做架构深挖。

## 项目清单

| 项目 | 方向 | stars | 语言 | 当前判断 |
|---|---:|---:|---|---|
| `Infrasys-AI/AISystem` | AI 系统全栈 | 16923 | Jupyter Notebook | AI infra 底层体系核心教材，优先级高 |
| `Infrasys-AI/AIInfra` | AI 基础设施 | 7319 | Jupyter Notebook | AI Infra 中文主线材料，优先级高 |
| `cr7258/ai-infra-learning` | 学习会议/资料 | 478 | - | 中文学习社群材料，适合做入口索引 |
| `CalvinXKY/InfraTech` | AI Infra 代码练习 | 2555 | Jupyter Notebook | PyTorch/vLLM/SGLang/性能加速练习，适合实践线 |
| `liguodongiot/llm-action` | LLM 工程化实战 | 24508 | HTML | 大模型工程化与应用落地中文材料 |
| `InftyAI/Awesome-LLMOps` | LLMOps 工具清单 | 238 | Python | LLMOps 工具索引，适合作补充清单 |
| `xlite-dev/Awesome-LLM-Inference` | LLM/VLM 推理论文代码 | 5281 | Python | 推理优化论文与代码索引，关联 [[llm-inference]] |
| `xlite-dev/LeetCUDA` | CUDA kernel 练习 | 11241 | Cuda | CUDA/Tensor Core/HGEMM/FA-2 实战，优先级高 |
| `Tony-Tan/CUDA_Freshman` | CUDA 入门 | 2759 | Cuda | CUDA 新手入门材料 |
| `a-hamdi/GPU` | GPU kernel 100 days | 601 | Cuda | kernel 训练打卡，适合补充练习 |
| `HeKun-NVIDIA/CUDA-Programming-Guide-in-Chinese` | CUDA 中文指南 | 1985 | - | CUDA 官方编程指南中文翻译 |
| `datawhalechina/happy-llm` | LLM 基础 | 31123 | Jupyter Notebook | 从零开始构建大模型，适合基础入口 |
| `datawhalechina/self-llm` | 开源模型微调/部署 | 30859 | Jupyter Notebook | 中文开源模型食用指南，实践价值高 |
| `AiHubCN/Awesome-Chinese-LLM` | 中文 LLM 清单 | 22611 | - | 中文大模型生态索引 |
| `Hannibal046/Awesome-LLM` | LLM 总清单 | 26922 | - | 通用 LLM awesome list |
| `datawhalechina/hello-agents` | Agent 教程 | 58595 | Python | 从零开始构建智能体，Agent 学习主线 |
| `panaversity/learn-agentic-ai` | Agent-native cloud | 4220 | Jupyter Notebook | Dapr/MCP/A2A/K8s/Knowledge Graph 组合路线 |
| `luzhenqian/ai-coding-lab` | AI 编程实战 | 137 | TypeScript | Vibe Coding → Agent/RAG 的实践教程 |
| `libukai/awesome-agent-skills` | Agent Skills | 4677 | Python | Agent Skills 生态中文入口，关联 [[agent-skills-plugin-system-map]] |
| `RKiding/Awesome-finance-skills` | Finance Agent Skills | 2483 | Python | 垂直领域 Skills 示例 |
| `nanocoai/nanoclaw` | Containerized personal agent | 29817 | TypeScript | 安全容器化 OpenClaw 替代项目，值得后续单独看 |
| `hhaAndroid/awesome-mm-chat` | 多模态 chat 清单 | 283 | Python | 多模态 chat 补充索引 |
| `WeThinkIn/AIGC-Interview-Book` | AIGC/LLM/Agent 面试 | 3913 | - | 面试知识库 |
| `bcefghj/ai-agent-interview-guide` | Agent 面试 | 1231 | Python | Agent 面试/项目/简历材料 |
| `wdndev/llm_interview_note` | LLM 面试笔记 | 14461 | HTML | LLM 算法/应用工程师面试题 |
| `antgroup/agentic-ai-landscape` | Agentic landscape | 472 | TypeScript | 数据驱动 agentic landscape |
| `academicpages/academicpages.github.io` | 个人主页模板 | 17130 | SCSS | 与 AI infra 主线弱相关，可忽略或放个人品牌 |
| `cr7258/ai-briefing` | AI briefing | 2 | Dart | 个人/小项目，暂不优先 |
| `LincanLi-X/Awesome-Data-Centric-Autonomous-Driving` | 自动驾驶数据中心清单 | 179 | - | 领域专题，非主线 |
| `LMD0311/Awesome-World-Model` | World Model 清单 | 2106 | - | 具身/自动驾驶方向补充 |
| `mainpropath/AI-java` | Java AI 示例 | 290 | Java | Java 应用学习材料，非 AI infra 核心 |
| `mainpropath/AI-SmartFuse-Framework` | Java AI framework | 288 | Java | Java 应用框架，非核心 |

## 初步分层

1. **AI Infra 总论**：`AISystem`、`AIInfra`、`ai-infra-learning`、`InfraTech`、`llm-action`。
2. **CUDA / GPU kernel**：`LeetCUDA`、`CUDA_Freshman`、`GPU`、`CUDA-Programming-Guide-in-Chinese`。
3. **LLM 推理优化**：`Awesome-LLM-Inference`，可与 [[paged-attention]]、[[radix-attention]]、[[kv-cache-offload]]、[[llm-inference]] 连接。
4. **模型基础 / 微调 / 部署**：`happy-llm`、`self-llm`、`Awesome-Chinese-LLM`、`Awesome-LLM`。
5. **Agent / Skills / 应用开发**：`hello-agents`、`learn-agentic-ai`、`ai-coding-lab`、`awesome-agent-skills`、`Awesome-finance-skills`、`nanoclaw`。
6. **面试 / 职业化**：`AIGC-Interview-Book`、`ai-agent-interview-guide`、`llm_interview_note`。
7. **领域扩展**：自动驾驶、world model、多模态 chat、Java AI 应用。

## 后续建议

优先把这份 list 作为“学习路径源材料”连接到 [[ai-infra-learning-cn-map]]。真正值得后续单独摄入源码/架构的项目是：`Infrasys-AI/AISystem`、`Infrasys-AI/AIInfra`、`CalvinXKY/InfraTech`、`xlite-dev/LeetCUDA`、`xlite-dev/Awesome-LLM-Inference`、`datawhalechina/self-llm`、`datawhalechina/hello-agents`、`nanocoai/nanoclaw`。
