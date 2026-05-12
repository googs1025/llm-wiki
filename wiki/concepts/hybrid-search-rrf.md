---
title: 混合检索与 RRF 重排
tags: [semantic-search, retrieval, design-pattern, llm-infra]
date: 2026-05-12
sources: [src-claude-context-architecture]
related: [[code-semantic-search]], [[three-tier-search-protocol]], [[milvus]], [[claude-context]]
---

# 混合检索与 RRF 重排

并行跑多种召回 + 用 RRF（Reciprocal Rank Fusion）公式合并排名的检索模式。[[claude-context]] 的核心检索机制。

## 为什么单一检索不够

| 检索类型 | 擅长 | 短板 |
|---------|------|------|
| **Dense 向量** | 概念匹配（"用户登录" 命中 `authenticateUser`） | 精确符号召不回（"JWT_SECRET" 可能漂掉） |
| **Sparse 向量** / BM25 | 精确符号、罕见词（函数名、常量名） | 同义改写完全召不回 |
| 关键词字符串匹配 | 完全精确 | 改写一字就废 |

**任何单一信号都有盲区** —— 并集召回 + 智能合并 > 任何单一策略。

## Hybrid Search 在 claude-context 的实现

```ts
vectorDB.hybridSearch({
  queries: [
    { type: 'dense',  vector: denseEmb,  params: { nprobe: 10 } },
    { type: 'sparse', vector: sparseEmb, params: { drop_ratio: 0.2 } }
  ],
  rerank: { strategy: 'rrf', k: 100 }
})
```

[[milvus|Milvus]] 在一个 collection 里同时存 dense + sparse 双向量字段，一次 RPC 完成两路召回 + 重排。

## RRF 公式

```
score(doc) = Σ_i  1 / (k + rank_i(doc))
```

- `rank_i(doc)`：doc 在第 i 路召回中的排名（1, 2, 3...）
- `k`：平滑常数（claude-context 用 100），越大头部排名差异越小

**性质**：
- 排名信号即可，**不依赖各路 score 的绝对量级**——避免不同信号量纲不可比的难题
- 多路同时命中得分翻倍，单路命中也有分（不会 0 分丢失）

## 应用到 Agent 记忆 / RAG 的检索

代码以外的场景同样适用，建议并行跑：

| 信号 | 用途 |
|------|------|
| 向量相似度 | 语义匹配 |
| 关键词 / BM25 | 精确符号、专有名词 |
| 时间衰减 | 最近优先（适合记忆场景） |
| metadata 过滤 | 业务约束（项目、用户、标签） |

最后 RRF 合并即可。这是企业级 RAG 的标配。

## 与三层搜索协议的关系

[[three-tier-search-protocol]] 解决**返回多少**（先 ID + 摘要，再按需取详情），hybrid + RRF 解决**怎么找到**（多信号并集）。两者正交、可叠加：

```
hybrid + RRF  →  ID 列表 + 摘要  →  按需 get_observations
   (找到)            (返摘要)          (取详情)
```

## 参考

- [[src-claude-context-architecture]]
