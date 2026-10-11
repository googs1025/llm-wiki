# vLLM Operations Lifecycle and Runbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a versioned vLLM operational-lifecycle guide and an executable production runbook covering startup, preload, readiness, drain, sleep/wake, weight updates, failure recovery, and shutdown.

**Architecture:** Keep state/resource ownership in `vllm-operational-lifecycle.md` and mutable commands/checklists in `vllm-production-operations-runbook.md`. Reuse existing reliability/operator concepts for cross-project principles, pin current vLLM release and main evidence separately, and extend the existing request-to-CUDA test harness plus generated HTML/graph contracts.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, ASCII diagrams, Python `unittest`, GitHub API/official vLLM documentation, `uv`, current wiki HTML/PDF builder, Git.

**Spec:** `docs/superpowers/specs/2026-10-11-vllm-operations-lifecycle-design.md`

## Global Constraints

- Create exactly two new Analysis pages: `wiki/analysis/vllm-operational-lifecycle.md` and `wiki/analysis/vllm-production-operations-runbook.md`.
- Do not modify `raw/` or rewrite historical Source snapshots as current facts.
- Resolve and record both the latest stable vLLM release/tag and current official upstream main SHA at implementation time.
- Label version-sensitive capabilities as `release-documented`, `main-documented`, `development-endpoint`, `integration-dependent`, or `external-control-plane`.
- Do not present `vllm preload`, Sleep levels, partial wake, weight reload, or HTTP endpoints as universally available across releases/backends.
- Explicitly state that default preload `zero_copy` mode is incompatible with Sleep Mode weight offload because the daemon owns the IPC allocations.
- Keep process health, engine readiness, Kubernetes readiness, and router membership as separate states.
- Every lifecycle action must state its in-flight request policy and must not imply transparent continuation after tokens were emitted.
- Multi-rank sleep/wake/reload is an all-participant operational boundary; partial rank success leaves the serving group unready.
- Use `text` fences for diagrams; keep wikilinks in prose outside diagram fences.
- Use the latest main builder's declared `uv` dependencies for tests/builds, preserve hand-crafted HTML, and prove the second build is identical.
- Continue on `feature/inference-request-to-cuda` / PR #49; use normal commits, fetch/rebase latest `origin/main` before final push if remote main advances, and update with `--force-with-lease` only when rebase requires it.

## Review Focus

- A main-only Preload feature is mistaken for stable-release behavior: both pages must show stable/main evidence separately and tag every Preload command `main-documented`; pinned by Tasks 1–2.
- An operator combines `ipc_cache` `zero_copy` with Sleep Mode: lifecycle matrix and runbook precheck must reject that combination and explain daemon ownership; pinned by Tasks 1–2.
- A Pod stays route-ready while paused, sleeping, loading, or draining: readiness sections must require removal from routing before lifecycle mutation and re-admission only after warm/readiness checks; pinned by Tasks 1–3.
- In-flight or partially streamed requests are lost during sleep/restart: every destructive lifecycle runbook must select abort/wait/keep/drain semantics and state that emitted-token streams cannot transparently resume; pinned by Task 2.
- One TP/PP/DP/EP rank fails sleep/wake/reload while peers succeed: diagnostics must mark the whole serving group unready and require coordinated rollback/restart; pinned by Tasks 1–2.

---

## File Map

**Create**

- `wiki/analysis/vllm-operational-lifecycle.md` — lifecycle state machine, resource ownership, version boundaries, and control-plane interfaces.
- `wiki/analysis/vllm-production-operations-runbook.md` — commands, Kubernetes ordering, diagnostics, rollback, and verification.

**Modify**

