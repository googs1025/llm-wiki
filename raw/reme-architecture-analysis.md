# ReMe 架构与设计思路分析

> 仓库：https://github.com/agentscope-ai/ReMe · 分析日期：2026-06-12 · 版本：HEAD `f458566`（2026-06-10，feat: add cron scheduling support and enhance Claude Code integration (#278)）· 获取方式：GitHub API 复核 HEAD + codeload tarball 源码扫描。

## 一句话定位

`agentscope-ai/ReMe` 是 AgentScope 生态的 memory management toolkit。它同时保留“memory as files”的 ReMeLight 和更完整的 vector/service pipeline：personal memory、task memory、tool memory、working memory 都有独立 summary/retrieve op，目标是解决长对话 context window 和跨 session stateless 两个问题。

## 核心架构图

```text
┌──────────────────────────── agent conversation / trajectory ─────────────────┐
│ messages · tool results · task traces · user preferences                      │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│ ReMe memory orchestration                                                     │
│ context check · compact · summarize · retrieve · pre_reasoning_hook           │
└───────────────┬───────────────────────────────┬───────────────────────────────┘
                │                               │
┌───────────────▼──────────────┐  ┌─────────────▼──────────────────────────────┐
│ ReMeLight file memory         │  │ vector/service pipeline                     │
│ MEMORY.md · daily journal     │  │ personal/task/tool/working ops + vector DB  │
└───────────────┬──────────────┘  └─────────────┬──────────────────────────────┘
                │                               │
┌───────────────▼───────────────────────────────▼──────────────────────────────┐
│ recalled context: compact summary · semantic/BM25 hits · task/tool lessons    │
└───────────────────────────────────────────────────────────────────────────────┘
```

## 模块分层

| 层/目录 | 责任 |
|---|---|
| `reme/reme_light.py` + `reme/memory/file_based/**` | 文件型记忆系统：`MEMORY.md`、daily journal、dialog JSONL、tool_result cache。 |
| `reme_ai/summary/**` | personal/task/tool/working 四类总结 pipeline，包含 observation、reflection、dedup、validation、trajectory segmentation。 |
| `reme_ai/retrieve/**` | personal/task/tool/working 检索 pipeline，包含 query rewrite、semantic rank、rerank/fusion、文件 grep/read/write。 |
| `reme_ai/vector_store/**` | 向量记忆更新、频率/效用更新、recall op。 |
| `reme_ai/service/**` | AgentScope Runtime memory service、personal/task memory service。 |

## 关键数据流

1. ReMeLight 在 pre-reasoning 前检查 token，过阈值则压缩老消息、保留近期上下文，并把长 tool output offload 到文件。
2. 长期记忆写入 `MEMORY.md` 和 `memory/YYYY-MM-DD.md`，原始对话进入 `dialog/YYYY-MM-DD.jsonl`，便于人工迁移/修改。
3. vector pipeline 将 personal/task/tool/working memory 拆成不同 summary 和 retrieve op，按场景选择信息，而不是用一个大表统管所有记忆。
4. 检索结果回填到 agent context，形成“压缩摘要 + 精确文件事实 + 语义召回”的组合。

## 设计决策与哲学

- 文件优先版本适合个人 agent：可读、可迁移、可手改；vector/service 版本适合规模化 AgentScope 应用。
- 按 memory type 拆 pipeline 比 mem0 的通用 memory layer 更重，但更贴合 agent 工作流。
- 把 tool result 单独 offload，说明 ReMe 主要关心 context 爆炸，不只是长期偏好。
- 最近增强 Claude Code 集成，表明它从 AgentScope 内存组件向 coding-agent 生态扩展。

## 与已有项目的对比

和 [[mem0]] 相比，ReMe 更框架内生，记忆类型更细；和 [[memsearch]] 相比，它不是 Markdown journal + Milvus shadow index，而是 context management + file/vector memory；和 [[tencentdb-agent-memory]] 相比，ReMe 更轻、更贴 AgentScope hooks。

## 选型提示

- 适合深挖的问题：入口协议、状态源、工具/运行时边界、部署模型、失败恢复和安全治理。
- 不要只看 README：本页结论来自源码目录、入口文件、核心包和 GitHub 当前 HEAD 的组合扫描。
- 后续如继续深化，应补充 release/tag 变更、关键 issue/PR 和真实部署案例。
