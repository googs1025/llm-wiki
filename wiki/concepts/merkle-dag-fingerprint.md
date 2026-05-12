---
title: Merkle DAG 文件指纹
tags: [design-pattern, incremental-sync, content-addressing, llm-infra]
date: 2026-05-12
sources: [src-claude-context-architecture]
related: [[claude-context]], [[code-semantic-search]], [[agent-memory]]
---

# Merkle DAG 文件指纹

用内容哈希构建的 DAG 做"我之前处理过这个吗"的判定。[[claude-context]] 用它做大型代码库的**增量同步**。

## 朴素方案的问题

| 朴素方案 | 缺陷 |
|---------|------|
| mtime 时间戳 | git checkout 改 mtime 但内容没变；clone 全部新 mtime |
| 版本号 | 谁去维护版本号？跨设备同步会乱 |
| 全量重建 | 千万行 repo 一次半小时 |

## Merkle DAG 怎么解决

```
file1.ts ──── hash(content) ──┐
file2.ts ──── hash(content) ──┼──► hash(子节点 hash 列表) ──► root
file3.ts ──── hash(content) ──┘
```

- 文件级哈希 → 目录级哈希 → 整库 root hash
- 任何文件内容变化 → 一路 hash 传播到 root
- root 没变 → 整库没变 → 跳过同步
- root 变了 → 二分定位变化的子树 → 精准重建

[[claude-context]] 的实现持久化到 `~/.context/merkle/<md5(path)>.json`，5 分钟后台轮询比对。

## 增量同步流程

```
旧 Merkle root ≠ 新 Merkle root
       │
       ▼
checkForChanges() → {added, removed, modified}
       │
   ┌───┴────┬─────────────┐
   ▼        ▼             ▼
 删向量   重新分块+嵌入  再写入
       │
       ▼
 持久化新快照
```

## 可迁移到的场景

> 不只是文件，**任何需要"我之前处理过这个吗"的场景都适用**：

| 场景 | 指纹的内容 |
|------|----------|
| 代码索引增量 | 文件内容 hash |
| 对话历史去重 | message chunk hash |
| 知识库增量更新 | doc hash |
| 工具调用结果缓存 | input 序列化 hash |
| Agent 记忆"已学习"标记 | observation 内容 hash |

> [!tip] 关键原则
> 用内容 hash 而非时间戳/版本号——**内容变了 hash 就变，自动失效旧缓存**。这是 content-addressable storage 的核心思想（Git、IPFS 都基于此）。

## 与 claude-mem 内容哈希去重的关系

[[claude-mem]] 也用内容哈希做 observation 去重（UNIQUE `generation_key` + `ON CONFLICT`），但只用了"hash 一个对象"的最简形式。Merkle DAG 进一步把哈希组织成树状结构，让"局部变化只触发局部重建"成为可能。

## 参考

- [[src-claude-context-architecture]]