- `wiki/html-assets/test_request_to_cuda.py` — lifecycle/runbook/backlink/generated-output contracts.
- `wiki/entities/vllm.md` — concise operations entry and current version boundary.
- `wiki/concepts/llm-serving-reliability.md` — vLLM drain/sleep/restart instantiation.
- `wiki/concepts/model-serving-operator.md` — controller-to-engine lifecycle interface.
- `wiki/analysis/vllm-gpu-execution-path.md` — worker/allocator to operational lifecycle link.
- `wiki/analysis/llm-inference-request-lifecycle.md` — asynchronous operations/control-path link.
- `wiki/index.md` — two Analysis entries and ordered operations reading path.
- `wiki/log.md` — one durable query entry.
- Generated `wiki/html/**` output from the current builder.

## Shared Test Interfaces

Extend `RequestToCudaWikiTest` and preserve its existing helpers. Add:

- `OPS_SLUGS = ("vllm-operational-lifecycle", "vllm-production-operations-runbook")`
- `test_vllm_operational_lifecycle_contract`
- `test_vllm_operations_runbook_contract`
- `test_vllm_operations_navigation_and_backlinks`
- Extend `test_generated_output` for both HTML pages and graph edges.

All new-page tests reuse `assert_common_page_contract`, assert `date: 2026-10-11`, complete frontmatter, balanced fences, no placeholders, fixed official URLs/SHAs, and at least one inbound link after Task 3.

### Task 1: vLLM Operational Lifecycle Page

**Files:**

- Create: `wiki/analysis/vllm-operational-lifecycle.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: official vLLM release notes/tag, upstream main Sleep/Preload docs, EngineCore/GPUWorker/SleepModeBackend, weight-cache daemon and IPC loader.

**Interfaces:**

- Consumes: existing `[[vllm]]`, `[[vllm-gpu-execution-path]]`, `[[llm-serving-reliability]]`, and the L0–L8 arrow/location conventions.
- Produces: canonical lifecycle states, action names, evidence labels, resource matrix, and Preload/Sleep ownership language consumed by Task 2.

- [ ] **Step 1: Pin release and upstream evidence**

Use `gh release view --repo vllm-project/vllm --json tagName,publishedAt,url` and `gh api repos/vllm-project/vllm/commits/main`. Record stable tag/date and main SHA. Confirm `.codegraph/` before searching any local vLLM clone; local code is navigation only unless its commit equals the pinned upstream. Verify fixed-commit paths for Sleep docs/API/Core/Worker/backend and Preload docs/CLI/daemon/IPC loader.

- [ ] **Step 2: Add the failing lifecycle contract**

Add `test_vllm_operational_lifecycle_contract`. Require headings `版本与证据边界`, `Lifecycle 状态机`, `Process / Engine / Worker / Daemon 所有权`, `普通启动与 Preload 启动`, `Warmup 与 Ready`, `Drain 与 Pause`, `Sleep Level 0/1/2`, `Partial Wake 与 Reload Weights`, `Preload Cache Modes`, `LoRA 生命周期`, `Shutdown 与 Restart`, `资源状态矩阵`, `失败与恢复边界`, `外部控制面接口`; at least seven ASCII diagrams; all five evidence labels; pinned release/main identifiers; and terms `zero_copy`, `ipc_cache`, `weights`, `kv_cache`, `scheduling`, `CUDA Graph`, `NCCL`.

- [ ] **Step 3: Verify RED**

Run the test through `uv run` with the builder's declared Markdown/PDF dependencies.

Expected: FAIL because `vllm-operational-lifecycle.md` is absent.

- [ ] **Step 4: Write the lifecycle page**

Implement the spec's state machine and resource matrix. Explain normal disk load versus daemon-backed `ipc_cache`, startup profiling/warmup/readiness, sleep levels and pause modes, partial wake ordering, level-2 reload flow, daemon fingerprints/cache modes, LoRA state, multi-rank coordination, shutdown, and control-plane ownership. Every main-only/development/integration-dependent statement carries its label near the claim.

- [ ] **Step 5: Verify GREEN and full existing suite**

Run the targeted lifecycle test, then the entire `test_request_to_cuda.py` suite in the same `uv` environment.

Expected: targeted PASS; existing tests remain green.

- [ ] **Step 6: Commit**

```bash
git add wiki/analysis/vllm-operational-lifecycle.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Add vLLM operational lifecycle"
```

### Task 2: vLLM Production Operations Runbook

**Files:**

- Create: `wiki/analysis/vllm-production-operations-runbook.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: Task 1 evidence table/state vocabulary plus current official server, health, Sleep, Preload, weight reload, LoRA, distributed and shutdown documentation/code.

