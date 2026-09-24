# M5-B Kubernetes Workload / Scheduling Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a current M5-B knowledge path from workload APIs through Kueue admission and kube-scheduler placement to Karpenter node capacity.

**Architecture:** `kubernetes-workload-gang-scheduling-design.md` becomes the M5-B L1 page with D1–D5. `kubernetes-scheduler-core-design.md` remains the scheduler-specific downlink. Five Entity pages receive dated evidence and responsibility boundaries. Historical Source pages remain immutable unless a real contradiction requires a separately reviewed conflict annotation.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, ASCII diagrams, official GitHub/docs evidence, Python Markdown HTML builder, Git.

---

## Scope and protection

Modify:

- `wiki/analysis/kubernetes-workload-gang-scheduling-design.md`
- `wiki/analysis/kubernetes-scheduler-core-design.md`
- `wiki/entities/kueue.md`
- `wiki/entities/jobset.md`
- `wiki/entities/lws.md`
- `wiki/entities/scheduler-plugins.md`
- `wiki/entities/karpenter.md`
- `wiki/index.md`
- `wiki/log.md`
- Generated `wiki/html/**`

Protect:

- `raw/`
- `wiki/sources/src-kueue-architecture.md`
- `wiki/sources/src-jobset-architecture.md`
- `wiki/sources/src-lws-architecture.md`
- `wiki/sources/src-scheduler-plugins-architecture.md`
- `wiki/sources/src-karpenter-architecture.md`

M5-C Device/DRA pages and M5-D HPA/metrics pages are out of scope.

Diagram semantics:

- Solid arrows: synchronous or ordered API/control action.
- Labeled dashed arrows: integration, watch/event, admission feedback, unschedulable feedback and requeue.
- Admission, placement and capacity provisioning are distinct regions.
- Code fences use plain project names; wikilinks stay in surrounding prose to avoid escaped anchor markup.

### Task 1: Capture current upstream evidence

**Files:**

- Modify: `wiki/analysis/kubernetes-workload-gang-scheduling-design.md:1-18`
- Modify: `wiki/analysis/kubernetes-scheduler-core-design.md:1-18`

- [ ] **Step 1: Verify baseline**

Run:

```bash
git status --short
rg -n '^date:|^## 当前上游核验' \
  wiki/analysis/kubernetes-workload-gang-scheduling-design.md \
  wiki/analysis/kubernetes-scheduler-core-design.md
```

Expected: clean tree; both pages dated 2026-07-07; no current evidence section.

- [ ] **Step 2: Resolve current repository commits**

Run:

```bash
for repo in kubernetes-sigs/kueue kubernetes-sigs/jobset kubernetes-sigs/lws kubernetes-sigs/scheduler-plugins kubernetes-sigs/karpenter kubernetes/kubernetes; do
  gh api "repos/$repo/commits/HEAD" --jq '["'"$repo"'", .sha[0:12], .commit.committer.date, (.commit.message | split("\n")[0])] | @tsv'
done
```

Plan-time anchors:

```text
kubernetes-sigs/kueue              edf96be8809c
kubernetes-sigs/jobset             03f9dccef945
kubernetes-sigs/lws                d4f1525f15a4
kubernetes-sigs/scheduler-plugins  6df8d8e4ae5f
kubernetes-sigs/karpenter          06bc3b4b94dd
kubernetes/kubernetes              ab9b0dcfd320
```

Use execution-time values if upstream moved.

- [ ] **Step 3: Verify primary documentation**

Read only relevant primary pages:

```text
https://kueue.sigs.k8s.io/docs/concepts/
https://jobset.sigs.k8s.io/docs/concepts/
https://jobset.sigs.k8s.io/docs/reference/jobset.v1alpha2/
https://lws.sigs.k8s.io/docs/concepts/
https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/
https://scheduler-plugins.sigs.k8s.io/docs/
https://karpenter.sh/docs/concepts/nodeclaims/
https://karpenter.sh/docs/concepts/nodepools/
```

Confirm API versions and the responsibilities in the approved design. Do not infer release maturity from default-branch HEAD.

