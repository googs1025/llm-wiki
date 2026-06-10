# llm-wiki 知识地图页面优化设计

日期：2026-06-10
状态：待用户评审

## 摘要

本次优化把 `llm-wiki` 的静态 HTML 从“Markdown 长列表渲染”提升为“知识地图入口 + 稳定阅读器”。首页承担快速定位主题、搜索页面、发现阅读路径和查看最近更新的任务；文章页承担深度阅读、扫描目录、识别标签和跳转相关页面的任务。

项目仍保持本地优先、纯静态输出和低依赖。实现只扩展现有 `wiki/html-assets/build.py` 与 `wiki/html-assets/style.css`，不引入 SPA 框架，不改变 `raw/` 原始资料，不改变 Markdown wiki 的 frontmatter 和 `[[wikilink]]` 维护规则。

## 产品目标

用户阅读这个知识库时通常处在研究和维护状态：在本地浏览器里快速定位 AI Agent、长期记忆、运行时隔离、LLM serving、Kubernetes 平台工程等主题，然后进入长文深读或横向对比。

优化目标是：

- 让 `wiki/html/index.html` 成为真正的知识地图首页，而不是完整索引 Markdown 的直接展开。
- 保留搜索能力，并让搜索结果更容易扫描。
- 在首页显式展示主题入口、页面总量、分类计数、推荐阅读路径、最近更新和待建页面摘要。
- 改善文章页公共组件，使长文、表格、代码块、标签、目录、相关页和页脚更稳定。
- 保持生成流程可重复、可审查、可长期维护。

## 非目标

- 不把项目改造成 React/Vue/Svelte 等重前端应用。
- 不引入服务端、数据库、远程搜索或构建缓存。
- 不改动 `raw/` 下的原始材料。
- 不改变 `wiki/*.md` 的知识库维护规范。
- 不做营销式 landing page、大 hero、装饰性卡片网格或复杂动效。
- 不强制重写已有内容分类；首页主题入口可以先基于当前标签和标题规则生成。

## 设计原则

### 工具优先

这是个人研究工具，不是宣传页。界面应偏工作台：信息密度可以高，但层级必须清楚。视觉重点放在搜索、主题入口、阅读路径和正文可读性上。

### 静态优先

所有数据在构建阶段生成到 HTML 中。浏览器端只保留轻量交互：主题切换、搜索过滤、目录 active 状态。没有运行时网络请求。

### 渐进增强

如果 JavaScript 不运行，首页仍应能展示主要入口和链接；文章页仍能阅读正文。搜索和目录高亮属于增强能力。

### 内容不被装饰遮挡

深色主题可保留，但对比度、行宽、间距和表格扫描优先级高于视觉氛围。设计不使用渐变文字、重阴影、玻璃拟态或纯装饰动效。

## 首页信息架构

首页由现有 `wiki/index.md` 内容和构建脚本收集的数据共同生成。

### 顶部栏

保留现有 sticky topbar，但做得更像工具导航：

- 左侧：`llm-wiki` 品牌与首页链接。
- 中间：当前页面上下文，例如 `知识地图`。
- 右侧：操作时间线链接、主题切换按钮。
- 窄屏：隐藏次要 meta，保留首页、日志、主题切换。

### 首屏摘要

首屏不使用营销 hero，而是紧凑的知识库概览：

- 标题：`llm-wiki`
- 副标题：个人 LLM / AI Agent / 云原生 / 推理基础设施知识库。
- 搜索框：搜索标题、标签、分类和简短描述。
- 统计条：总页面数、实体页、概念页、源文件摘要、分析页。

### 主题入口

首页展示 4 个主要主题入口，第一版用规则生成或手工映射：

- AI Agent / Memory
- Agent Runtime / Sandbox
- LLM Inference / Serving
- Kubernetes / Cloud Native

每个主题入口显示：

- 主题名称。
- 一句说明。
- 相关页面数量。
- 2 到 4 个关键链接，优先分析页和核心概念页。

主题入口不使用重复装饰图标网格。它们是导航模块，重点是可点击内容。

### 推荐阅读路径

保留 README 中的阅读路径语义，把它变成首页模块：

