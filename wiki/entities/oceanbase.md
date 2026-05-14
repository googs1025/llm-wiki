---
title: OceanBase
tags: [entity, database, distributed-db, vector-db, stub]
date: 2026-05-14
sources: []
related: [powermem]
---

# OceanBase

蚂蚁集团开源的企业级分布式关系数据库；原生支持 **向量索引**（HNSW / IVF 系列）、**全文检索**（多种 parser）、**图存储**，是 [[powermem]] 的默认后端。Apache 2.0。

> [!todo] Stub 占位
> 详细架构（OBServer / OBProxy / 副本协议 / Paxos / LSM 存储引擎）TBD。当前主要价值在于作为 [[powermem]] 的存储基座出现。
>
> 待补充：
> - OceanBase 4.x 向量能力（`pyobvector` SDK）
> - 嵌入式 SeekDB（`pyseekdb`，v1.1.0 让 PowerMem 零依赖）
> - 与同类 vector-aware DB（pgvector / Milvus）的对照