- [ ] **Step 4: Run failing assertions**

Run:

```bash
rg -n '^date: 2026-09-25$|^## 当前上游核验（2026-09-25）$' \
  wiki/analysis/kubernetes-workload-gang-scheduling-design.md \
  wiki/analysis/kubernetes-scheduler-core-design.md
```

Expected: no matches and exit 1.

- [ ] **Step 5: Update M5-B L1 evidence/frontmatter**

Set date to `2026-09-25`. Preserve all existing sources and add the five project Source slugs. Normalize `related` as valid quoted wikilinks, preserving all values and adding missing five project Entities plus `[[kubernetes-scheduler-core-design]]`.

After H1 add `## 当前上游核验（2026-09-25）` with a five-project evidence table. Each project row contains a clickable exact commit SHA, current API/responsibility, and M5-B layer. State that Source pages remain 2026-06-14 snapshots and commits are not releases.

- [ ] **Step 6: Update scheduler-page evidence/frontmatter**

Set date to `2026-09-25`; preserve sources/related and normalize YAML. Add `[[k8s-core-controller-map]]`, `[[kueue]]`, `[[karpenter]]`, and `[[kubernetes-workload-gang-scheduling-design]]` if missing.

After H1 add current Kubernetes and scheduler-plugins commit anchors, current official scheduling-framework links, and a note that Kubernetes KEP pages remain historical design/evolution evidence.

- [ ] **Step 7: Verify and commit**

Run YAML parsing, exact SHA/link checks, required links, `git diff --check`, and one-task two-file scope.

Commit:

```bash
git add wiki/analysis/kubernetes-workload-gang-scheduling-design.md wiki/analysis/kubernetes-scheduler-core-design.md
git commit --no-gpg-sign -m "query: Refresh M5-B scheduling evidence"
```

### Task 2: Build the M5-B L1 D1–D5 map

**Files:**

- Modify: `wiki/analysis/kubernetes-workload-gang-scheduling-design.md`

- [ ] **Step 1: Assert new headings are absent**

Expected exact headings:

```text
## D1 · Workload / Admission / Placement / Capacity
## D2 · Admission 与 Scheduling 路径
## D3 · Capacity Feedback
## D4 · Workload 生命周期
## D5 · 失败边界
```

- [ ] **Step 2: Add D1 responsibility backbone**

Create a fenced text diagram with four distinct regions:

```text
Workload expression
  JobSet · LeaderWorkerSet · DisaggregatedSet
       - - integration / PodSets - ->
Admission and quota
  Kueue Workload · LocalQueue · ClusterQueue
  ResourceFlavor · Cohort · AdmissionCheck · Topology
       - - admitted / unsuspend - ->
Pod placement
  kube-scheduler framework · scheduler-plugins
       │ bind to existing Node
       ▼
Node capacity feedback
  Unschedulable Pods - -> Karpenter NodePool / NodeClass → NodeClaim → Node
```

In prose state: workload APIs own group/lifecycle; Kueue owns admission; kube-scheduler owns binding; scheduler-plugins extends scheduler; Karpenter owns node capacity lifecycle.

- [ ] **Step 3: Add D2 admission/scheduling diagram**

Show workload creation/integration → Kueue Workload/PodSets → LocalQueue → ClusterQueue/Cohort → quota/flavor/check/topology → admission/unsuspend → Pods → QueueSort/PreFilter/Filter/Score/Reserve/Permit/PreBind/Bind.

Use plain names inside fences and scope integration differences in prose.

- [ ] **Step 4: Add D3 capacity-feedback diagram**

Show Unschedulable Pod condition/event → Karpenter combines pending-Pod requirements with NodePool/NodeClass → immutable NodeClaim → launch/register/initialize → Node Ready → scheduler requeue. Explain that Karpenter does not bind Pods. Keep drift/consolidation/expiration disruption as a separate feedback paragraph.

- [ ] **Step 5: Add D4 lifecycle matrix**

Rows: JobSet, LeaderWorkerSet, DisaggregatedSet, Kueue Workload. Columns: unit owned, child resources/state, success/failure/restart semantics, scaling/rollout boundary, snapshot/API caveat.

