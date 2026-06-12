---
title: llm-wiki
tags: [entity, repo-wiki, knowledge-base, code-intelligence]
date: 2026-06-12
sources: []
related: [[repo-wiki-generation]], [[code-graph]], [[deepwiki-open]], [[code-semantic-search]]
---

# llm-wiki

llm-wiki 是当前这个人工维护的个人知识库项目，用 `raw/` 保存来源材料，用 `wiki/sources/`、`wiki/entities/`、`wiki/concepts/` 和 `wiki/analysis/` 维护可链接的技术知识图谱。

## 架构边界

它和 [[deepwiki-open]] 都面向 repo/wiki 生成，但 llm-wiki 更偏人工 curated 架构页、跨项目选型地图和概念层维护；deepwiki-open 更偏自动生成、交互式问答和产品化 repo wiki。

## 选型判断

适合沉淀高信噪比架构理解、项目对比和选型判断；不适合完全自动化覆盖大量仓库。
