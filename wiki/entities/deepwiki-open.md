---
title: deepwiki-open
tags: [entity, repo-wiki, code-intelligence, llm, nextjs]
date: 2026-06-12
sources: [deepwiki-open-architecture-analysis.md]
related: [[repo-wiki-generation]], [[code-graph]], [[code-semantic-search]], [[llm-wiki]]
---

# deepwiki-open

开源 DeepWiki / repo wiki generator，用 Next.js UI、Python API/tools 和 LiteLLM multi-provider routing，把仓库自动生成可问答 wiki。详见 [[src-deepwiki-open-architecture]]。

## 架构边界

deepwiki-open 不是代码编辑 agent，而是 repo understanding / documentation generator。它与本 llm-wiki 工作流形成镜像：都把 source 转成可导航知识库，但 deepwiki-open 更产品化、自动化和交互式。

## 选型判断

适合自动生成 repo wiki、问答和浏览。若需要可审计的手工 curated 架构页、选型地图和跨项目概念层，llm-wiki 这种人工维护知识库仍更可控。