**Interfaces:**

- Consumes: lifecycle states/actions/resource ownership from Task 1.
- Produces: common operation template `PRECHECK → REMOVE FROM ROUTING → DRAIN/POLICY → EXECUTE → VERIFY → RECOVER/ROLLBACK → POSTCHECK` used by Task 3 links.

- [ ] **Step 1: Trace operational entry points and failure signals**

Confirm current CLI/API names for normal serve, preload daemon health, `ipc_cache`, sleep/wake/is-sleeping/release-KV/reload, LoRA management, server health, process signals, and distributed worker lifecycle. Separate dev-only endpoints from production-safe control paths and record fallback/mismatch log signals.

- [ ] **Step 2: Add the failing runbook contract**

Add `test_vllm_operations_runbook_contract`. Require headings `使用方式与版本标签`, `启动前检查`, `普通启动`, `Preload Daemon`, `Health、Startup 与 Readiness`, `安全 Drain`, `Sleep Level 0`, `只释放 KV Cache`, `Sleep Level 1`, `Sleep Level 2 与权重更新`, `Wake 与恢复流量`, `LoRA 运维`, `Graceful Shutdown`, `Kubernetes Rolling Upgrade`, `故障诊断树`, `回滚`, `Post-operation Checklist`; at least five ASCII diagrams; exact operation template labels; `VLLM_SERVER_DEV_MODE=1`; and warnings for zero-copy/Sleep, emitted-token streams, and partial-rank failure.

- [ ] **Step 3: Verify RED**

Run the targeted runbook test in the `uv` environment.

Expected: FAIL because the runbook page is absent.

- [ ] **Step 4: Write the runbook page**

For every operation include purpose, evidence label/version, preconditions, commands or control-plane actions, successful observations, failure observations, rollback, request semantics, and resource verification. Add single-node examples and Kubernetes-neutral ordering; do not invent a CRD or assume one external platform.

- [ ] **Step 5: Verify GREEN and full suite**

Run the targeted runbook test and the full test file.

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add wiki/analysis/vllm-production-operations-runbook.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Add vLLM production operations runbook"
```

### Task 3: Connect vLLM Operations to the Wiki

**Files:**

- Modify: `wiki/entities/vllm.md`
- Modify: `wiki/concepts/llm-serving-reliability.md`
- Modify: `wiki/concepts/model-serving-operator.md`
- Modify: `wiki/analysis/vllm-gpu-execution-path.md`
- Modify: `wiki/analysis/llm-inference-request-lifecycle.md`
- Modify: `wiki/index.md`
- Modify: `wiki/log.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`

**Interfaces:**

- Consumes: both new slugs and Task 2 operation template.
- Produces: inbound links, ordered reading path, durable log entry, and layer-appropriate navigation without copied runbook content.

- [ ] **Step 1: Add the failing navigation/backlink contract**

Add `test_vllm_operations_navigation_and_backlinks`. Assert both new pages have inbound links outside themselves; `[[vllm]]` links both; reliability links the runbook; operator links lifecycle; engine/request analyses link lifecycle; Index contains both Analysis entries and exact order `[[vllm-operational-lifecycle]] → [[vllm-production-operations-runbook]]`; Log contains exactly one `## [2026-10-11] query | Add vLLM operations lifecycle and runbook` entry.

- [ ] **Step 2: Verify RED**

Run the navigation test.

Expected: FAIL because existing pages/index/log do not reference the operations pages.

- [ ] **Step 3: Update Entity, Concepts, and Analysis backlinks**

Add concise sections/links only: vLLM Entity owns the operations entry; reliability maps request failure/drain; model-serving-operator maps reconcile/readiness; GPU execution maps allocator resources; request lifecycle maps async operations. Preserve latest main content and evidence.

