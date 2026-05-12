---
title: 代码语义检索
tags: [code-rag, semantic-search, llm-infra, design-pattern]
date: 2026-05-12
sources: [src-claude-context-architecture]
related: [[hybrid-search-rrf]], [[merkle-dag-fingerprint]], [[claude-context]], [[agent-memory]]
---

# 代码语义检索

让 AI Agent **不必多轮 grep/read** 就能在大型代码库中直达相关片段的工程方法。由 [[claude-context]] 验证。

## 与传统方案对比

| 方案 | 痛点 |
|------|------|
| 整个目录塞 prompt | Token 爆炸，成本高 |
| Agent 自己 grep/read 探索 | 慢、消耗工具调用次数 |
| 仅关键词匹配 | 找不到概念相关代码 |
| **语义检索（本方案）** | 一次查询直达目标 |

## 标准管道

```
源代码
   ↓ Splitter (AST → 字符兜底)
代码块 (chunk)
   ↓ Embedding
向量
   ↓ VectorDB
检索引擎
   ↓ 用户自然语言查询
top-K 相关片段
```

## 三大关键技术点

### 1. 分块策略

**AST 分块（首选）**：用 tree-sitter 按函数 / 类 / 方法边界切分——语义内聚，每块就是完整可读单元。

**字符分块（兜底）**：LangChain RecursiveCharacterTextSplitter，按字符长度 + 分隔符。适用于不支持 AST 的语言（如早期的 Solidity）或解析失败时的 fallback。

> [!tip] 降级链原则
> AST 失败时不应抛错卡死整个 pipeline，而应自动 fallback 到字符切分。详见 [[ai-agent-plugin-patterns]]。

### 2. 检索策略

**单一向量召回不够用**——concept "用户登录" 能匹配语义，但精确符号 "validateJWT" 需要 sparse 召回。

claude-context 用 Dense + Sparse + RRF 三件套，详见 [[hybrid-search-rrf]]。

### 3. 增量同步

代码库不是静态的——每次修改都全量重建索引不现实。用内容指纹（[[merkle-dag-fingerprint|Merkle DAG]]）只重建变化的文件。

## 关键超参数

| 参数 | 典型值 | 影响 |
|------|--------|------|
| chunkSize | 2500 字符 | 太小召回多碎片，太大单 chunk 信息混杂 |
| chunkOverlap | 300 字符 | 边界处函数被切两半时仍能召回 |
| embeddingBatch | 100 | 流式批处理，避免内存爆炸 |
| collectionLimit | 450000 chunks | 向量库单 collection 上限保护 |

## 与 Agent 记忆检索的关系

代码语义检索 ≈ [[agent-memory|Agent 记忆]]检索的**特化形式**：

- 共同点：都是"语义检索 + 结构化字段 + 增量同步"
- 差异：代码检索的"数据源"是文件，记忆的"数据源"是工具调用日志
- 启示：两套系统的引擎层完全可以共用，只是 Splitter 不同

## 适用场景

- 大型 monorepo 给 AI Agent 加导航能力
- 代码搜索引擎（替代 Sourcegraph 的 LLM 版本）
- API 文档语义查询
- 跨项目代码复用发现

## 参考

- [[src-claude-context-architecture]]
