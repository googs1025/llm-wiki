# Design: `ingest-codebase` Skill

- **Date**: 2026-05-13
- **Status**: Approved by user (brainstorm phase)
- **Scope**: A project-local skill for the `llm-wiki` repository that turns a code repository (local path or GitHub URL) into a wiki-grade architecture analysis with two-layer output and automatic index maintenance.

## 1. Motivation

The author maintains an LLM-themed personal wiki under `~/llm-wiki/`. Two project-architecture analyses already exist (`claude-mem`, `claude-context`) and more are planned. Each one currently requires:

1. Running `code-explorer` (or an ad-hoc deep read) on the repo
2. Hand-writing a detailed analysis into `raw/<project>-architecture-analysis.md`
3. Hand-distilling that into `wiki/sources/src-<project>-architecture.md` (with frontmatter, `[[wikilinks]]`, preserved ASCII art)
4. Updating `wiki/index.md` and `wiki/log.md`
5. Optionally creating new `wiki/entities/` pages
6. Committing under the convention `ingest: <title>`

This is repetitive, easy to drift on (e.g., accidentally compressing ASCII diagrams in step 3), and the structure has stabilized enough to codify.

## 2. Goals & Non-Goals

### Goals
- One slash command — `/ingest-codebase <local-path-or-github-url>` — produces a complete, conventionally-structured analysis in the wiki.
- Reuse `code-explorer` for deep code reading rather than reimplementing.
- Enforce the "preserve ASCII diagrams" convention recorded in user memory.
- Maintain `wiki/index.md` and `wiki/log.md` automatically.
- Stop short of irreversible actions: never auto-commit, never auto-create entity pages without confirmation.

### Non-Goals
- Replace or wrap the generic ingest workflow defined in `CLAUDE.md` (the new skill is *one specialization* — for source-code repos).
- Replace `code-explorer` (the skill calls it; it is not duplicated).
- Generate SVG / Mermaid / draw.io diagrams (ASCII only, matching existing convention).
- Support non-GitHub remotes (GitLab/Bitbucket deferred).
- Diff / version-compare repeated ingests of the same project (overwrite or `-v2` suffix instead).

## 3. Decisions (locked during brainstorm)

| # | Question | Decision |
|---|---|---|
| Q1 | Input source | **D**: local path **or** GitHub URL (auto `git clone` to `/tmp/`) |
| Q2 | Output layers | **B**: two layers — detailed `raw/` file + distilled `wiki/sources/` file |
| Q3 | Section template | **B**: recommended sections (must-have backbone + optional add-ons) |
| Q4 | Must-have sections | One-line definition · ASCII architecture diagram · module-tier table · key data flow · design philosophy |
| Q5 | Relationship to `code-explorer` | **C**: orchestration — the skill calls `code-explorer` for Phase 2 analysis |
| Q6 | Automation depth | **C**: auto-update index/log + propose commit; do **not** auto-commit or auto-create entity pages |
| Q7 | Name / location / trigger | `ingest-codebase`, project-local at `~/llm-wiki/.claude/skills/`, `user-invocable: true` |
| Q7-fu | Global access | Project-local plus user-managed shell alias (`alias ingest='cd ~/llm-wiki && claude code'`) — not a skill concern |

## 4. Skill Layout

```
~/llm-wiki/.claude/skills/ingest-codebase/
├── SKILL.md                          # frontmatter + 4-phase instructions
├── templates/
│   ├── raw-analysis-template.md      # backbone for raw/<project>-architecture-analysis.md
│   └── wiki-source-template.md       # backbone (+ frontmatter) for wiki/sources/src-<project>-architecture.md
└── scripts/
    ├── clone_or_locate.sh            # resolve input → absolute repo path
    ├── derive_name.sh                # derive project slug (github owner/repo → repo, local → dirname)
    └── check_existing.sh             # idempotency check for raw/ + wiki/sources/
```

