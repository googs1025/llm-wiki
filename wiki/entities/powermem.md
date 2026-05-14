---
title: PowerMem
tags: [entity, ai-infra, memory-layer, llm-agents, oceanbase]
date: 2026-05-14
sources: [powermem-architecture-analysis.md]
related: [oceanbase, ebbinghaus-forgetting-curve, hybrid-search-rrf, mcp, claude-code-plugin, agent-memory, claude-mem]
---

# PowerMem

**OceanBase 团队开源的、面向 LLM agents/apps 的持久化记忆中间件。** Apache 2.0，Python 3.11+，PyPI 包名 `powermem`，最新版本 v1.1.1（2026-05-13）。

## 一句话定位

把对话流水线压缩成可被语义检索的长期记忆。**四路混合检索**（向量 + 全文 + 稀疏向量 + 图谱，OceanBase 原生支持）+ **LLM 驱动的事实抽取/更新** + **[[ebbinghaus-forgetting-curve]] 衰减**。SDK / CLI（`pmem`）/ FastAPI 服务 + Dashboard / [[mcp]] 服务 / VS Code 扩展 / [[claude-code-plugin]] **共用同一份 `.env`**。

## 关键能力

| 维度 | 能力 |
|------|------|
| **存储后端** | [[oceanbase]]（默认，含嵌入式 SeekDB）/ pgvector / SQLite |
| **向量索引** | HNSW / HNSW_SQ / IVFFLAT / IVFSQ / IVFPQ |
| **全文检索** | jieba / ngram / ngram2 / ik / beng / space 6 种 parser |
| **稀疏向量** | qwen_sparse（仅 OceanBase 后端支持） |
| **图谱** | OceanBase Graph Store，3-hop 遍历 + 早停 + 防环 |
| **混合融合** | [[hybrid-search-rrf]] + 自适应权重归一化 |
| **LLM 提供商** | 12 种：openai / anthropic / qwen / gemini / deepseek / ollama / vllm / langchain / azure / siliconflow / zai / qwen_asr |
| **Embedder 提供商** | 15 种 + sparse |
| **Reranker 提供商** | 4 种：qwen / jina / zai / generic |
| **多 Agent** | 5 种 scope（private/agent_group/user_group/public/restricted）+ 4 种 Controller |
| **多模态** | text / image / audio（独立 `audio_llm` 配置） |

## 接入形态

- **Python SDK**：`from powermem import Memory, auto_config; memory = Memory(config=auto_config())`
- **CLI**：`pmem memory add/search/list`、`pmem shell` REPL、`pmem config init`
- **HTTP API + Dashboard**：`powermem-server --port 8000`，Dashboard 自动挂载 `/dashboard/`
- **[[mcp]] Server**：`uvx powermem-mcp sse`（sse / stdio / streamable-http）
- **VS Code 扩展**：把记忆接入 Cursor / Claude / Codex / Copilot / Windsurf
- **[[claude-code-plugin]]**：Go 二进制 hook + `UserPromptSubmit` 自动检索注入 `additionalContext`
- **OpenClaw 集成**：通过 `memory-powermem` 插件

## 设计哲学（与同类记忆框架对照）

- **跨形态统一中间件 vs [[claude-mem]] 单一插件**：一个 `.env` 同时供 7 种客户端使用，不复制配置/状态。
- **认知科学抽象 + 数学公式解耦存储**：working / short / long 三层 + [[ebbinghaus-forgetting-curve]] `R = e^(-t/S)`；Intelligence 不直接改库，只在 metadata 写分数；`MemoryOptimizer` 离线扫描决定晋升/清理 —— 避免每次写都跑昂贵 LLM。
- **OceanBase 优先但绝不绑死**：`VectorStoreFactory + StorageAdapter` 关键解耦点；v1.1.0 引入嵌入式 SeekDB（`pyseekdb`）让用户零部署用上 OceanBase 语义。
- **后台线程池**：模块级 3-worker `ThreadPoolExecutor`，前台只阻塞 LLM 抽取/重要性评估，telemetry/audit/optimization 异步。
- **Provider 矩阵 + pydantic-settings**：每个 provider 一文件一 config 类；切换只改 `.env` 里的 `LLM_PROVIDER` —— 跑通"Qwen + DashScope + OceanBase 全栈国产化"路径。

## Benchmark 数字（LOCOMO 长对话）

| 指标 | PowerMem | "塞满上下文" baseline | 倍数 |
|------|----------|----------------------|------|
| 准确率 | 78.70% | 52.9% | +25.8 pp |
| Retrieval p95 latency | 1.44s | 17.12s | 11.9× faster |
| Tokens / query | ~0.9k | ~26k | 28.9× less |

## 版本演进

| 版本 | 日期 | 关键变更 |
|------|------|----------|
| 0.1.0 | 2025-11-14 | 核心 memory + 混合检索；LLM 抽取；遗忘曲线；多 agent；OceanBase/PG/SQLite |
| 0.2.0 | 2025-12-16 | 高级 profiles；多模态 |
| 0.3.0 | 2026-01-09 | 生产级 HTTP API Server；Docker |
| 0.4.0 | 2026-01-20 | 稀疏向量；profile-based query rewrite；schema 迁移工具 |
| 0.5.0 | 2026-02-06 | pydantic-settings 统一配置；OceanBase 原生混合搜索 |
| 1.0.0 | 2026-03-16 | CLI `pmem` + Web Dashboard |
| 1.1.0 | 2026-04-02 | 嵌入式 SeekDB；IDE 集成（VS Code + Claude Code） |
| 1.1.1 | 2026-04-? | bug fix release（GraphStoreFactory / sparse_embedder / custom prompt env / i18n） |

## 相关页面

- 架构详解：[[src-powermem-architecture]]
- 默认存储后端：[[oceanbase]]
- 核心算法：[[ebbinghaus-forgetting-curve]]、[[hybrid-search-rrf]]
- 同类对照：[[claude-mem]]（单一 Claude Code 插件 vs PowerMem 通用中间件）、[[agent-memory]]（领域综述）
- 接入：[[claude-code-plugin]]、[[mcp]]