- [ ] **Step 6: Add D5 failure matrix**

Cover queue inactive, quota/flavor shortage, AdmissionCheck/provisioning stall, topology unsatisfied, scheduler no feasible node, NodeClaim launch/register/init failure, JobSet child failure, LWS/DS group-role failure, and PDB/do-not-disrupt/termination constraints. Each row distinguishes automatic retry/controller recovery/human intervention.

- [ ] **Step 7: Reconcile existing KEP sections**

Keep the existing background, core objects, design evolution, workload-aware preemption, priority, topology, controller API, KEP state and reading order after D1–D5. Update project relationship prose for current LWS/DS and avoid duplicate architecture explanations.

- [ ] **Step 8: Verify and commit**

Verify exact headings, three fenced diagrams/six fence markers, valid YAML, plain names inside fences, all links and no new missing target, one-file scope and diff check.

Commit:

```bash
git add wiki/analysis/kubernetes-workload-gang-scheduling-design.md
git commit --no-gpg-sign -m "query: Redraw M5-B workload map"
```

### Task 3: Redraw the scheduler downlink

**Files:**

- Modify: `wiki/analysis/kubernetes-scheduler-core-design.md`

- [ ] **Step 1: Add exact sections**

```text
## M5-B 中的职责边界
## Scheduling / Binding Cycle
## Queue / Requeue Feedback
## Scheduling 失败路径
```

- [ ] **Step 2: Add scheduling/binding cycle diagram**

Show active queue → PreEnqueue/QueueSort → PreFilter/Filter → PostFilter if no feasible node → PreScore/Score → Reserve → Permit → PreBind → Bind → PostBind. Distinguish scheduling cycle and binding cycle according to official framework docs.

- [ ] **Step 3: Add queue/requeue diagram**

Show activeQ/backoffQ/unschedulableQ, cluster events/QueueingHints, retry/backoff and how Kueue admission happens before scheduling while Karpenter responds after unschedulable feedback.

- [ ] **Step 4: Add failure-path table**

Cover Filter failure, PostFilter/preemption, Permit wait/reject/timeout, PreBind failure, Bind failure, stale plugin data and conflicting plugin objectives. Scope scheduler-plugins as out-of-tree framework plugins, not an alternate scheduler ownership model.

- [ ] **Step 5: Reconcile existing content and commit**

Keep ComponentConfig/profiles, topology, preemption, KEP state and reading links. Remove duplicate old data-flow prose only when the new diagrams fully replace it.

Verify exact headings, two fenced diagrams/four markers, YAML/links/diff and commit:

```bash
git add wiki/analysis/kubernetes-scheduler-core-design.md
git commit --no-gpg-sign -m "query: Redraw M5-B scheduler flow"
```

### Task 4: Synchronize five Entity pages

**Files:**

- Modify: `wiki/entities/kueue.md`
- Modify: `wiki/entities/jobset.md`
- Modify: `wiki/entities/lws.md`
- Modify: `wiki/entities/scheduler-plugins.md`
- Modify: `wiki/entities/karpenter.md`

- [ ] **Step 1: Prove M5-B sections are absent**

Exact heading: `## 在 M5-B Workload / Scheduling 地图中的位置`.

- [ ] **Step 2: Update dates and evidence notes**

Set all dates to `2026-09-25`. Add execution-time clickable commit snapshot, not-release caveat, corresponding 2026-06-14 Source boundary, and links to the M5-B L1 page and scheduler downlink.

Preserve existing sources/related; normalize YAML and add peer/Analysis links without duplicates.

- [ ] **Step 3: Add exact responsibility boundaries**

```text
Kueue: admission/quota/flavor/topology/checks; does not select final Node.
JobSet: set of replicated batch Jobs with dependency, success/failure/restart and shared-volume lifecycle; does not own quota or node placement.
LWS: LeaderWorkerSet owns homogeneous pod-group replication/lifecycle; DisaggregatedSet composes role-specific LWS/slices for multi-role inference; neither owns quota admission.
scheduler-plugins: out-of-tree implementations of kube-scheduler framework extension points; does not own workload CRD lifecycle or node creation.
Karpenter: watches unschedulable demand, combines Pod/NodePool/NodeClass constraints, creates NodeClaims and manages node lifecycle/disruption; kube-scheduler still binds Pods.
```

