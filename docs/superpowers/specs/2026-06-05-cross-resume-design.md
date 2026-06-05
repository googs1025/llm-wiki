# Cross Resume 需求与设计文档

日期：2026-06-05
状态：待用户评审

## 摘要

Cross Resume 是一个本地优先的多 Agent 上下文接续工具。它帮助用户在 Claude Code、Codex、OpenCode 等编码 Agent 之间迁移工作上下文，把历史对话、项目状态、用户诉求、关键决策、约束条件和待办事项提炼成结构化的上下文简报。

第一版的主要体验不是新的终端 TUI，而是在当前 Agent 对话中显式调用 `/cross-resume`。CLI 和 MCP server 是底层能力，供 skills、slash command、command wrapper 或 Agent 指令模板调用。

## 产品目标

用户经常在多个编码 Agent 之间切换。Claude Code 的某个对话里可能已经包含了用户诉求、设计决策和未完成问题，但新开的 Codex 对话看不到这些上下文。用户不希望复制完整聊天记录，也不希望反复解释“上次做到哪里了”。

Cross Resume 要解决的问题是：

- 跨 Agent、跨会话恢复工作上下文。
- 把噪声大的历史记录压缩成可审阅、可检索、可加载的记忆。
- 在新对话中通过显式命令加载上下文，而不是默认无感注入。
- 通过 review 流程避免错误记忆污染长期状态。
- 本地优先存储，区分用户记忆和项目记忆。

## 第一版非目标

- 不把独立终端 TUI 作为主体验。
- 不自动把所有记忆注入每个 Agent 会话。
- 不默认静默采集完整聊天记录。
- 不做云同步、团队权限、企业审计。
- 不替代 [[claude-mem]] 或 [[agentmemory]] 这类完整长期记忆服务。
- 不把某个 Agent 的私有 transcript 格式作为唯一数据源。

## 项目位置

Cross Resume 应作为独立项目开发，不直接放在 `llm-wiki` 内实现。`llm-wiki` 只保存需求文档、架构分析和后续知识库条目。

默认实现目录：

```text
/Users/zhenyu.jiang/cross-resume
```

后续实现计划、源码、CLI、MCP server、adapter 和测试都应在这个独立目录中管理。

## 目标用户

- 同一项目中同时使用 Claude Code 和 Codex 的开发者。
- 经常新开 Agent 对话、需要快速恢复任务上下文的用户。
- 使用 `AGENTS.md`、`CLAUDE.md`、wiki、plans、commit log 沉淀项目知识的用户。
- 希望显式控制哪些信息进入长期记忆的高级用户。

## 核心概念

### 上下文简报

上下文简报是加载给 Agent 的最终内容。它不是原始聊天记录，而是经过整理的工作上下文。

简报可以包含：

- 当前目标
- 用户诉求
- 已确认决策
- 约束条件和偏好
- 当前项目状态
- 相关文件和命令
- 未解决问题
- 下一步行动
- 指向更深层记忆记录的引用

### 三层记忆

Cross Resume 把记忆分成三层：

- 用户记忆：跨项目的长期偏好、稳定约束和工作习惯。
- 项目记忆：当前仓库相关的事实、设计决策、架构笔记、任务状态。
- 会话记忆：某次 Agent 对话或某个任务阶段的 handoff 摘要。

默认上下文简报可以组合三层记忆，但用户可以选择只加载其中一部分。

### 候选记忆 Diff

`capture` 不直接写入长期记忆。它只生成候选记忆 diff，用户 review 后才能保存。

候选记忆类型包括：

- `goal`
- `decision`
- `constraint`
- `todo`
- `preference`
- `file-context`
- `risk`
- `question`
- `source`

## 主体验：Agent 对话内命令

主命令是 `/cross-resume`。

这个命令运行在 Claude Code、Codex 或其他支持的 Agent 对话里，通过 skill、slash command、command wrapper 或指令模板接入。交互用纯文本完成，不要求用户离开当前 Agent。

### 默认流程

用户输入：

```text
/cross-resume
```

Agent 回复：

```text
我找到这些可以恢复的上下文：

1. [当前项目] Cross Resume 设计
   updated 12m ago - 6 decisions - 3 todos - 4 files

2. [相似会话] Claude/Codex memory research
   updated 1h ago - claude-mem - agentmemory - mcp

3. [历史任务] NemoClaw ingest workflow
   updated 1h ago - wiki - ingest-codebase

回复编号加载，或输入关键词继续搜索。
```

用户回复：

```text
1 2
```

Agent 预览：

```text
将加载：
- 当前目标：设计一个多 Agent 上下文接续工具
- 已确认决策：CLI core、skill/command 入口、V1 MCP 只读
- 约束：本地优先、写入前 review、文件 + SQLite 存储
- 待确认问题：Agent 内 capture 与 resume 的具体交互

预计预算：standard，约 5k tokens。
回复 yes、edit、brief、full 或 cancel。
```

用户确认后，Agent 把返回的上下文简报作为当前对话的工作上下文。