- [ ] **Step 4: Update Index and Log**

Add both Analysis entries and the ordered operations reading path near the request-to-CUDA path. Append the exact log heading and a concise summary distinguishing release/main/dev endpoints.

- [ ] **Step 5: Verify GREEN and commit**

Run the navigation test and full suite, then commit:

```bash
git add wiki/entities/vllm.md wiki/concepts/llm-serving-reliability.md wiki/concepts/model-serving-operator.md wiki/analysis/vllm-gpu-execution-path.md wiki/analysis/llm-inference-request-lifecycle.md wiki/index.md wiki/log.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Link vLLM operations into the wiki"
```

### Task 4: Generated HTML, Graph, and Full Integrity

**Files:**

- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Generate: both new Analysis HTML pages, affected Entity/Concept/Analysis HTML, Index/Log, graph, and navigation changes produced by the current builder.

**Interfaces:**

- Consumes: all Markdown and backlinks from Tasks 1–3.
- Produces: reproducible generated output and final evidence for PR update.

- [ ] **Step 1: Extend generated-output tests before building**

Extend `test_generated_output` or add `test_vllm_operations_generated_output`. Assert both HTML pages exist, contain text diagrams and required headings, contain no missing new wikilinks, all local href targets exist after removing query/fragment, graph contains both nodes plus lifecycle→runbook and vllm→both edges, and total new operations diagrams are at least 12. Extend raw/hand-crafted preservation checks without replacing the existing baseline.

- [ ] **Step 2: Verify RED**

Run the generated-output test before building.

Expected: FAIL because HTML/graph is absent or stale.

- [ ] **Step 3: Run Markdown/content tests**

Run the full test file before build.

Expected: only generated-output assertions fail; all Markdown contracts pass.

- [ ] **Step 4: Build twice and prove idempotence**

Run `./wiki/html-assets/build.py` in the latest main `uv` environment, hash `git diff -- wiki/html`, run again, and compare hashes.

Expected: both builds succeed, hand-crafted pages are skipped/preserved, and hashes match.

- [ ] **Step 5: Run final test/build/diff suite**

Run the complete unittest file, builder, Python compile check for the test, `git diff --check`, raw/hand-crafted preservation, and `git status --short`.

Expected: all tests PASS, builder is clean on rerun, and only scoped Markdown/test/generated files are changed.

- [ ] **Step 6: Inspect representative desktop/narrow pages**

Render and inspect lifecycle desktop, lifecycle narrow, runbook desktop, and runbook narrow. Verify state diagrams scroll rather than clip, resource matrix remains readable, command blocks preserve whitespace, and related/navigation panels link correctly.

- [ ] **Step 7: Commit generated output**

```bash
git add wiki/html wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Add vLLM operations lifecycle and runbook"
```

### Task 5: Rebase Safety and PR #49 Update

**Files:** None unless conflict resolution is required.

**Interfaces:**

- Consumes: verified Task 4 HEAD and current `origin/main`.
- Produces: mergeable PR #49 with successful build checks.

- [ ] **Step 1: Fetch and compare main**

Fetch `origin/main`, inspect `git cherry origin/main HEAD`, and determine whether main advanced after the plan began. Confirm only this feature's commits are ahead.

- [ ] **Step 2: Rebase only if required**

If main advanced, rebase the feature commits onto current `origin/main` with signing disabled for the operation. Resolve Markdown conflicts by preserving latest main knowledge and reapplying operations links; resolve generated conflicts by taking main as the base and rebuilding, never by hand-merging HTML.

- [ ] **Step 3: Re-run full verification after any rebase**

Run the full unittest file, builder twice/hash comparison, compile check, `git diff --check`, and clean status.

Expected: all green and the branch is based on current `origin/main`.

- [ ] **Step 4: Update PR safely**

Push normally if no rewrite occurred; otherwise use `git push --force-with-lease`. Verify PR #49 base is `main`, `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`, and build checks pass. Preserve the worktree for review feedback.
