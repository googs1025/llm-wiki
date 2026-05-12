---
title: Agent 长期记忆
tags: [agent-memory, llm-infra, design-pattern]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[event-driven-memory-pipeline]], [[three-tier-search-protocol]], [[ai-as-compressor]], [[claude-mem]]
---

# Agent 长期记忆

让 AI Agent 跨会话保留上下文的设计领域。核心矛盾：**LLM 上下文窗口有限 + 对话历史天然噪声大 + 用户期望"上次说过的事这次还记得"**。

## 基础形态对比

| 方案 | 存储 | 检索 | 缺点 |
|------|------|------|------|
| 全量对话历史 | 原始 message 数组 | 按时间截取 | 噪声大、token 浪费、超窗即丢 |
| 摘要压缩 | LLM 生成的会话摘要 | 加载完整摘要 | 摘要损失细节、跨会话不易关联 |
| **结构化观察 + 双索引** | facts / concepts / files 等可索引字段 + 向量 | 三层搜索协议 | 实现成本高，但精度和 token 效率最好 |

[[claude-mem]] 采用第三种。

## 关键设计要点

### 1. 记忆生命周期 ≠ 会话生命周期

claude-mem 用 **session_id 双轨制**：

- `contentSessionId` — 当前对话会话 ID（短期）
- `memorySessionId` — 跨 session 累积的记忆线 ID（长期）

> 必须分两个 ID 才能跨 session 累积同一项工作的上下文。

### 2. 压缩比检索更关键

LLM 的真正用途不是"问答"而是"信息浓缩"。详见 [[ai-as-compressor]]。

### 3. 双索引：全文 + 向量

- **全文（FTS5）**——精确关键词命中
- **向量（Chroma）**——语义/概念相似
- 两者结果合并排序

### 4. 反向调用入口（Skill）

给 Agent 注册一个"查记忆"工具（如 mem-search Skill），提示词写清触发时机（"用户提到过去/上次时调用"），模型自己学会触发。比手动每次塞历史更优雅。

### 5. 边缘剥离敏感数据

敏感数据零信任处理——`<private>...</private>` 标签在 hook 层（边缘）就剥离，永不进入压缩管道。代码在 `src/utils/tag-stripping.ts`。

## 完整管道

详见 [[event-driven-memory-pipeline]]。

## 适用场景

- 长周期项目助手（代码 Agent、研究 Agent）
- 多轮调试场景（用户问"这个 bug 上次怎么改的"）
- 需要审计的 AI 操作（医疗、合规）

## 参考

- [[src-claude-mem-architecture]]