### 支持的命令形态

```text
/cross-resume
/cross-resume current
/cross-resume brief
/cross-resume full
/cross-resume search "claude codex memory"
/cross-resume capture
/cross-resume capture "我们决定 V1 MCP 只读，写入走 CLI review。"
```

### 交互要求

- 必须能在 Agent 对话中完成，不依赖独立 TUI。
- 必须支持编号选择。
- 必须支持关键词搜索。
- 加载 standard 或 full 上下文前必须展示 preview。
- 必须支持 `brief`、`standard`、`full` 三档上下文预算。
- 默认优先加载当前项目相关记忆，避免跨项目噪声。

## Capture 体验

Capture 是把资料转成候选记忆 diff 的过程。

第一版支持三类来源：

1. 用户在当前 Agent 对话中显式提供的 notes。
2. 当前项目资料，例如 `AGENTS.md`、`CLAUDE.md`、docs、plans、git branch、recent commits、dirty diff 摘要。
3. Cross Resume adapter 维护的 Agent history index。

### Agent 内 Capture

用户输入：

```text
/cross-resume capture
```

Agent 回复：

```text
你想 capture 哪类上下文？

1. 当前对话总结
2. 当前项目状态
3. 搜索历史 Agent 记录
4. 粘贴 notes
```

用户可以回复编号，也可以直接提供文本。Agent 调用 CLI 或 MCP-backed command wrapper 生成候选记忆 diff。

### 历史搜索 Capture

Agent 可以在对话中展示类似搜索列表：

```text
搜索历史 Agent 记录。Filter: current project. Sort: updated.

1. 1h ago  $subagent-driven-development ... claude code 和 codex 上下文接续
2. 1h ago  $ingest-codebase https://github.com/NVIDIA/NemoClaw
3. 1h ago  安装 agentgateway 到 minikube
4. 1d ago  Review Kubernetes node-readiness-controller PR 201

回复编号 capture，或输入关键词继续搜索。
```

这不是终端 TUI，而是 Agent 对话内的文本选择协议。

### Review 后写入

Capture 完成后，Agent 展示候选 diff：

```text
候选记忆 diff：

[decision] V1 MCP 只读。
[decision] 主命令使用 /cross-resume。
[constraint] 主体验是 Agent 对话内文本交互，不是独立 TUI。
[todo] 定义 adapter history index 格式。

回复 accept、edit、reject 或 save-as-session-only。
```

只有用户接受的条目会写入记忆。

## CLI 需求

CLI 是稳定的本地核心。Agent 命令优先调用 CLI 能力。

必需命令：

```bash
cross-resume capture
cross-resume capture --notes "..."
cross-resume capture --file transcript.md
cross-resume capture --source claude-code
cross-resume review
cross-resume brief
cross-resume brief --target codex --level standard
cross-resume search "query"
cross-resume list
```

CLI 行为：

- `capture` 生成候选记忆 diff。
- `review` 接受、编辑、拒绝或路由候选记忆。
- `brief` 为目标 Agent 渲染上下文简报。
- `search` 检索相关记忆和历史记录。
- `list` 展示最近的 briefs、captures 和 memory records。

CLI 后续可以增加交互式终端模式，但第一版不依赖它。

## MCP 需求

MCP 不从零实现协议，优先使用官方开源 SDK。

优先 SDK：

- `modelcontextprotocol/typescript-sdk`
- `modelcontextprotocol/python-sdk`

第一版 MCP 只读。写入类操作仍然走 CLI 的 review 流程。

必需 MCP tool/resource：

- `get_context_brief`
- `search_context`
- `list_context_briefs`
- `get_project_summary`
- `get_user_preferences`

MCP 不应该把未 review 的候选记忆暴露为长期记忆。它可以在 Agent 请求 review 状态时展示 pending diff。

## Agent Adapter 需求

Adapter 负责把核心能力接入具体 Agent。

第一版内置 adapter：

- Claude Code
- Codex

后续 adapter：

- OpenCode
- Gemini CLI
- Cursor
- Hermes

Adapter 职责：

- 提供 `/cross-resume` 的 skill、command 或指令模板。
- 调用 CLI 或 MCP server。
- 把搜索结果、候选 diff 和 preview 渲染成 Agent 对话内文本。
- 当无法稳定读取 Agent 原生 transcript 时，维护轻量 history index。
- 如果读取 Agent 私有历史格式，必须标记为 best effort，不能作为唯一数据来源。

## 存储需求

第一版使用可读文件 + SQLite 索引。

### 项目存储

项目本地存储目录：

```text
.cross-resume/
  memories/
  sessions/
  candidates/
  briefs/
  history/
  index.sqlite
```

项目记忆可由用户选择是否提交到 git。

### 用户存储

用户全局存储目录：

```text
~/.cross-resume/
  memories/
  preferences/
  sessions/
  history/
  index.sqlite
```

用户记忆默认私有，不应自动写入项目目录。

### 文件格式

人类可读记录使用 Markdown + YAML frontmatter，或 Markdown 配 JSON sidecar。

