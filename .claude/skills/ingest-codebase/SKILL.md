---
name: ingest-codebase
description: |
  把一个代码仓库（本地路径或 GitHub URL）摄入到 llm-wiki 知识库。
  触发场景：
  - "/ingest-codebase <本地路径或 GitHub URL>"
  - "把这个仓库摄入到 wiki" / "分析这个项目并入库"
  - "为 <项目名> 写一份架构页"
  - "ingest 这个项目"
  注意：本 skill 只在工作目录是 ~/llm-wiki 时可用。源码理解阶段会调用 code-explorer skill。
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Skill
  - AskUserQuestion
---

# Ingest Codebase

你是 llm-wiki 项目源码摄入的执行者。把一个代码仓库变成两份产物：
1. `raw/<slug>-architecture-analysis.md`（详细分析，约 500-1500 行）
2. `wiki/sources/src-<slug>-architecture.md`（蒸馏摘要 + frontmatter + wikilink，200-400 行）

同时维护 `wiki/index.md` 和 `wiki/log.md`，最后提议 commit。**绝不自动 commit。**

## 前置约束

- 必须在 `~/llm-wiki/` 工作目录下运行。如果 `$PWD` 不是 llm-wiki 根（找不到 `CLAUDE.md` 或 `wiki/index.md`），立即报错并让用户 `cd ~/llm-wiki`。
- 输出的所有 ASCII 图必须保持原样（呼应 user memory: "Ingest 摘要必须保留原文 ASCII 图表"）。
- 不替换、不绕过 `code-explorer`。Phase 2 必须经由 Skill 工具调用它。

---

## Phase 1 — 定位

### Step 1.1: 解析参数

从用户消息提取第一个非空参数（路径或 GitHub URL）。若用户没给参数，用 `AskUserQuestion` 询问。

### Step 1.2: 推导项目 slug

```bash
.claude/skills/ingest-codebase/scripts/derive_name.sh "<input>"
```

- 退出码 0：slug 可用，记下来。
- 退出码 1：slug 太通用（`repo`/`code`/`src`/…）。用 `AskUserQuestion` 问用户希望用什么名字。
- 退出码 2：输入无效。报错并退出。

### Step 1.3: 解析为绝对路径（必要时 clone）

```bash
REPO_PATH=$(.claude/skills/ingest-codebase/scripts/clone_or_locate.sh "<input>")
```

- 退出码 0：`$REPO_PATH` 是本地绝对路径。
- 退出码 2：clone 失败 / 路径不存在。报错并退出，**不进入 Phase 2**。

### Step 1.4: 幂等检查

```bash
WIKI_ROOT="$PWD" .claude/skills/ingest-codebase/scripts/check_existing.sh "<slug>"
```

- 退出码 0：干净，继续。
- 退出码 1：有冲突文件。用 `AskUserQuestion` 让用户选：
  - "overwrite" — 删除旧文件后重新分析
  - "skip"      — 终止本次 ingest
  - "v2-suffix" — slug 改为 `<slug>-v2`（再跑一次 check_existing，递增到无冲突的版本号）

### Step 1.5: 规模 / 类型预检

```bash
# 粗略文件数
FILE_COUNT=$(find "$REPO_PATH" -type f -not -path '*/.git/*' | wc -l | tr -d ' ')
# 粗略大小（MB）
SIZE_MB=$(du -sm "$REPO_PATH" 2>/dev/null | cut -f1)
```

- `FILE_COUNT > 5000` 或 `SIZE_MB > 200` → `AskUserQuestion`，让用户确认或指定 `--include=<subdir>` 子目录。
- 用 `Glob` 看仓库是否有可识别语言的文件（`*.py`/`*.ts`/`*.go`/`*.rs`/`*.java`/`*.js`/`*.rb`/`*.c`/`*.cpp`/`*.kt` 等）。若只有 markdown / 文档，提示走 CLAUDE.md 通用 ingest 流程，本 skill 退出。

---

## Phase 2 — 深度分析（委托 code-explorer）

### Step 2.1: 先 Read 模板，把骨架装进上下文

调用 `Read` 工具读取：

```
.claude/skills/ingest-codebase/templates/raw-analysis-template.md
```

这是写 raw 文件时必须遵循的骨架（5 个 must-have 章节 + optional 章节）。

### Step 2.2: 调用 code-explorer

用 `Skill` 工具调用 code-explorer。**注意 args 是普通字符串，shell 变量不会被展开**——必须把 Step 1.3 记下的实际绝对路径直接拼进字符串：

```
Skill(
  skill: "code-explorer",
  args: "deep mode on <把 $REPO_PATH 的实际值替换在这里，例如 /Users/foo/projects/claude-mem>; focus: overall architecture & module relationships; output: standard with ASCII art"
)
```

> 替换约定：本 skill 文档中所有 `<slug>` / `<input>` / `$REPO_PATH` 字面量都是占位符。**真正调用工具时，你（orchestrator）负责把这些占位符替换为 Phase 1 记下的实际值。** Bash 块里的 `$REPO_PATH` 由 shell 自然展开，是例外。

### Step 2.3: 重新组织成 must-have 骨架

code-explorer 的 deep 模式有自己的输出格式（`核心功能摘要 / 架构流程图 / 关键逻辑拆解 / 深度洞察 / 建议深入探索`），**与本 skill 的 must-have 骨架不一致**。