Do not add diagrams. Scope API versions and volatile feature counts to the snapshot.

- [ ] **Step 4: Verify and commit**

Verify dates/headings/SHAs, YAML, links to both Analysis pages, preserved original body/fences, no new missing links and five-file scope.

Commit:

```bash
git add wiki/entities/kueue.md wiki/entities/jobset.md wiki/entities/lws.md wiki/entities/scheduler-plugins.md wiki/entities/karpenter.md
git commit --no-gpg-sign -m "query: Link M5-B workload projects"
```

### Task 5: Publish Index, Log and HTML

**Files:**

- Modify: `wiki/index.md`
- Modify: `wiki/log.md` (append only)
- Regenerate: `wiki/html/**`

- [ ] **Step 1: Update existing Index entries**

Without adding a category:

- describe the M5-B L1 page and scheduler downlink;
- update Kueue, JobSet, LWS/DisaggregatedSet, scheduler-plugins and Karpenter descriptions by responsibility;
- add one M5-B reading path under Kubernetes workload/scheduling content.

- [ ] **Step 2: Append one log entry**

Use current operation date:

```markdown
## [2026-09-25] query | M5-B Kubernetes Workload / Scheduling 地图

- 基于 Kueue、JobSet、LWS/DisaggregatedSet、scheduler-plugins、Karpenter 与 Kubernetes scheduler 当前官方证据，重构 Workload → Admission → Placement → Capacity 主线。
- 更新 [[kubernetes-workload-gang-scheduling-design]] 的 D1–D5，并重画 [[kubernetes-scheduler-core-design]] 的 scheduling/binding cycle 与 queue/requeue。
- 同步五个 Entity；保留历史 Source/ASCII 图，更新 Index、HTML 与 graph。
```

- [ ] **Step 3: Check links and protected paths**

Run baseline-aware link checks on seven content pages. Assert no new missing links.

Resolve design commit and assert no `raw/` or protected Source path changed.

- [ ] **Step 4: Build and inspect**

Run:

```bash
uv run --quiet --with markdown --script wiki/html-assets/build.py
```

Verify all D1–D5 and scheduler headings in generated HTML, five Entity M5-B sections, Index reading path, Log entry and graph backlinks. Verify code fences contain no escaped wikilink anchor markup.

- [ ] **Step 5: Prove idempotency and commit**

Run the builder again and compare the full binary diff hash before/after. Run `git diff --check`.

Commit:

```bash
git add wiki/index.md wiki/log.md wiki/html
git commit --no-gpg-sign -m "query: Publish M5-B workload map"
```

### Task 6: Final M5-B audit

**Files:** verify all M5-B files.

- [ ] **Step 1: Audit full scope**

Resolve the design commit `query: Plan M5-B workload scheduling design`, inspect the full range and confirm only approved Markdown, generated HTML, design and plan files changed.

- [ ] **Step 2: Verify protection and conflicts**

Assert no raw/Source Markdown change unless a separately reviewed conflict annotation was explicitly added. If conflict annotations exist, verify historical diagrams are byte-identical.

- [ ] **Step 3: Verify semantics**

Confirm:

- Kueue admission is not scheduler placement.
- kube-scheduler binds Pods.
- scheduler-plugins extends framework points.
- Karpenter creates/manages capacity and does not bind Pods.
- JobSet/LWS/DS ownership and failure boundaries are distinct.
- D1–D5 and scheduler diagrams use agreed arrow semantics.

- [ ] **Step 4: Verify content and generated output**

Parse all seven YAML frontmatters; check fences/headings/wikilinks; run full local HTML link/fragment and graph integrity checks; confirm hand-crafted HTML unchanged.

- [ ] **Step 5: Final build**

Run the builder twice at final HEAD, verify a clean worktree and `git diff --check`.
