---
title: 三层搜索协议
tags: [agent-memory, design-pattern, token-economy]
date: 2026-05-12
sources: [src-claude-mem-architecture]
related: [[agent-memory]], [[event-driven-memory-pipeline]], [[claude-mem]]
---

# 三层搜索协议

让 Agent 在记忆库中检索时**避免上下文爆炸**的设计模式。由 [[claude-mem]] 的 `mem-search` Skill 实现。

## 协议三层

```
search(query)          → 返回 ID 列表 + 一句话摘要      (~50-100 tokens/result)
   ↓
timeline(anchor_id)    → 围绕锚点取上下文窗口
   ↓
get_observations(ids)  → 仅取筛选后的 ID 全文
```

## 核心思想

**永远先返低 token 摘要，让模型筛选后再取详情。**

朴素做法：一次返回所有匹配结果的全文 → 单次查询可能吃掉数千 token，命中 10 条无关结果就废了一半上下文。

三层协议做法：

| 阶段 | 返回 | Token 量级 | 决策方 |
|------|------|-----------|--------|
| `search` | 20 个 ID + 一句话摘要 | ~1-2k | 模型决定哪些值得深看 |
| `timeline` | 锚点附近的事件序列 | ~500 | 模型决定要不要全文 |
| `get_observations` | 筛选后 3-5 条全文 | ~3-5k | 真正读细节 |

相比一次性全文返回，省 10x token。

## 为什么 Agent 能自主调用

claude-mem 把这套协议注册成 Skill（`plugin/skills/mem-search/SKILL.md`），描述里写明触发时机。Claude 在判断"用户问到过去"时会自主决定调用——SKILL.md 的描述文案艺术决定了触发精度。

## 可迁移性

任何"AI Agent + 长期存储"场景都适用：

- 给 RAG 加分层检索（先返 chunk ID，再取选中 chunk 全文）
- 给企业知识库 Agent 加分层调用（先返文档元信息，再取段落）
- 工具调用结果分级（先返摘要，模型按需 expand）

## 与朴素 RAG 的对比

| 维度 | 朴素 RAG | 三层协议 |
|------|---------|---------|
| 一次返多少 | top-K 全文 chunk | top-N ID + 摘要 |
| 谁决定要哪些 | 检索算法（固定） | LLM（动态） |
| Token 效率 | 低 | 高 |
| 实现复杂度 | 低 | 中 |

## 参考

- [[src-claude-mem-architecture]]
