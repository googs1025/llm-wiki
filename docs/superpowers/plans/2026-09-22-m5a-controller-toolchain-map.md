# M5-A Kubernetes Controller Toolchain Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Kubernetes controller/toolchain pages into a current, diagram-driven M5-A map that separates build-time generation from runtime reconciliation.

**Architecture:** `k8s-core-controller-map.md` becomes the canonical M5-A L1 page. It records current upstream evidence, then uses D1/D3/D4/D5 to connect Kubebuilder scaffolding, controller-tools generation, controller-runtime orchestration and client-go mechanisms. Three Entity pages receive responsibility/backlink sections; raw-backed Source summaries remain unchanged.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, ASCII diagrams, GitHub API evidence, Python Markdown HTML builder, Git.

---

## Scope and protected files

Modify:

- `wiki/analysis/k8s-core-controller-map.md`
- `wiki/entities/controller-runtime.md`
- `wiki/entities/kubebuilder.md`
- `wiki/entities/controller-tools.md`
- `wiki/index.md`
- `wiki/log.md`
- Generated files under `wiki/html/`

Do not modify `raw/` or the three Source pages `src-controller-runtime-architecture.md`, `src-kubebuilder-architecture.md`, and `src-controller-tools-architecture.md`. If fresh evidence contradicts a Source, stop and report it so a separate bidirectional conflict annotation can be planned.

Diagram semantics:

- Solid arrows: synchronous generation step or API read/write.
- Labeled dashed arrows: asynchronous watch, enqueue, feedback or retry.
- Build-time artifacts and runtime state occupy separate regions.
- D5 arrows describe cause → conditional response, not synchronous calls.

### Task 1: Capture current upstream evidence

**Files:**

- Modify: `wiki/analysis/k8s-core-controller-map.md:1-15`

- [ ] **Step 1: Verify baseline**

Run:

```bash
git status --short
rg -n '^date:|^## 当前上游核验' wiki/analysis/k8s-core-controller-map.md
```

Expected: clean tree; date 2026-06-13; no current-verification section.

- [ ] **Step 2: Resolve current upstream commits**

Run:

```bash
for repo in kubernetes-sigs/controller-runtime kubernetes-sigs/kubebuilder kubernetes-sigs/controller-tools; do
  gh api "repos/$repo/commits/HEAD" --jq '["'"$repo"'", .sha[0:12], .commit.committer.date, (.commit.message | split("\n")[0])] | @tsv'
done
```

Plan-time snapshots:

```text
kubernetes-sigs/controller-runtime  6ab2188a1fb1
kubernetes-sigs/kubebuilder         5f31d1f3c075
kubernetes-sigs/controller-tools    030a93937cbb
```

Use execution-time values if upstream moved.

- [ ] **Step 3: Verify primary architecture boundaries**

Read current primary documentation:

```text
https://github.com/kubernetes-sigs/controller-runtime
https://github.com/kubernetes-sigs/kubebuilder
https://book.kubebuilder.io/
https://github.com/kubernetes-sigs/controller-tools
https://pkg.go.dev/k8s.io/client-go
```

Confirm that client-go provides REST/watch/informer/workqueue foundations; controller-runtime composes runtime primitives; Kubebuilder owns author workflow/scaffolding; controller-tools parses markers/types and generates integration artifacts.

- [ ] **Step 4: Run the failing content assertion**

Run:

```bash
rg -n '^date: 2026-09-22$|^## 当前上游核验（2026-09-22）$' wiki/analysis/k8s-core-controller-map.md
```

Expected: exit 1.

- [ ] **Step 5: Add valid frontmatter and the evidence table**

Set date to `2026-09-22`. Expand sources to:

```yaml
sources: [src-k8s-core-controllers-stars, src-controller-runtime-architecture, src-kubebuilder-architecture, src-controller-tools-architecture]
```

Convert `related` to a quoted YAML wikilink list, preserving existing targets and adding `[[controller-runtime]]`, `[[kubebuilder]]`, `[[controller-tools]]`.

After H1 add `## 当前上游核验（2026-09-22）` and a table with project, exact commit link, stable responsibility and M5-A position. Use full SHAs in GitHub URLs, 12-character labels, and no placeholders. Include client-go as the foundation without inventing a new Entity. Link the Kubebuilder Book and official repositories.

- [ ] **Step 6: Verify and commit**

Run:

```bash
rg -n '^date: 2026-09-22$|^## 当前上游核验（2026-09-22）$' wiki/analysis/k8s-core-controller-map.md
for p in controller-runtime kubebuilder controller-tools; do rg -q "\[\[$p\]\]" wiki/analysis/k8s-core-controller-map.md || exit 1; done
ruby -rdate -e 'require "yaml"; s=File.read(ARGV[0]); YAML.safe_load(s.split(/^---\s*$\n/)[1], permitted_classes: [Date], aliases: false); puts "yaml ok"' wiki/analysis/k8s-core-controller-map.md
git diff --check
git add wiki/analysis/k8s-core-controller-map.md
git commit --no-gpg-sign -m "query: Refresh M5-A controller evidence"
```

