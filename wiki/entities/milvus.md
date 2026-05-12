---
title: Milvus
tags: [vector-database, llm-infra, zilliz, open-source]
date: 2026-05-12
sources: [src-claude-context-architecture]
related: [[claude-context]], [[hybrid-search-rrf]]
---

# Milvus

开源向量数据库，由 Zilliz 开发。同时支持 **dense 向量**（语义匹配）和 **sparse 向量**（BM25-like 精确匹配），并内置 RRF（Reciprocal Rank Fusion）等混合检索重排策略。

## 在 claude-context 中的角色

[[claude-context]] 把代码块向量化后存入 Milvus collection（同时存 dense + sparse 双字段），检索时调用 `hybridSearch` 一次查询返回融合排名。详见 [[hybrid-search-rrf]]。

## 部署形态

| 形态 | 说明 |
|------|------|
| 本地 Milvus | 自托管，需要部署 etcd / MinIO 等依赖 |
| Zilliz Cloud | Milvus 托管服务，配置 `MILVUS_ADDRESS` + `MILVUS_TOKEN` 即可 |
| Milvus-RESTful | 单文件 HTTP API 适配，轻量场景 |

claude-context 通过 `VectorDB` 接口抽象同时支持后两者。

## 关键限制

- 单 collection 容量有实际上限 → claude-context 用 `CHUNK_LIMIT = 450000` 做保护，超限切状态而非崩溃
- Hybrid search 的 `nprobe` 和 `drop_ratio` 参数影响精度 / 速度权衡

## 参考

- [[src-claude-context-architecture]]
