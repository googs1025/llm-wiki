---
title: Repo Wiki Generation
tags: [concept, repo-wiki, code-intelligence, documentation, llm]
date: 2026-06-12
sources: [deepwiki-open-architecture-analysis.md]
related: [[deepwiki-open]], [[code-graph]], [[code-semantic-search]], [[code-semantic-search-rag-map]]
---

# Repo Wiki Generation

Repo wiki generation 指从代码仓库自动生成结构化知识库、架构说明、模块页面和问答入口的工作流。它介于 Code RAG、文档生成和代码理解产品之间。

## 代表项目

[[deepwiki-open]] 是当前 wiki 中的代表：Next.js UI + Python API/tools + LiteLLM routing，把 repo 自动生成可浏览、可问答的 wiki。

## 与 llm-wiki 的关系

本 llm-wiki 更偏人工维护的知识图谱和选型地图：source、entity、concept、analysis 分层明确。repo wiki generator 更偏自动化生成和交互式浏览。两者可以互补：自动生成初稿，人工维护跨项目概念和选型判断。

## 选型提示

如果目标是快速给一个仓库生成文档，选 repo wiki generator；如果目标是跨多个项目做长期可演化的技术地图，仍需要人工 curated concept/entity 层。
