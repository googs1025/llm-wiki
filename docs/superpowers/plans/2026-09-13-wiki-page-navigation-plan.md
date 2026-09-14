# Wiki 页面阅读导航 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让生成的 wiki HTML 页面根据 `wiki/index.md` 的顺序显示上一页、推荐下一页和相关页面导航。

**Architecture:** 在 `build.py` 中解析索引链接，生成全局内容页序列；渲染每个页面时根据序列计算前后页面，并把导航 HTML 注入现有 shell。使用 CSS 完成响应式布局，Markdown 内容不增加导航标记。

**Tech Stack:** Python 3、标准库 `re/html`、现有 Markdown renderer、现有 CSS/HTML generator。

---

### Task 1: 为索引阅读序列增加解析器

**Files:**
- Modify: `wiki/html-assets/build.py`，位于 `Resolver` 与 wikilink preprocessing 附近

- [ ] **Step 1: 增加 `reading_order` 函数**

解析 `wiki/index.md` 的 `[[target]]`，通过 `Resolver.resolve()` 过滤为实际存在的内容页，去重并保留首次出现顺序；返回 `(category, stem)` 列表。

- [ ] **Step 2: 增加导航项计算函数**

实现 `navigation_for(category, stem, resolver, order)`：当前页存在于序列时返回前一项和后一项，否则返回两个 `None`；用 `resolver.href()` 生成相对于当前 category 的链接。

- [ ] **Step 3: 用最小 Python 断言验证顺序和边界**

运行：`python -m py_compile wiki/html-assets/build.py`

预期：退出码为 0。

### Task 2: 将导航注入 HTML shell

**Files:**
- Modify: `wiki/html-assets/build.py`，HTML shell 和页面渲染调用处

- [ ] **Step 1: 增加 `render_navigation`**

生成上一页、推荐下一页、返回索引和相关页面链接；对标题与 URL 做 HTML escape。无上一页或下一页时使用“返回索引”作为边界操作。

- [ ] **Step 2: 将 `{navigation_html}` 放在 footer 前**

扩展 `SHELL.format(...)` 参数，并确保 index/log 页面使用空导航或专用返回入口，不影响已有 sidebar、TOC、related 和 Markdown 源链接。

- [ ] **Step 3: 重新构建并检查代表页面**

运行：`uv run --quiet --with markdown wiki/html-assets/build.py`

检查：实体、概念、source、analysis 页面 HTML 都包含导航 class；首页不出现错误的 `../None` 链接。

### Task 3: 增加样式并验证完整输出

**Files:**
- Modify: `wiki/html-assets/style.css`

- [ ] **Step 1: 增加导航布局样式**

添加 `.page-navigation`、`.page-navigation a`、`.page-navigation .previous`、`.page-navigation .next` 与 `.page-navigation .recommended` 样式；窄屏下使用 grid/flex 换行，不改变现有主题变量。

- [ ] **Step 2: 重新生成 HTML**

运行：`uv run --quiet --with markdown wiki/html-assets/build.py`

预期：输出 `Done. wrote ...`，且构建不覆盖标记为 hand-crafted 的页面。

- [ ] **Step 3: 做静态验证**

运行：`git diff --check`；`rg -l 'page-navigation' wiki/html/entities wiki/html/concepts wiki/html/sources wiki/html/analysis | wc -l`。

预期：diff 无空白错误，生成内容页均能找到导航标记；最后检查 `git status --short`，保留用户已有改动。