Analysis primitives (language detection, entry-point discovery, git-log context) are **not** reimplemented — those live in `code-explorer/scripts/` and are reached transitively when `code-explorer` is invoked during Phase 2.

## 5. Execution Flow (4 Phases)

### Phase 1 — Locate

1. Parse the slash argument.
2. If it looks like a GitHub URL (`github.com/<owner>/<repo>` or `git@github.com:...`), run `git clone` into `/tmp/ingest-codebase-<short-hash>/`. The clone is **not** removed after analysis — keeping it lets the user re-run cheaply. The user can clear `/tmp` whenever they wish.
3. If a local path, validate it exists and is a git repository (warn if not — analysis still proceeds, but commit-history hints will be absent).
4. Derive project slug:
   - GitHub URL → `<repo>` (e.g., `thedotmack/claude-mem` → `claude-mem`)
   - Local path → final path component
   - If the derived slug is generic (`repo`, `code`, `src`, `main`) → `AskUserQuestion` for a clearer name.
5. Idempotency check: if `raw/<slug>-architecture-analysis.md` or `wiki/sources/src-<slug>-architecture.md` already exists → `AskUserQuestion` with three options:
   - **Overwrite** (re-analyze, replace files)
   - **Skip** (abort)
   - **`-v2` suffix** (treat as a fresh re-analysis of an evolved version)

### Phase 2 — Deep Analysis (delegates to `code-explorer`)

1. Invoke the `code-explorer` skill via the `Skill` tool with these parameters:
   - Mode: **deep** (`整个项目、架构、多模块关系`)
   - Focus: overall architecture + module relationships
   - Output detail: standard with ASCII art
2. Constrain `code-explorer`'s output by instructing it to organize findings under the must-have section backbone (see §6) plus any optional sections the project warrants.
3. Persist the final analysis to `raw/<slug>-architecture-analysis.md`.

This phase is the only "AI-heavy" step; everything else is mechanical.

### Phase 3 — Distill to Wiki

1. Read the freshly-written `raw/<slug>-architecture-analysis.md`.
2. Produce `wiki/sources/src-<slug>-architecture.md` per the contract in §7:
   - Add frontmatter (`title`, `tags`, `date`, `sources`, `related`).
   - **Copy every ASCII diagram verbatim** (no redraw, no table-substitution). Self-check: `grep -c "│"` on both files; the counts should be close. If not, redo the affected section.
   - Replace 5–10 core entity names with `[[wikilinks]]`.
   - Trim "key component deep-dives" to the 1–2 most central — the rest stay only in `raw/`.

### Phase 4 — Index Maintenance & Commit Proposal

1. **Auto-update** `wiki/index.md`: add a new entry under the appropriate category.
2. **Auto-append** `wiki/log.md`: `## [YYYY-MM-DD] ingest | <项目名> 架构`.
3. **Entity-page detection**: scan distilled `[[wikilinks]]`. For each link with no matching file under `wiki/entities/` or `wiki/concepts/`, `AskUserQuestion`: *"Create entity page for `[[X]]`? (yes / yes-stub / no)"*. Never create silently.
4. `git add` everything new or modified.
5. Print a proposed commit message (`ingest: <项目名> 架构`) and stop. The user runs the commit.

## 6. Section Templates

### Must-have backbone (raw + wiki, in order)

1. **一句话定位** — 2–3 sentence positioning, threaded with `[[wikilinks]]` in the wiki version.
2. **核心架构图** — full ASCII diagram. **No substitutions.**
3. **模块分层** — table + brief prose per tier.
4. **关键数据流** — at least one end-to-end flow, ASCII preferred.
5. **设计决策与哲学** — bullet list of non-obvious choices and their rationale.

### Recommended-optional add-ons

- 关键组件深入解读
- 与同类对比
- 性能 / 资源开销
- 安全模型
- 代码统计

Selection rule for optional sections: include only when the project naturally surfaces the topic (e.g., a CLI tool rarely needs "network protocol"; a distributed system always does).

