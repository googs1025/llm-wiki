# LLM Wiki - Personal Knowledge Base

## Domain

General personal knowledge base. Adjust the domain when the wiki becomes focused on a narrower technical area.

## Directory Structure

```
raw/            # Immutable source material, read-only
  assets/       # Image attachments
wiki/           # LLM-generated and maintained knowledge pages
  index.md      # Content index
  log.md        # Operation timeline
  entities/     # Entity pages: people, organizations, projects, tools
  concepts/     # Concept pages: methods, principles, theories
  sources/      # Source summary pages
  analysis/     # Analysis pages produced from queries
```

## Page Format

Every wiki page must contain YAML frontmatter:

```yaml
---
title: Page title
tags: [tag1, tag2]
date: YYYY-MM-DD
sources: [source1.md, source2.md]
related: [related wikilink]
---
```

Use `[[wikilink]]` cross-references in page bodies so Obsidian can recognize the link graph.

## Ingest Workflow

When the user asks to ingest a new source:

1. Read the target source file under `raw/`.
2. Discuss the key points with the user.
3. Create a summary page under `wiki/sources/`, named `src-short-title.md`.
4. Update or create related pages under `wiki/entities/` and `wiki/concepts/`.
5. Ensure new and updated pages have `[[wikilink]]` cross-references.
6. Update `wiki/index.md` with new entries and category changes.
7. Append one entry to `wiki/log.md` in this format: `## [YYYY-MM-DD] ingest | Title`.

Notes:

- Ingest one source at a time and keep the workflow interactive with the user.
- If new content conflicts with existing pages, mark the conflict in both pages with a `> [!warning] Conflict` callout.
- Never modify files under `raw/`.
- Source summary pages must not compress ASCII diagrams from the original source. Architecture diagrams, flowcharts, directory trees, SQL schemas, and other dense visual structures must be copied as-is. Do not redraw them or simplify them into tables. Use tables only as supplemental quick-reference material when diagrams cannot express the point well.
- Self-check ASCII diagram preservation with `grep -c "│" raw/xxx.md wiki/sources/src-xxx.md`; the two counts should be close.

## Query Workflow

When the user asks a question:

1. Read `wiki/index.md` first to locate relevant pages.
2. Read the related wiki pages and synthesize the answer.
3. Cite wiki sources in the answer with `See [[Page Name]]`.
4. If the answer has long-term value, ask whether it should be saved under `wiki/analysis/`.

For project understanding, architecture comparison, or technology selection questions:

- Re-check the relevant GitHub repositories before analysis, even when wiki pages or source summaries already exist.
- Prefer primary evidence from the current repository: README, docs, architecture diagrams, package/module layout, examples, config files, recent releases/tags, and notable recent commits.
- Compare multiple existing projects side by side when useful, focusing on architecture boundaries, core abstractions, control/data flow, storage/runtime dependencies, extension points, operational model, maturity, and trade-offs.
- Make the selection guidance explicit: best fit, avoid-if conditions, migration/adoption cost, and what to verify next.
- Distinguish fresh GitHub observations from older ingested source notes when they differ or when confidence depends on current repository state.

## Lint Workflow

When the user asks for a health check, inspect these items:

- [ ] Contradictions: conflicting claims across pages
- [ ] Orphan pages: pages with no inbound links
- [ ] Missing references: concepts mentioned in text but not linked with `[[wikilink]]`
- [ ] Outdated content: old claims superseded by newer sources
- [ ] Data gaps: important topics that lack source material
- [ ] Recommendations: next sources or research questions worth ingesting

## Conventions

- Use lowercase English filenames with hyphens, for example `kubernetes-scheduling.md`.
- Use lowercase English tags, for example `cloud-native` and `ai-infra`.
- Commit after each completed operation. Commit message formats: `ingest: Title`, `query: Question summary`, `lint: YYYY-MM-DD`.
- Prefer updating existing pages over creating new pages unless the topic is truly a new entity or concept.
