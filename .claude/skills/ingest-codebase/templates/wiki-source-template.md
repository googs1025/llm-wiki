<!--
  TEMPLATE: wiki/sources/src-<slug>-architecture.md
  HAS frontmatter (it IS a wiki page).
  RULE: every ASCII diagram below MUST be copied byte-identical from the matching raw/ file.
       After writing, run: grep -c "│" raw/<slug>-architecture-analysis.md wiki/sources/src-<slug>-architecture.md
       The two counts should be close (within ~5%). If they diverge a lot, you accidentally compressed a diagram — redo.
-->

---
title: {{PROJECT_NAME}} 架构与设计思路分析
tags: [architecture, {{DOMAIN_TAG_1}}, {{DOMAIN_TAG_2}}]
date: {{DATE_YYYY_MM_DD}}
sources: [{{SLUG}}-architecture-analysis.md]
related: [[{{PROJECT_NAME}}], [[{{RELATED_CONCEPT_1}}]], [[{{RELATED_CONCEPT_2}}]]]
---

# {{PROJECT_NAME}} 架构与设计思路分析

> 原文：`raw/{{SLUG}}-architecture-analysis.md` · 仓库：{{REPO_URL_OR_PATH}} · 分析版本 {{VERSION_OR_COMMIT}}

## 一句话定位

{{蒸馏自 raw 的"一句话定位"。这里允许（鼓励）替换实体为 [[wikilink]]，使 Obsidian 能形成图谱。}}

## 核心架构图

```
{{原样复制 raw/ 中的核心架构 ASCII 图。禁止重绘、禁止改写、禁止替换为表格。}}
```

## 模块分层

| 层 / 模块 | 职责 |
|----------|------|
| {{Tier 1}} | {{responsibility}} |
| {{Tier 2}} | {{responsibility}} |

{{wiki 版的表可以省略 "主要文件 / 目录" 列，因为 wiki 读者不一定关心源码路径；想了解去看 raw/。}}

## 关键数据流

```
{{原样复制 raw/ 中的关键数据流 ASCII 图。}}
```

## 设计决策与哲学

- **{{决策 1}}**：{{1-2 句，带 [[wikilink]]}}
- **{{决策 2}}**：{{...}}
- **{{决策 3}}**：{{...}}

<!-- 可选：从 raw/ 的"关键组件深入"里挑 1-2 个最核心的，简化后保留。
     其它组件深入不在 wiki 重复 —— 读者需要细节去看 raw/。 -->

## 相关页面

- [[{{ENTITY_OR_CONCEPT_1}}]]
- [[{{ENTITY_OR_CONCEPT_2}}]]
- [[{{ENTITY_OR_CONCEPT_3}}]]