## 7. File Contracts

### `raw/<slug>-architecture-analysis.md`

- **No frontmatter** — matches existing `raw/claude-mem-architecture-analysis.md` and `raw/claude-context-architecture-analysis.md`; `raw/` is immutable source material, not a wiki page.
- Length: typically 500–1500 lines.
- Headings follow the backbone in §6.

### `wiki/sources/src-<slug>-architecture.md`

```yaml
---
title: <项目名> 架构与设计思路分析
tags: [architecture, <项目领域 tags>]
date: YYYY-MM-DD
sources: [<slug>-architecture-analysis.md]
related: [[<项目名>], [[相关概念1]], [[相关概念2]]]
---

# <项目名> 架构与设计思路分析

> 原文：`raw/<slug>-architecture-analysis.md` · 仓库：<URL or path> · 分析版本 <vX.Y.Z if known>

## 一句话定位
...

## 核心架构图
```
<ASCII diagram, copied verbatim from raw>
```

## 模块分层
...

## 关键数据流
...

## 设计决策与哲学
...

## 相关页面
- [[...]]
```

## 8. Error Handling & Edge Cases

| Scenario | Behavior |
|---|---|
| Invalid GitHub URL / `git clone` failure | Fail Phase 1 immediately with a clear error. Phase 2 must not run. |
| Repo too large (> 5000 files **or** > 200 MB) | `AskUserQuestion` to confirm before continuing. User may pass `--include=<subdir>` to narrow scope. |
| Repo is not a code project (only docs/markdown) | Detect heuristically (no recognized language files). Suggest the generic ingest workflow in `CLAUDE.md`; exit. |
| Output files already exist | `AskUserQuestion`: overwrite / skip / `-v2` suffix. |
| Ambiguous project slug | `AskUserQuestion` to disambiguate. |
| ASCII diagram drift during distillation | Self-check `grep -c "│"` on raw vs wiki; if counts diverge, redo the affected section. |
| `gh` missing or `git clone` needs auth | Surface the error; suggest `gh auth login` or a local path fallback. |

## 9. Explicit YAGNI (won't do)

- ❌ Auto-commit (commits are semantic; user decides).
- ❌ Replacement or bypass of `code-explorer` (Phase 2 always calls it).
- ❌ Version-diffing repeated ingests.
- ❌ Persisting cloned source under `raw/` or git (clone lives in `/tmp/`, never tracked).
- ❌ Non-ASCII diagrams (SVG / Mermaid / draw.io).
- ❌ Silent entity-page creation.
- ❌ GitLab / Bitbucket / generic git remotes.

## 10. Relationship to Existing Skills & Workflows

| Component | Role | Relationship |
|---|---|---|
| `code-explorer` | Read & explain code | **Called** by `ingest-codebase` during Phase 2. |
| `architecture-diagram` | Produce polished architecture diagrams | **Not used**. ASCII-only convention. |
| Generic ingest workflow (`CLAUDE.md`) | Ingest arbitrary documents | `ingest-codebase` is the source-code-repo specialization. |
| User memory: "Ingest 摘要必须保留原文 ASCII 图表" | Diagram-preservation rule | Enforced via §7 contract and §5 Phase 3 self-check. |

## 11. Success Criteria

- A user can run `cd ~/llm-wiki && claude code` then `/ingest-codebase https://github.com/thedotmack/claude-mem` and end up with: (a) a fresh raw file, (b) a wiki-conformant `wiki/sources/` page, (c) updated `index.md` and `log.md`, (d) a proposed commit message — **without** writing any markdown by hand.
- Re-running on the same repo prompts for overwrite / skip / `-v2`, never silently clobbers.
- ASCII diagrams in `wiki/sources/` are byte-identical to those in `raw/`.
- Re-running `code-explorer` for unrelated tasks remains unchanged (the skill only adds a caller, never modifies `code-explorer` itself).
