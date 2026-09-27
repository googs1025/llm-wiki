# M5-C Kubernetes Device / GPU Map Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a current Device/GPU knowledge path that separates discovery, node software lifecycle, Device Plugin and DRA allocation, CDI injection, and GPU sharing/isolation.

**Architecture:** `k8s-gpu-device-stack.md` becomes the M5-C L1 page. `kubernetes-dra-design-deep-dive.md` provides the ResourceClaim/scheduler/kubelet downlink. Four Concept and five Entity pages receive dated role boundaries. Historical Source diagrams stay protected unless a real contradiction requires a separately reviewed warning.

**Tech Stack:** Markdown, YAML, Obsidian wikilinks, ASCII diagrams, official GitHub/docs evidence, Python Markdown HTML builder, Git.

---

## Scope and protected content

Modify:

- `wiki/analysis/k8s-gpu-device-stack.md`
- `wiki/analysis/kubernetes-dra-design-deep-dive.md`
- `wiki/concepts/device-plugin.md`
- `wiki/concepts/kubernetes-dra.md`
- `wiki/concepts/cdi.md`
- `wiki/concepts/gpu-sharing.md`
- `wiki/entities/node-feature-discovery.md`
- `wiki/entities/gpu-operator.md`
- `wiki/entities/k8s-device-plugin.md`
- `wiki/entities/dra-driver-nvidia-gpu.md`
- `wiki/entities/hami.md`
- `wiki/index.md`, `wiki/log.md`, generated `wiki/html/**`

Protect `raw/` and the Source Markdown pages for NFD, GPU Operator, Device Plugin, NVIDIA DRA Driver and HAMi. M5-B and M5-D content are out of scope.

Diagram rules:

- Solid arrows: ordered/synchronous API or node action.
- Dashed arrows: discovery publication, reconciliation, watch/health feedback and retry.
- Device Plugin and DRA are separate allocation paths.
- CDI appears only at device injection/runtime handoff.
- Plain names inside fences; wikilinks live in prose.

### Task 1: Capture current evidence and audit conflicts

**Files:**

- Modify: `wiki/analysis/k8s-gpu-device-stack.md:1-15`
- Modify: `wiki/analysis/kubernetes-dra-design-deep-dive.md:1-18`

- [ ] **Step 1: Verify baseline**

Run status/date/evidence-heading checks. Expected dates are 2026-06-13 and 2026-07-07 with no current-evidence headings.

- [ ] **Step 2: Resolve execution-time commits**

Run:

```bash
for repo in kubernetes-sigs/node-feature-discovery NVIDIA/gpu-operator NVIDIA/k8s-device-plugin NVIDIA/k8s-dra-driver-gpu Project-HAMi/HAMi kubernetes/kubernetes; do
  gh api "repos/$repo/commits/HEAD" --jq '["'"$repo"'", .sha[0:12], .commit.committer.date, (.commit.message | split("\n")[0])] | @tsv'
done
```

Plan-time anchors:

```text
node-feature-discovery  386fda4332ba
gpu-operator            60526e35efee
k8s-device-plugin       86142cf1a93f
k8s-dra-driver-gpu      495bf4c59b94
HAMi                    a2dd191b2e7f
kubernetes              6c1c7702cf20
```

- [ ] **Step 3: Verify primary docs and feature stages**

Read current Kubernetes DRA/DRA Features/API docs, NVIDIA GPU Operator/DRA docs, NFD docs, NVIDIA Device Plugin repo/docs and HAMi protocol/integration/FAQ. Confirm:

- base DRA stable since v1.35;
- extension stages are independent;
- GPU Operator `ClusterPolicy` and `GPUCluster` paths differ;
- only one owner should advertise a conflicting GPU resource on one node;
- HAMi scheduler/device-plugin/core responsibilities are distinct.

- [ ] **Step 4: Audit historical Source for real conflicts**

Search protected Source pages for unqualified present-tense claims about repo ownership, DRA feature stage, mutual coexistence and GPU Operator CRDs. Missing new capabilities are not conflicts. If a real contradiction exists, stop and report exact page/lines before editing any Source.

