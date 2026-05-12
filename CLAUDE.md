# LLM Wiki - 个人知识库

## 领域

通用个人知识库（可按需调整为特定领域）

## 目录结构

```
raw/            # 不可变原始素材（只读）
  assets/       # 图片附件
wiki/           # LLM 生成和维护的知识页
  index.md      # 内容索引
  log.md        # 操作时间线
  entities/     # 实体页（人物、组织、项目、工具）
  concepts/     # 概念页（方法论、技术原理、理论）
  sources/      # 源文件摘要页
  analysis/     # 查询产出的分析页
```

## 页面格式

每个 wiki 页面必须包含 YAML frontmatter：

```yaml
---
title: 页面标题
tags: [tag1, tag2]
date: YYYY-MM-DD
sources: [source1.md, source2.md]
related: [相关页面的 wikilink]
---
```

正文中使用 `[[wikilink]]` 做交叉引用，确保 Obsidian 能识别链接关系。

## Ingest 工作流

当用户要求摄入新的源文件时：

1. 读取 `raw/` 中的目标源文件
2. 与用户讨论关键要点
3. 在 `wiki/sources/` 创建摘要页（命名：`src-简短标题.md`）
4. 更新或创建相关的 `wiki/entities/` 和 `wiki/concepts/` 页面
5. 确保所有新页面和被更新的页面之间有 `[[wikilink]]` 交叉引用
6. 更新 `wiki/index.md`（添加新条目、调整分类）
7. 追加一条到 `wiki/log.md`，格式：`## [YYYY-MM-DD] ingest | 标题`

注意：
- 一次摄入一篇源文件，保持与用户的互动
- 如果新内容与已有页面存在矛盾，在两个页面中都标注 `> [!warning] 矛盾` callout
- raw/ 中的文件绝不修改
- **源摘要页禁止压缩原文中的 ASCII 图表**：架构图、流程图、目录树、SQL Schema 等高密度可视化结构必须原样复制保留，不可重绘、不可简化为表格。表格只用于补充图表无法表达的速读清单（如"参数→默认值"）。冗长的文字叙述才适合压成要点。
- 自查：`grep -c "│" raw/xxx.md wiki/sources/src-xxx.md` 两个数字应接近

## Query 工作流

当用户提出问题时：

1. 先读 `wiki/index.md` 定位相关页面
2. 读取相关 wiki 页面，综合信息回答
3. 回答中引用来源：`参见 [[页面名]]`
4. 如果回答具有长期价值，询问用户是否存入 `wiki/analysis/`

## Lint 工作流

当用户要求健康检查时，逐项检查：

- [ ] 矛盾：不同页面中的冲突声明
- [ ] 孤立页：没有任何入链的页面
- [ ] 缺失引用：正文提到但没有 `[[wikilink]]` 的概念
- [ ] 过时内容：被更新源文件取代的旧声明
- [ ] 数据缺口：值得深入但缺乏源材料的主题
- [ ] 建议：推荐下一步可以摄入的材料或探索的问题

## 约定

- 文件名使用小写英文 + 短横线（如 `kubernetes-scheduling.md`）
- 标签使用小写英文（如 `cloud-native`, `ai-infra`）
- 每次操作完成后 commit，commit message 格式：`ingest: 标题` / `query: 问题摘要` / `lint: 日期`
- 优先更新已有页面，不要随意创建新页面（除非确实是新实体/概念）