### Task 2: Redraw the canonical M5-A Analysis page

**Files:**

- Modify: `wiki/analysis/k8s-core-controller-map.md:16-140`

- [ ] **Step 1: Assert the new diagram headings are absent**

Run:

```bash
for h in 'D1 · Controller 工具链职责图' 'D3 · Reconcile 控制循环' 'D4 · 状态与一致性' 'D5 · 失败边界'; do
  rg -q "^## $h$" wiki/analysis/k8s-core-controller-map.md && exit 1
done
```

Expected: exit 0.

- [ ] **Step 2: Add D1 with separate build-time and runtime regions**

Use this semantic structure:

```text
BUILD-TIME
Kubebuilder CLI
  - - scaffold - -> Go API types + markers + project layout
                          │ parse / generate
                          ▼
                 controller-tools / controller-gen
                          ├─ CRD schema
                          ├─ RBAC
                          ├─ webhook config
                          ├─ deepcopy code
                          └─ object/manifests YAML

RUNTIME
client-go foundations
  REST client · watch · informer · workqueue
                          │ composed by
                          ▼
controller-runtime
  Manager · Cache · Client · Controller/Reconciler · Webhook · envtest
```

Explain that these projects compose rather than replace one another.

- [ ] **Step 3: Add D3 Reconcile loop**

Use:

```text
Kubernetes API Server
       - - watch event - -> Cache / Informer
                                  │ enqueue key
                                  ▼
Manager → Controller → Workqueue → Reconciler
                                  ├─ cached read
                                  ├─ API write / patch
                                  ├─ status / condition
                                  ├─ finalizer
                                  └─ owned resource
                                         └ - observed state / requeue - -> API Server
```

State that reconcile is level-based, idempotent and asynchronous, not a synchronous request handler.

- [ ] **Step 4: Add D4 state/consistency table**

Cover cached read versus direct write, resourceVersion conflicts, spec/status/conditions/observedGeneration, ownerReference/GC, finalizer/deletionTimestamp, and requeue/rate-limit/idempotency. For every row identify stale/failure risk and recovery behavior.

- [ ] **Step 5: Add D5 failure boundaries**

Cover stale cache, write conflict, hot reconcile, webhook/certificate unavailability, leader switch, stuck finalizer, and wrong ownership/status. Do not imply automatic recovery when operator intervention may be required.

- [ ] **Step 6: Reconcile existing sections**

Keep the learning path, core boundaries, AI Infra examples, SIG table, OpenKruise view and selection guidance. Add controller-tools to core boundary prose. Move broad ecosystem content after D1/D3/D4/D5 and remove the old duplicate opening stack.

- [ ] **Step 7: Verify and commit**

Run:

```bash
for h in 'D1 · Controller 工具链职责图' 'D3 · Reconcile 控制循环' 'D4 · 状态与一致性' 'D5 · 失败边界'; do
  rg -q "^## $h$" wiki/analysis/k8s-core-controller-map.md || exit 1
done
test "$(rg -c '^```' wiki/analysis/k8s-core-controller-map.md)" -eq 4
git diff --check
git add wiki/analysis/k8s-core-controller-map.md
git commit --no-gpg-sign -m "query: Redraw M5-A controller map"
```

### Task 3: Synchronize the three core Entity pages

**Files:**

- Modify: `wiki/entities/controller-runtime.md`
- Modify: `wiki/entities/kubebuilder.md`
- Modify: `wiki/entities/controller-tools.md`

- [ ] **Step 1: Prove the M5-A section is absent**

Run:

```bash
for f in wiki/entities/controller-runtime.md wiki/entities/kubebuilder.md wiki/entities/controller-tools.md; do
  rg -q '^## 在 M5-A Controller 地图中的位置$' "$f" && exit 1
done
```

Expected: exit 0.

- [ ] **Step 2: Update dates and evidence notes**

Set all dates to `2026-09-22`. After the H1/introduction add the execution-time HEAD with a direct commit link, identify the corresponding Source as the 2026-06-14 raw-backed snapshot, and link `[[k8s-core-controller-map]]` as the current cross-project evidence page.

Preserve existing `sources` and `related`; normalize YAML only if needed.

- [ ] **Step 3: Add responsibility sections**

Use exact heading `## 在 M5-A Controller 地图中的位置`.

Boundaries:

```text
controller-runtime: runtime framework; Manager/cache/client/controller/reconciler/webhook/envtest; built on client-go; does not scaffold projects or generate CRDs by itself.
Kubebuilder: author workflow/scaffolding/project layout; invokes controller-tools and organizes controller-runtime code; does not own runtime reconcile semantics.
controller-tools: marker/type parser and generator; outputs CRD/RBAC/webhook/deepcopy/object artifacts; does not run the controller.
```