- [ ] **Step 5: Update L1 evidence/frontmatter**

Set date `2026-09-27`; preserve/add all five project Source slugs and valid related links including NFD. Add exact heading `## 当前上游核验（2026-09-27）` after H1 with five clickable commit rows, current responsibility/allocation layer, official docs and not-release/Source-snapshot caveat.

- [ ] **Step 6: Update DRA page evidence/frontmatter**

Set date `2026-09-27`; preserve sources/related, normalize YAML and add L1/Entity/Concept links. Add current Kubernetes and NVIDIA DRA commit evidence plus a feature-stage table that separates stable base DRA from current alpha/beta extensions. Every feature stage must cite current official docs or source.

- [ ] **Step 7: Verify and commit**

Validate both YAML files, exact SHAs/links, sources/related, no body changes below inserted evidence, no new missing links and two-file scope.

Commit:

```bash
git add wiki/analysis/k8s-gpu-device-stack.md wiki/analysis/kubernetes-dra-design-deep-dive.md
git commit --no-gpg-sign -m "query: Refresh M5-C device evidence"
```

### Task 2: Redraw the M5-C L1 Device/GPU map

**Files:**

- Modify: `wiki/analysis/k8s-gpu-device-stack.md`

- [ ] **Step 1: Add exact headings**

```text
## D1 · GPU Device Stack
## D2 · Device Plugin Allocation
## D3 · Discovery / Operator Control Loops
## D4 · DRA Resource 生命周期
## Sharing / Isolation Overlay
## D5 · 失败边界
```

- [ ] **Step 2: Add D1 stack diagram**

Show NFD discovery/capability → GPU Operator node-software lifecycle → explicit fork:

- Device Plugin / ClusterPolicy / extended resource / kubelet Allocate.
- DRA / GPUCluster / DeviceClass+ResourceSlice / ResourceClaim / NodePrepare+CDI.

State operator/allocator/injection boundaries and coexistence caveats.

- [ ] **Step 3: Add D2 Device Plugin diagram**

Show registration → ListAndWatch/health → Node capacity/allocatable → Pod extended-resource request → scheduler node fit → kubelet Allocate → env/mount/CDI/device injection → runtime.

- [ ] **Step 4: Add D3 control-loop diagram**

Show NFD worker publication/GC/topology and GPU Operator desired-policy reconciliation/status. State NFD feature freshness and Operator non-ownership of individual allocation.

- [ ] **Step 5: Add D4 DRA lifecycle summary**

Add a compact L1 diagram or table linking to the downlink page: DeviceClass/ResourceSlice → Claim → scheduler allocation/binding conditions → NodePrepare/CDI → NodeUnprepare/release.

- [ ] **Step 6: Add Sharing/Isolation overlay**

Explain HAMi scheduler/extender reservation, Pod annotation handoff, device-plugin Allocate and HAMi-core isolation. Include current single-plugin/resource ownership caveat and distinguish HAMi-DRA allocation path from isolation.

- [ ] **Step 7: Add D5 failure matrix**

Cover NFD stale state, Operator operands, plugin registration/Allocate/health, ResourceSlice/Claim drift, binding timeout, NodePrepare/CDI/checkpoint, MIG/VFIO/ComputeDomain partial mutation, HAMi annotation handoff and isolation/overcommit. Distinguish API retry, node recovery, operator reconcile and human repair.

- [ ] **Step 8: Reconcile old content and commit**

Keep project boundaries, LLM serving relation and selection guidance after D1–D5; remove only superseded generic stack. Use plain names in fences. Verify exact headings, intended fence count, YAML/links/no escaped anchor/one-file/diff.

Commit:

```bash
git add wiki/analysis/k8s-gpu-device-stack.md
git commit --no-gpg-sign -m "query: Redraw M5-C device stack"
```

### Task 3: Redraw the DRA downlink

**Files:**

- Modify: `wiki/analysis/kubernetes-dra-design-deep-dive.md`