- AI Agent / Memory
- Agent Runtime / Sandbox
- LLM Inference / Serving
- Kubernetes / Cloud Native

每条路径包含 1 到 3 个入口链接和简短说明。该模块可以由 `wiki/index.md` 的结构生成，也可以在构建脚本中维护一份轻量主题配置。

### 最近更新

从 `wiki/log.md` 和页面 frontmatter `date` 生成最近更新列表：

- 显示最近 6 到 10 条。
- 每条包含日期、操作类型、标题或目标页面。
- 链接到对应页面时优先链接 source / analysis / entity / concept；无法解析时链接到日志页。

### 待建页面摘要

保留 `wiki/index.md` 里的待建页面信息，但首页只显示摘要：

- 按当前大类展示少量待建主题。
- 提供跳转到原索引待建页面段落的链接。
- 不让待建列表压过已建知识地图。

## 搜索设计

搜索仍是客户端过滤，但搜索索引更结构化。

每个索引项包含：

- `title`
- `href`
- `category`
- `tags`
- `description`：优先取首页索引条目中的短描述，取不到则为空。
- `date`

搜索行为：

- 输入为空时不显示结果，避免首页首屏拥挤。
- 命中标题、标签、分类、描述。
- 结果显示标题、分类、标签、描述摘要。
- 最多显示 30 条。
- 结果列表使用稳定行高和可点击区域，避免内容跳动。

## 文章页设计

文章页继续由 `build_page()` 生成，但页面外壳和公共组件更明确。

### Page Header

正文顶部包含：

- 标题。
- 日期和来源摘要。
- 标签 chips。

标题不使用大幅 display 字体，保持产品工具感。副标题和 tags 应紧凑，避免把正文推到太靠下。

### 正文区域

正文最大阅读宽度应控制在适合长文的范围内。含表格、代码块、ASCII 图和 Mermaid 图时允许横向滚动，不挤压文字。

建议行为：

- 普通段落使用 65 到 75ch 视觉行宽。
- 表格、代码块、图表可以突破段落行宽并横向滚动。
- `h2` 有清楚分隔，但不使用厚重侧边条。
- `h3` 与前后段落间距更紧凑，便于技术文档扫描。

### TOC

桌面端保留右侧 sticky TOC：

- 宽度适中，目录层级最多展示 h2/h3。
- active 状态使用 accent 色和轻背景，不只依赖颜色变化。
- 超长标题截断或换行，不撑破侧栏。

窄屏隐藏 TOC，正文单列阅读。

### Related

frontmatter `related` 生成的相关页面应从普通列表升级为紧凑链接组：

- 已存在页面显示为普通链接。
- 缺失页面保留缺失状态，但视觉不应像错误告警。
- 相关页面模块放在正文末尾、页脚之前。

### Callout

现有 callout 使用粗 `border-left`，需要改为完整边框或轻背景，避免侧边色条模式。warning / ok / info 通过标题、图标文字或背景 tint 区分。

### 表格和代码

表格：

- 表头更清晰。
- 行 hover 保留但要克制。
- 小屏允许横向滚动。

代码块：

- 保留 monospace。
- inline code 和 block code 有明确区分。
- 代码块边框、背景和正文背景对比足够。

### Footer

页脚保留 Markdown 源链接，但减少视觉噪声：

- 页面类型。
- Markdown 源链接。
- 生成器信息可放在首页或 title，不必每篇文章都强调。

## 构建脚本设计

`build.py` 保持单文件脚本，不拆出复杂构建系统。

新增或调整的内部结构：

- `SearchEntry` 或等价 dict：统一搜索数据。
- `collect_pages()`：收集 entities / concepts / sources / analysis 页面元数据。
- `build_topic_groups()`：根据主题配置和 tags/title 匹配生成主题入口。
- `parse_log_entries()`：从 `wiki/log.md` 解析最近更新。
- `render_site_index()`：将首页拆成小的 render 函数，减少一个巨型 f-string 的复杂度。

主题配置可以先放在脚本常量中，避免新增配置文件：

```python
TOPIC_GROUPS = [
    {
        "title": "AI Agent / Memory",
        "tags": ["agent-memory", "ai-agent", "mcp", "claude-code"],
        "preferred": ["agent-memory-project-map", "ai-agent-frameworks-map"],
    },
]
```