SQLite 索引用于：

- record lookup
- 全文检索
- 当前项目路径过滤
- Agent 来源过滤
- created/updated 排序
- 候选记忆 review 状态管理

向量检索不是第一版必需项，但 schema 不应阻碍后续添加 embeddings。

## 数据模型

记忆记录字段：

```yaml
id: string
type: goal | decision | constraint | todo | preference | file-context | risk | question | source
scope: user | project | session
visibility: private | project
project_path: string
source_agent: claude-code | codex | opencode | manual | unknown
source_session_id: string
title: string
narrative: string
facts: string[]
files: string[]
tags: string[]
created_at: datetime
updated_at: datetime
confidence: high | medium | low
status: active | superseded | rejected | archived
```

候选记录额外字段：

```yaml
review_status: pending | accepted | edited | rejected
reviewed_at: datetime
reviewer_note: string
```

## LLM 压缩需求

LLM 压缩是可选增强。

没有配置 LLM 时：

- Capture 使用规则、模板、git 摘要和用户 notes。
- 仍然必须能生成可用的候选记忆 diff。

配置 LLM 后：

- LLM 负责提取 goals、decisions、constraints、todos、risks、file context。
- LLM 输出必须经过 schema 校验。
- LLM 不能直接写入长期记忆。
- 远端模型调用必须由用户显式配置 provider 后才允许。

这遵循 [[ai-as-compressor]] 模式：模型用于压缩噪声输入，不作为事实来源本身。

## 隐私与权限

第一版隐私策略：

- 本地优先存储。
- 默认不云同步。
- 默认不调用远端模型。
- 用户记忆和项目记忆分离。
- 用户记忆默认不写入 repo。
- 候选记忆必须 review 后才持久化。

第一版 visibility：

- `private`：用户全局私有，默认不写入项目目录。
- `project`：项目本地，可由用户选择是否通过 git 共享。

schema 预留未来的 `team` 和 `public` visibility。

## 上下文预算

简报渲染器支持三档：

- `brief`：约 1k 到 2k tokens，只包含当前目标、关键决策、下一步。
- `standard`：约 4k 到 8k tokens，默认用于多数 Agent handoff。
- `full`：约 12k 到 20k tokens，用于复杂任务恢复，包含更多历史依据和文件线索。

加载 `standard` 或 `full` 前，应展示估算 token 预算。

## 搜索与排序

搜索排序依据：

- 当前项目匹配度
- 最近更新时间
- 用户显式选择
- 记忆类型优先级
- 关键词匹配
- 来源 Agent 和 session 相关性

默认过滤：

- `/cross-resume` 默认搜索当前项目 + 用户记忆。
- `/cross-resume search` 优先搜索当前项目，需要时可扩展到 all projects。
- `/cross-resume current` 只加载当前项目和用户记忆。

## 端到端示例

1. 用户在 Claude Code 中讨论并决定：Cross Resume V1 使用 CLI core、Agent 内命令体验、MCP 只读。
2. 用户输入 `/cross-resume capture "我们决定命令叫 /cross-resume，主体验不是独立 TUI。"`
3. Agent 展示候选记忆 diff。
4. 用户接受候选条目。
5. 用户稍后在同一项目中打开 Codex，输入 `/cross-resume`。
6. Codex 列出相关上下文简报。
7. 用户选择 Cross Resume 设计简报。
8. Codex 预览即将加载的目标、决策、约束和待办。
9. 用户确认。
10. Codex 基于恢复后的上下文继续工作。

## 第一版验收标准

- 用户能在支持的 Agent 中输入 `/cross-resume` 并看到相关上下文选择。
- 用户能通过编号选择上下文简报，并在加载前看到 preview。
- 用户能在 Agent 对话内 capture 新决策或会话摘要。
- Capture 生成候选记忆 diff，而不是直接写长期记忆。
- Review 能接受或拒绝候选记忆。
- CLI 能生成 `brief`、`standard`、`full` 三档上下文简报。
- MCP 基于官方 SDK 暴露只读上下文检索能力。
- 项目记忆和用户记忆分开存储。
- 未配置 LLM provider 时系统仍可使用。
- 配置 LLM provider 后，提炼结果必须通过 schema 校验后再进入 review。

## 实现计划前待确认问题

- V1 CLI 和 MCP server 用 TypeScript 还是 Python？
- 项目目录 `.cross-resume/` 默认是否写入 `.gitignore`，还是拆成可共享和私有两个子目录？
- 各 Agent adapter 如何发现历史记录？无法读取原生 transcript 时，history index 的最小格式是什么？
- `/cross-resume capture` 默认先展示来源选择，还是默认 capture 当前对话 notes？
- Codex / Claude Code skill 收到 context brief 后，应如何把它作为当前工作上下文使用？

## 相关 Wiki

- [[agent-memory]]
- [[event-driven-memory-pipeline]]
- [[ai-as-compressor]]
- [[three-tier-search-protocol]]
- [[src-claude-mem-architecture]]
- [[src-agentmemory-architecture]]