- [ ] **Step 1: Add exact sections**

```text
## M5-C 中的职责边界
## DRA Allocation / Binding Lifecycle
## kubelet Prepare / CDI / Release
## DRA 失败与恢复路径
```

- [ ] **Step 2: Add allocation/binding diagram**

Show DeviceClass/ResourceSlice publication, Claim creation, scheduler filter/select/allocation, optional binding conditions and PreBind wait, Pod bind and status ownership.

- [ ] **Step 3: Add kubelet/runtime diagram**

Show kubelet NodePrepareResources → vendor DRA plugin → device configuration/checkpoint → CDI assignment → runtime; termination → NodeUnprepareResources/release/cleanup.

- [ ] **Step 4: Add feature-stage and failure tables**

Keep stable base versus extension stages explicit. Failure table covers stale slices, allocation conflict, binding condition timeout/failure, plugin restart/checkpoint, Prepare/Unprepare, CDI, partial device mutation and node loss.

- [ ] **Step 5: Reconcile KEP history and commit**

Keep historical KEP model, scheduler path, Claim state, kubelet, autoscaler, extensions, risks and reading order; update current-state interpretation without rewriting history.

Verify headings, two plain-text diagrams/four fence markers, YAML/links/one-file/diff.

Commit:

```bash
git add wiki/analysis/kubernetes-dra-design-deep-dive.md
git commit --no-gpg-sign -m "query: Redraw M5-C DRA lifecycle"
```

### Task 4: Synchronize four Concept pages

**Files:**

- Modify: `wiki/concepts/device-plugin.md`
- Modify: `wiki/concepts/kubernetes-dra.md`
- Modify: `wiki/concepts/cdi.md`
- Modify: `wiki/concepts/gpu-sharing.md`

- [ ] **Step 1: Update dates and navigation**

Set dates to `2026-09-27`. Preserve sources/related, normalize YAML and add both M5-C Analysis pages plus relevant Entity links.

- [ ] **Step 2: Update Device Plugin concept**

Explain registration/ListAndWatch/health/extended-resource/Allocate/runtime-injection flow, DRA difference and resource-owner coexistence risk. Link D2.

- [ ] **Step 3: Update Kubernetes DRA concept**

State base DRA stable since v1.35, link current feature-stage table, and replace “future-only” language. Separate ResourceClaim allocation, node prepare and CDI.

- [ ] **Step 4: Update CDI concept**

State that CDI describes device injection for container runtimes; it is not scheduler/allocation. Explain producers/consumers across Device Plugin, DRA, Operator and HAMi.

- [ ] **Step 5: Update GPU Sharing concept**

Separate scheduling/accounting, allocation, hardware partitioning and runtime isolation. Compare time-slicing, MPS, MIG and HAMi-core without claiming equivalent isolation.

- [ ] **Step 6: Verify and commit**

Verify four YAML files, exact current-state statements, both Analysis links, no new missing links, original body retained except directly updated sections, no diagrams unless required.

Commit:

```bash
git add wiki/concepts/device-plugin.md wiki/concepts/kubernetes-dra.md wiki/concepts/cdi.md wiki/concepts/gpu-sharing.md
git commit --no-gpg-sign -m "query: Align M5-C device concepts"
```

### Task 5: Synchronize five Entity pages

**Files:**

- Modify: `wiki/entities/node-feature-discovery.md`
- Modify: `wiki/entities/gpu-operator.md`
- Modify: `wiki/entities/k8s-device-plugin.md`
- Modify: `wiki/entities/dra-driver-nvidia-gpu.md`
- Modify: `wiki/entities/hami.md`

- [ ] **Step 1: Add evidence snapshots**

Set dates to `2026-09-27`. Add execution-time clickable commit links, not-release caveats, 2026-06/07 historical Source boundaries and both M5-C Analysis links. Preserve/normalize related lists.

- [ ] **Step 2: Add exact heading**

`## 在 M5-C Device / GPU 地图中的位置`

Responsibilities:

```text
NFD: detect/publish node features/topology and clean stale objects; no device allocation.
GPU Operator: reconcile NVIDIA node software and chosen allocation operands; no per-Pod device choice.
NVIDIA Device Plugin: advertise extended resources/health and service kubelet Allocate; no rich claim model.
NVIDIA DRA Driver: publish DRA devices/classes/slices, prepare/unprepare and manage NVIDIA-specific device configuration/ComputeDomain; not traditional extended-resource plugin.
HAMi: scheduler/extender reservation + device-plugin allocation + HAMi-core isolation; resource-owner coexistence and annotation protocol explicitly scoped.
```

- [ ] **Step 3: Correct current-facing contradictions**

Only correct old Entity body when it directly contradicts current evidence, such as treating DRA as merely future/experimental or presenting ClusterPolicy as the only current GPU Operator mode. Record each correction in the report.

- [ ] **Step 4: Verify and commit**

Verify dates/SHAs/YAML/links/responsibilities, no new diagrams, no new missing links and five-file scope.

Commit:

```bash
git add wiki/entities/node-feature-discovery.md wiki/entities/gpu-operator.md wiki/entities/k8s-device-plugin.md wiki/entities/dra-driver-nvidia-gpu.md wiki/entities/hami.md
git commit --no-gpg-sign -m "query: Link M5-C device projects"
```

### Task 6: Publish Index, Log and generated output

**Files:**

- Modify: `wiki/index.md`
- Modify: `wiki/log.md` (append only)
- Regenerate: `wiki/html/**`

- [ ] **Step 1: Update Index descriptions and reading path**

Within existing sections, describe M5-C L1/DRA downlink, four Concepts and five Entity roles. Add one reading path from stack map → DRA lifecycle → Concepts/Entities. Do not add a category.

- [ ] **Step 2: Append log entry**

Use:

```markdown
## [2026-09-27] query | M5-C Kubernetes Device / GPU 地图

- 基于 NFD、NVIDIA GPU Operator、Device Plugin、DRA Driver、HAMi 与 Kubernetes DRA 当前官方证据，重构 discovery → node software → allocation → runtime injection → sharing/isolation 主线。
- 更新 [[k8s-gpu-device-stack]] 的 D1–D5 与 [[kubernetes-dra-design-deep-dive]] 的 ResourceClaim/scheduler/kubelet/CDI 生命周期。
- 同步四个 Concept 和五个 Entity；保留历史 Source/ASCII 图，更新 Index、HTML 与 graph。
```

- [ ] **Step 3: Check protected content and links**

Run baseline-aware wikilink checks on 11 content pages. Assert no unapproved raw/Source changes.

- [ ] **Step 4: Build and inspect**

Build HTML. Verify L1/DRA headings, all Concept/Entity positioning, Index/Log and graph backlinks. Decode/compare diagrams and assert no escaped wikilink anchors.

- [ ] **Step 5: Prove idempotency and commit**

Run a second build and compare binary diff hashes. Run `git diff --check`.

Commit:

```bash
git add wiki/index.md wiki/log.md wiki/html
git commit --no-gpg-sign -m "query: Publish M5-C device map"
```

### Task 7: Final M5-C audit

- [ ] **Step 1: Audit full change range and protected paths**

Resolve the design commit, list changed files, validate approved scope, no raw changes and only approved Source warnings if any.

- [ ] **Step 2: Audit semantics repository-wide**

Search current-facing pages for stale claims about DRA maturity, GPU Operator management mode, Device Plugin/DRA coexistence, CDI ownership and HAMi plugin coexistence. Historical Source text may remain only with clear snapshot boundaries.

- [ ] **Step 3: Validate content and graph**

Parse 11 YAML files, verify headings/fences/arrows/wikilinks, all local HTML targets/fragments, graph endpoints/degrees and bidirectional links. Confirm hand-crafted HTML unchanged.

- [ ] **Step 4: Final deterministic build**

Run two builds at final HEAD, require clean status and identical empty status hashes; run `git diff --check`.