这足够支撑当前知识库。后续如果主题更多，再考虑独立配置文件。

## 样式系统设计

继续使用 `wiki/html-assets/style.css`，但整理 token 和模块类。

### Token

保留暗色默认、亮色可切换。颜色策略是克制产品工具：

- 背景：深色 neutral。
- Surface：内容区和交互控件的轻微层级。
- Accent：用于主要链接、搜索 focus、active TOC、关键导航。
- State：warning、ok、missing link。

不使用单一大面积蓝紫渐变；accent 只用于状态和导航。

### 模块类

新增或整理这些类：

- `.home-shell`
- `.home-hero`
- `.home-search`
- `.stats-strip`
- `.topic-grid`
- `.topic-card`
- `.reading-paths`
- `.recent-updates`
- `.missing-summary`
- `.page-header`
- `.page-meta`
- `.related-panel`
- `.table-wrap`

卡片半径控制在 8 到 12px。边框和阴影不叠加做装饰，主要用背景层级和边框组织信息。

## 响应式设计

桌面：

- 首页可以使用两列或多列模块。
- 文章页是正文 + 右侧 TOC。

平板：

- 首页主题入口从 4 列降到 2 列。
- 统计条可换行。
- 文章页 TOC 可隐藏或移动到正文顶部，第一版采用隐藏。

手机：

- topbar meta 收缩。
- 首页模块单列。
- 搜索结果全宽。
- 正文 padding 减小。
- 表格、代码和图表横向滚动。
- 按钮和链接触控区域不小于 40px 高度。

## 可访问性

- 文本对比度满足 WCAG AA：正文至少 4.5:1，大号标题至少 3:1。
- 搜索框有明确 placeholder 和 focus 样式。
- 主题切换按钮保留 `aria-label`。
- active TOC 不只依赖颜色，增加背景或字重。
- 链接 hover 不应是唯一可见状态，focus-visible 需要清晰。
- 减少或不使用动画；如使用 transition，遵守 `prefers-reduced-motion`。

## 验证计划

实现完成后需要运行：

- `./wiki/html-assets/build.py`
- 检查 `wiki/html/index.html` 正常生成。
- 用本地静态页面或开发服务器打开首页和至少两类文章页。
- 桌面宽度检查首页、搜索结果、文章 TOC。
- 手机宽度检查 topbar、首页单列、正文、表格/代码横向滚动。
- 检查浏览器控制台无 JavaScript 错误。
- `git status --short` 确认只包含预期文件。

## 实施边界

第一轮实现只触及：

- `wiki/html-assets/build.py`
- `wiki/html-assets/style.css`
- 由构建脚本生成的 `wiki/html/**/*.html`
- `.gitignore` 中的 `.superpowers/` 忽略项

不触及：

- `raw/`
- `wiki/*.md` 内容正文
- `AGENTS.md`
- README 的内容结构

## 风险与处理

### 首页生成逻辑过重

风险：把太多规则塞进 `build.py` 会让脚本难维护。

处理：主题配置保持小而显式；复杂推断不做。优先使用已有 tags、标题和已知 analysis 页。

### 搜索索引转义问题

风险：当前搜索 JSON 用字符串拼接，标题中有特殊字符时可能破坏 JavaScript。

处理：实现时改用 Python `json.dumps()` 生成搜索索引，避免手工拼 JSON。

### 手工 HTML 被覆盖

风险：构建脚本会跳过没有自动生成 marker 的手工 HTML 页面。

处理：保留现有 `should_write()` 规则，不使用 `--force` 覆盖手工页面，除非用户明确要求。

### 首页和 Markdown 索引不一致

风险：首页模块化后，和 `wiki/index.md` 的完整列表可能出现差异。

处理：首页使用 `wiki/index.md` 和实际页面目录作为数据源；完整内容仍可从 Markdown 索引维护。首页是导航摘要，不替代知识源。

## 用户评审点

请重点确认：

- 首页是否应以四个主题入口为主。
- 最近更新是否应来自 `wiki/log.md`，还是只看页面 frontmatter 日期。
- 文章页 TOC 在手机端是否可以隐藏。
- 第一版是否接受主题配置写在 `build.py` 常量中。