你（orchestrator，**不是** code-explorer）负责把 code-explorer 的产出**重新组织**成 Step 2.1 读到的 `templates/raw-analysis-template.md` 骨架：

1. 一句话定位（蒸馏自"核心功能摘要"）
2. 核心架构图（取"架构流程图"里的 ASCII）
3. 模块分层（表 + 散文，从"关键逻辑拆解"提取）
4. 关键数据流（至少 1 个端到端，ASCII）
5. 设计决策与哲学（蒸馏自"深度洞察"）

按项目特性可追加 optional 章节：关键组件深入解读 / 与同类对比 / 性能 / 安全模型。

### Step 2.4: 写入 raw 文件

把上一步重新组织的内容用 `Write` 工具写入：

```
raw/<slug>-architecture-analysis.md
```

（其中 `<slug>` 替换为 Phase 1 记下的实际 slug。）

`raw/` 文件**不加 frontmatter**（参考 `raw/claude-mem-architecture-analysis.md` 风格）。

---

## Phase 3 — 蒸馏到 wiki

### Step 3.1: 先 Read wiki 模板

调用 `Read` 工具读取：

```
.claude/skills/ingest-codebase/templates/wiki-source-template.md
```

这是 wiki source 页的 frontmatter + 章节骨架。

### Step 3.2: 生成 wiki source 页

再 `Read` 一次刚写好的 `raw/<slug>-architecture-analysis.md`（`<slug>` 替换为实际 slug），然后按 wiki 模板蒸馏，用 `Write` 写入：

```
wiki/sources/src-<slug>-architecture.md
```

蒸馏规则：

- frontmatter 必填：`title` / `tags` / `date` / `sources` / `related`
- **所有 ASCII 图原样复制**，禁止重绘、禁止替换为表格
- 拣选 5-10 个核心实体，写成 `[[wikilink]]`（项目名本身、关键概念、依赖项目、相关方法论）
- raw 的"关键组件深入"在 wiki 中只保留 1-2 个最核心的，其它读者去看 raw

### Step 3.3: ASCII 自查

```bash
raw_bars=$(grep -c "│" "raw/<slug>-architecture-analysis.md" || echo 0)
wiki_bars=$(grep -c "│" "wiki/sources/src-<slug>-architecture.md" || echo 0)
echo "raw: $raw_bars | wiki: $wiki_bars"
```

若 `wiki_bars` 显著少于 `raw_bars`（差距超过 ~5%），说明某张 ASCII 图被压缩了。回到 Step 3.2 重做受影响章节。注意：`raw_bars` 为 0 时说明 raw 文件本来就没有 ASCII 图，跳过本步。

---

## Phase 4 — 索引维护 + commit 提议

### Step 4.1: 更新 `wiki/index.md`

Read 现有 `wiki/index.md`，把新条目添加到合适分类下：

```markdown
- [[src-<slug>-architecture]] — <项目一句话定位简版>
```

如果不确定归类，`AskUserQuestion` 让用户选分类（或新建分类）。

### Step 4.2: 追加 `wiki/log.md`

```markdown
## [<YYYY-MM-DD>] ingest | <项目名> 架构
```

### Step 4.3: 实体页检测（交互式）

对 wiki source 里出现的每个 `[[X]]`：

```bash
ls wiki/entities/ wiki/concepts/ 2>/dev/null | grep -i "<X>" || echo "missing"
```

如果某个 `[[X]]` 既不在 `wiki/entities/` 也不在 `wiki/concepts/`，用 `AskUserQuestion` 问：
- "yes"     — 创建完整实体页（从 raw/wiki 信息提炼一页）
- "yes-stub"— 创建占位页（frontmatter + 一句话 + TODO）
- "no"      — 跳过

**不要静默创建任何实体页。**

### Step 4.4: 暂存所有变更

```bash
git add raw/<slug>-architecture-analysis.md \
        wiki/sources/src-<slug>-architecture.md \
        wiki/index.md \
        wiki/log.md \
        $(任何新增的 entity/concept 页)
```

### Step 4.5: 提议 commit message

打印（不执行）：

```bash
git commit -m "ingest: <项目名> 架构与设计思路"
```

告诉用户："已暂存所有变更。请确认 commit message 后由你执行 `git commit`。"

---

## YAGNI 守则

绝不做：

- ❌ 自动 `git commit`
- ❌ 重写 / 绕过 code-explorer 的分析逻辑
- ❌ 生成 SVG / Mermaid / draw.io 图
- ❌ 静默创建实体页
- ❌ 对重复 ingest 做 diff（用户已经在 Step 1.4 选了 overwrite / skip / v2）
- ❌ 把 clone 出来的源码副本放进 `raw/` 或加入 git tracking（clone 留在 `/tmp/`）
- ❌ 处理 GitHub 以外的 git 远端（GitLab/Bitbucket 暂不支持）

## 失败处理

| 场景 | 处理 |
|------|------|
| `$PWD` 不是 llm-wiki | 立即报错让用户 cd 到 llm-wiki，不做任何写操作 |
| `git clone` 失败 / URL 无效 | Phase 1 退出，提示用户 `gh auth login` 或改用本地路径 |
| code-explorer 调用失败 | 报错，不写 raw/，让用户排查 |
| ASCII 自查不通过且 3 次重做仍失败 | 把 raw 文件的对应章节原文粘贴到 wiki，标记 `> [!warning] 自动蒸馏失败，已粘贴原文`，让用户人工调整 |
