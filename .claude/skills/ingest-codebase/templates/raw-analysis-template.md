<!--
  TEMPLATE: raw/<slug>-architecture-analysis.md
  This file has NO frontmatter (raw/ is immutable source material, not a wiki page).
  Replace {{...}} placeholders. Keep all ASCII diagrams as raw text inside fenced blocks.
  Section order below is the MUST-HAVE backbone — do not reorder, do not omit.
  Optional sections may be appended after "设计决策与哲学" if the project warrants them.
-->

# {{PROJECT_NAME}} 架构与设计思路分析

> 仓库：{{REPO_URL_OR_PATH}} · 分析日期：{{DATE_YYYY_MM_DD}} · 版本：{{VERSION_OR_COMMIT}}

## 一句话定位

{{2-3 句话，说清"它是什么 / 解决什么问题 / 关键手段"。这一段后面会蒸馏进 wiki/sources/ 并加 [[wikilink]]。}}

## 核心架构图

```
{{完整 ASCII 架构图：用框线字符 (─│┌┐└┘├┤┬┴┼) 画出主要组件、数据/控制流方向、外部依赖。
保持原始格式，禁止替换为表格或缩略。}}
```

## 模块分层

| 层 / 模块 | 主要文件 / 目录 | 职责 |
|----------|----------------|------|
| {{Tier 1}} | {{paths}} | {{responsibility}} |
| {{Tier 2}} | {{paths}} | {{responsibility}} |

{{表后可补 1-3 段散文，说明分层的关键约束（例：哪一层禁止做什么）。}}

## 关键数据流

至少 1 个端到端流程，优先 ASCII：

```
{{flow diagram: 触发 → 各组件 → 副作用 / 输出}}
```

{{补充说明：超时、错误传递、回退路径。}}

## 设计决策与哲学

- **{{决策 1}}**：{{为什么这么做，舍弃了什么。引用源码位置 path/to/file.ext:NN-MM 加深说服力。}}
- **{{决策 2}}**：{{...}}
- **{{决策 3}}**：{{...}}

<!-- 以下为 optional 章节，按需保留；不需要的删掉。 -->

## 关键组件深入解读

### {{Component A}}（path/to/file.ext）

{{200-400 字的源码 walk-through：核心数据结构、关键函数、与其他组件的接口。}}

### {{Component B}}

{{...}}

## 与同类对比

| 维度 | {{此项目}} | {{同类 A}} | {{同类 B}} |
|------|-----------|------------|------------|
| ... | ... | ... | ... |

## 性能 / 资源开销

{{冷启动 / 稳态 / 峰值 / 存储占用。有数据就有数据，没有就标 "未测"。}}

## 安全模型

{{攻击面、信任边界、密钥/凭证存储位置、已知风险。}}