Each section links the Analysis and both peer Entities. Do not add diagrams.

- [ ] **Step 4: Verify and commit**

Run:

```bash
for f in wiki/entities/controller-runtime.md wiki/entities/kubebuilder.md wiki/entities/controller-tools.md; do
  rg -q '^date: 2026-09-22$' "$f" || exit 1
  rg -q '^## 在 M5-A Controller 地图中的位置$' "$f" || exit 1
  rg -q '\[\[k8s-core-controller-map\]\]' "$f" || exit 1
  ruby -rdate -e 'require "yaml"; s=File.read(ARGV[0]); YAML.safe_load(s.split(/^---\s*$\n/)[1], permitted_classes: [Date], aliases: false)' "$f" || exit 1
done
git diff --check
git add wiki/entities/controller-runtime.md wiki/entities/kubebuilder.md wiki/entities/controller-tools.md
git commit --no-gpg-sign -m "query: Link M5-A controller projects"
```

### Task 4: Publish navigation and generated output

**Files:**

- Modify: `wiki/index.md`
- Modify: `wiki/log.md` (append only)
- Regenerate: matching files under `wiki/html/`

- [ ] **Step 1: Update existing index entries**

Without adding a new category:

- describe `[[k8s-core-controller-map]]` as the M5-A D1/D3/D4/D5 entry;
- describe controller-runtime, Kubebuilder and controller-tools by runtime/scaffold/generator roles;
- add a short M5-A reading path under the existing Kubernetes controller/toolchain content.

- [ ] **Step 2: Append one log entry**

Append:

```markdown
## [2026-09-22] query | M5-A Kubernetes Controller 工具链地图

- 基于 controller-runtime、Kubebuilder、controller-tools 当前官方仓库，重构 [[k8s-core-controller-map]]，区分 build-time generation 与 runtime reconciliation。
- 新增 D1 工具链职责、D3 Reconcile、D4 状态一致性和 D5 失败边界，并同步三个核心 Entity。
- 保留 2026-06-14 Source/ASCII 图不变，更新 Index、HTML 与 graph。
```

- [ ] **Step 3: Check links and protected files**

Run a baseline-aware wikilink check on the four changed content pages and assert that no new target is missing.

Resolve the design commit and verify protection:

```bash
M5A_BASE=$(git log --format=%H --grep='^query: Plan M5-A controller map design$' -1)
test -n "$M5A_BASE"
git diff --name-only "$M5A_BASE"..HEAD | rg '^(raw/|wiki/sources/)' && exit 1 || exit 0
```

Expected: exit 0 and no output.

- [ ] **Step 4: Rebuild and inspect HTML**

Run:

```bash
uv run --quiet --with markdown --script wiki/html-assets/build.py
rg -n 'D1 · Controller 工具链职责图|D3 · Reconcile 控制循环|D4 · 状态与一致性|D5 · 失败边界' wiki/html/analysis/k8s-core-controller-map.html
for f in controller-runtime kubebuilder controller-tools; do rg -q '在 M5-A Controller 地图中的位置' "wiki/html/entities/$f.html" || exit 1; done
rg -q 'M5-A' wiki/html/index.html
```

Expected: build exit 0 and all markers present.

- [ ] **Step 5: Verify idempotency and commit**

Run the builder a second time, then run:

```bash
git diff --check
git status --short
```

Expected: the second build introduces no additional changes beyond the first generated output.

Commit:

```bash
git add wiki/index.md wiki/log.md wiki/html
git commit --no-gpg-sign -m "query: Publish M5-A controller map"
```

### Task 5: Final M5-A audit

**Files:** verify all files in scope.

- [ ] **Step 1: Check full change scope**

Run:

```bash
M5A_BASE=$(git log --format=%H --grep='^query: Plan M5-A controller map design$' -1)
test -n "$M5A_BASE"
git diff --name-only "$M5A_BASE"..HEAD
git diff --check "$M5A_BASE"..HEAD
```

Expected: only the M5-A Analysis, three Entities, index/log, generated HTML, and plan documentation.

- [ ] **Step 2: Confirm Source/raw protection**

Run:

```bash
git diff --name-only "$M5A_BASE"..HEAD | rg '^(raw/|wiki/sources/)' && exit 1 || exit 0
```

Expected: exit 0 and no output.

- [ ] **Step 3: Verify diagrams, YAML and backlinks**

Verify D1/D3/D4/D5, all four content frontmatters, Entity → Analysis links, Analysis → Entity links, balanced fences and no new missing wikilinks.

- [ ] **Step 4: Run final build verification**

Run:

```bash
uv run --quiet --with markdown --script wiki/html-assets/build.py
git diff --check
git status --short
```

Expected: build succeeds and the worktree is clean after the publication commit.
