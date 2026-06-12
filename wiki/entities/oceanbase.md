---
title: OceanBase
tags: [entity, database, vector-search, memory]
date: 2026-06-12
sources: [powermem-architecture-analysis.md]
related: [[powermem]], [[hybrid-search-rrf]], [[agent-memory]]
---

# OceanBase

OceanBase 是分布式数据库，在当前知识库中主要作为 [[powermem]] 的优先存储后端出现：PowerMem 用它承载向量、全文、稀疏和图检索相关能力，并通过适配层保留替换为其他存储的可能。

## 架构边界

在 PowerMem 场景里，OceanBase 是 memory storage / retrieval backend，不是 Agent runtime。记忆系统的工作流、艾宾浩斯衰减、provider 适配和 MCP/CLI/API 入口仍由 [[powermem]] 自身负责。

## 选型判断

适合需要把 Agent 记忆、向量检索和数据库能力放在同一个可运维存储底座上的场景。若只做本地轻量 memory，可对比 SQLite / SeekDB 路径。
