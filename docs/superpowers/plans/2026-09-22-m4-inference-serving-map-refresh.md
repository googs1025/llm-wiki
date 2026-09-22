# M4 Inference / Serving / Routing Map Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh the M4 inference-serving knowledge path so the wiki clearly relates engines, gateways, endpoint routing, distributed serving, KV state, Kubernetes control loops, and GPU infrastructure.

**Architecture:** Keep the 2026-09-13/14 Source summaries and their dense ASCII diagrams unchanged. Rebuild the two cross-project Analysis pages around the agreed L1/D1–D5 diagram system, then add lightweight module-position links to existing Entity and Concept pages. Treat current official repository/docs observations as a dated evidence layer and do not silently rewrite older raw-backed claims.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, ASCII diagrams, official GitHub/docs evidence, `wiki/html-assets/build.py`, Git.

---

## Scope and file map

- Modify `wiki/analysis/llm-inference-serving-project-map.md`: canonical M4 L1 page and D1–D5 diagrams.
- Modify `wiki/analysis/llm-serving-engine-selection-map.md`: layer-first selection and composition guidance.
- Modify `wiki/concepts/{llm-inference,inference-routing,disaggregated-serving,kv-cache-offload}.md`: focused entry points back to M4.
- Modify `wiki/entities/{vllm,sglang,dynamo,llm-d,aibrix}.md`: project responsibility in the M4 stack.
- Modify `wiki/index.md` and append `wiki/log.md`.
- Regenerate matching pages under `wiki/html/`.
- Do not modify `raw/` or `wiki/sources/`. If current evidence contradicts a Source summary, add a visible conflict note and handle the Source in a separate operation.

Diagram conventions:

- Solid arrows mean synchronous request/data transfer.
- `- - signal - ->` means asynchronous observation/control.
- APIs and user-facing layers go at the top; device/compute layers go at the bottom.
- Control-plane boxes remain outside the synchronous request path.
- Every diagram heading starts with D1, D2, D3, D4, or D5.

### Task 1: Capture fresh upstream evidence

**Files:**

- Modify: `wiki/analysis/llm-inference-serving-project-map.md:1-15`
- Modify: `wiki/analysis/llm-serving-engine-selection-map.md:1-24`

- [ ] **Step 1: Confirm the baseline**

Run:

```bash
git status --short
rg -n '^date:|^## 当前上游核验' \
  wiki/analysis/llm-inference-serving-project-map.md \
  wiki/analysis/llm-serving-engine-selection-map.md
```

Expected: clean tree; both pages have June dates; only the selection page has an older current-check heading.

- [ ] **Step 2: Resolve current primary-repository revisions**

Run:

```bash
for repo in vllm-project/vllm sgl-project/sglang ai-dynamo/dynamo llm-d/llm-d vllm-project/aibrix; do
  gh api "repos/$repo/commits/HEAD" \
    --jq '["'"$repo"'", .sha[0:12], .commit.committer.date, (.commit.message | split("\n")[0])] | @tsv'
done
```

Expected: five TSV rows containing repository, 12-character SHA, date, and subject.

- [ ] **Step 3: Verify only the architecture claims needed by the map**

Read these primary sources:

```text
https://docs.vllm.ai/en/latest/getting_started/v1_user_guide.html
https://docs.sglang.ai/
https://docs.nvidia.com/dynamo/dev/knowledge-base/overview
https://docs.nvidia.com/dynamo/dev/knowledge-base/concepts/architecture
https://llm-d.ai/docs/dev/architecture
https://llm-d.ai/docs/dev/architecture/core/router/epp
https://aibrix.readthedocs.io/latest/getting_started/overview.html
https://aibrix.readthedocs.io/latest/features/runtime.html
```

Verify these boundaries: vLLM/SGLang own engine scheduling, execution and local KV; Dynamo surrounds engines with distributed request/control/state concerns; llm-d centers on Proxy/EPP, InferencePool and Model Server; AIBrix supplies Kubernetes routing, autoscaling, model/adapter/runtime and KV orchestration around engines.

- [ ] **Step 4: Prove the new evidence marker is absent**

Run:

```bash
rg -n '^date: 2026-09-22$|^## 当前上游核验（2026-09-22）$' \
  wiki/analysis/llm-inference-serving-project-map.md
```

Expected: exit 1 with no matches.

- [ ] **Step 5: Add the dated evidence layer**

In both Analysis pages set `date: 2026-09-22`. Add `src-vllm-architecture`, `src-aibrix-architecture`, `src-k8s-serving-stack-comparison`, `[[aibrix]]`, `[[inference-routing]]`, and `[[model-serving-operator]]` to frontmatter where missing.

Immediately after the project-map H1, add:

```markdown
## 当前上游核验（2026-09-22）

本页把官方仓库/文档的当前观察与既有 raw-backed Source 摘要分开。Source 摘要仍保存其分析时点；下表用于判断本次横向地图是否需要调整。

| 项目 | 核验版本 | 当前稳定职责 | 本次处理 |
|------|----------|--------------|----------|
| [[vllm]] | `HEAD f84325c48c0a` | engine scheduler、model execution、local KV | 保留内部图，补外部边界 |
| [[sglang]] | `HEAD 04c0913434c4` | engine/runtime、RadixCache、distributed/P-D integration | 保留内部图，补集成边界 |
| [[dynamo]] | `HEAD da27aa78dcad` | distributed request/control/state runtime、routing、KV transfer、planner | 更新平台层关系 |
| [[llm-d]] | `HEAD 1e9a86a3a9da` | Proxy/EPP、InferencePool、Model Server 与 routing signals | 更新 Gateway/EPP 热路径 |
| [[aibrix]] | `HEAD 96056b47f158` | K8s routing、autoscaling、adapter/model lifecycle、KV/multi-role orchestration | 纳入核心比较 |

> [!note] 证据边界
> 当前职责来自本次官方仓库与文档核验；内部调用路径仍以对应 Source 页面为准。
```

Before editing, compare these captured SHAs with Step 2 output. If upstream moved, use the newly resolved SHAs consistently in both Analysis pages. Rename the selection page's old check heading to the same dated heading and list the same five revisions.

- [ ] **Step 6: Verify and commit**

Run:

```bash
rg -n '^date: 2026-09-22$|^## 当前上游核验（2026-09-22）$|\[\[aibrix\]\]' \
  wiki/analysis/llm-inference-serving-project-map.md \
  wiki/analysis/llm-serving-engine-selection-map.md
git add wiki/analysis/llm-inference-serving-project-map.md \
  wiki/analysis/llm-serving-engine-selection-map.md
git commit -m "query: Refresh M4 upstream evidence"
```

Expected: both pages have the date/heading and the evidence commit succeeds.

### Task 2: Rebuild the M4 L1 page with D1–D5

**Files:**

- Modify: `wiki/analysis/llm-inference-serving-project-map.md:13-350`

- [ ] **Step 1: Prove the diagram headings are absent**

Run:

```bash
for h in 'D1 · 模块边界图' 'D2 · 在线请求热路径' 'D3 · 扩缩与部署控制循环' 'D4 · KV 状态生命周期' 'D5 · 故障与降级边界'; do
  rg -q "^## $h$" wiki/analysis/llm-inference-serving-project-map.md && exit 1
done
```

Expected: exit 0 because none of the exact headings exists.

- [ ] **Step 2: Replace the current opening diagrams with D1**

Insert a `## D1 · 模块边界图` section containing this normal `text` code fence:

```text
Application / Agent / Batch Client
                  │ OpenAI-compatible API
                  ▼
┌──────────────── Gateway / Traffic ────────────────┐
│ Gateway API / HTTPRoute / Proxy / auth / policy   │
└───────────────────────┬───────────────────────────┘
                        │ endpoint decision
                        ▼
┌──────────────── Routing / Serving Platform ───────┐
│ EPP / Router / InferencePool / discovery          │
│ Dynamo / llm-d / AIBrix control and runtime parts │
└──────────────┬───────────────────────┬─────────────┘
               │ aggregated            │ disaggregated
               ▼                       ▼
┌──────────────── Inference Engines ────────────────┐
│ vLLM / SGLang / TensorRT-LLM                     │
│ scheduler → model runner → attention → local KV  │
└───────────────────────┬───────────────────────────┘
                        │ allocate / transfer / offload
                        ▼
┌──────────────── Compute and State ────────────────┐
│ GPU / HBM / CPU / SSD / object store / KV index  │
└───────────────────────────────────────────────────┘

control plane beside the path:
CRD / deployment / planner / autoscaler / operator
  - - metrics · KV events · readiness · SLO - ->
```

Follow it with: “This is a responsibility map, not a claim that every deployment contains every box.” Explain that vLLM/SGLang are engines while Dynamo/llm-d/AIBrix provide different surrounding scopes.

- [ ] **Step 3: Add D2 request paths**

Add `## D2 · 在线请求热路径` with:

```text
aggregated:
Client → Gateway/Frontend → Router/EPP → Engine Scheduler → Model Runner → stream

disaggregated:
Client → Gateway/Frontend → Router/EPP
                              │
                              ├→ Prefill worker ── KV metadata/data ─┐
                              │                                      ▼
                              └───────────────────────────────→ Decode worker → stream
```

State explicitly: connection handling, endpoint selection, and token execution are separate responsibilities; P/D mode also requires a KV-transfer contract.

- [ ] **Step 4: Add D3 control loop**

Add `## D3 · 扩缩与部署控制循环` with:

```text
Model / SLO / topology intent
             │
             ▼
CRD / Deployment / InferencePool / platform config
             │ reconcile
             ▼
Operator / Planner / Autoscaler ───────→ worker pools / engine pods
             ▲                                      │
             └ - metrics / queue / KV / readiness - ┘
```

Explain which portions may be owned by Dynamo, llm-d, or AIBrix without implying they are interchangeable.

- [ ] **Step 5: Add D4 KV lifecycle**

Add `## D4 · KV 状态生命周期` with:

```text
prompt tokens
     │ prefill
     ▼
local KV blocks ── publish events/index ──→ routing locality signal
     │
     ├── direct P→D transfer ─────────────→ decode-local KV
     ├── offload → CPU / SSD / remote tier → recall/promote
     └── pressure / expiry / model change ─→ evict or recompute
```

State that the engine owns local KV representation while surrounding layers may index, route, transfer, or offload it.

- [ ] **Step 6: Add D5 failure boundaries**

Add `## D5 · 故障与降级边界` with:

```text
EPP/router unavailable → fail open / fail close / reject according to gateway policy
worker not ready        → discovery removes/inhibits endpoint → choose another worker
prefill/decode failure  → cancel, retry, or recompute according to backend contract
KV index stale          → lower hit quality; engine correctness remains independent
autoscaler lag          → queue/load shedding protects the request path
```

- [ ] **Step 7: Reconcile existing prose and tables**

Make all of these changes:

1. Add llm-d and AIBrix to `一句话分层` and `横向对比`.
2. Group comparison rows by engine, distributed runtime, K8s serving/control plane, and infrastructure.
3. Add short llm-d/AIBrix subsections to `项目工程剖面`; link to Entity/Source pages instead of copying Source text.
4. Scope time-sensitive claims to official evidence instead of calling configurable features universal defaults.
5. Remove already-resolved items from `下一批候选` and `当前知识库缺口`.

- [ ] **Step 8: Verify and commit**

Run:

```bash
for h in 'D1 · 模块边界图' 'D2 · 在线请求热路径' 'D3 · 扩缩与部署控制循环' 'D4 · KV 状态生命周期' 'D5 · 故障与降级边界'; do
  rg -q "^## $h$" wiki/analysis/llm-inference-serving-project-map.md || exit 1
done
for p in vllm sglang dynamo llm-d aibrix; do
  rg -q "\[\[$p\]\]" wiki/analysis/llm-inference-serving-project-map.md || exit 1
done
git add wiki/analysis/llm-inference-serving-project-map.md
git commit -m "query: Redraw M4 inference serving map"
```

Expected: D1–D5 and all five anchor projects exist; commit succeeds.

### Task 3: Reframe selection as layer-first composition

**Files:**

- Modify: `wiki/analysis/llm-serving-engine-selection-map.md:24-57`

- [ ] **Step 1: Prove the new headings are absent**

Run:

```bash
rg -n '^## (先选层，再选项目|决策流程图|组合方案)$' \
  wiki/analysis/llm-serving-engine-selection-map.md
```

Expected: exit 1 with no matches.

- [ ] **Step 2: Add the layer-first matrix**

Add:

```markdown
## 先选层，再选项目

| 当前问题 | 应选择的层 | 代表项目 |
|----------|------------|----------|
| scheduler、kernel、local KV、单实例吞吐 | 推理引擎 | [[vllm]], [[sglang]] |
| multi-node runtime、P/D、KV transfer | distributed serving runtime | [[dynamo]] |
| Gateway API、endpoint picking、InferencePool | K8s routing/serving stack | [[llm-d]] |
| autoscaling、LoRA/model lifecycle、K8s inference operations | K8s inference control plane | [[aibrix]] |
| GPU allocation、sharing、health、capacity | infrastructure | [[k8s-gpu-device-stack]] |

不同层的项目不是直接替代关系；生产系统通常组合一个 engine、一个 routing/control layer 和一个 infrastructure layer。
```

- [ ] **Step 3: Add the decision flow**

Add `## 决策流程图` with:

```text
Need a model execution engine?
  ├─ yes → vLLM or SGLang by model/hardware/scheduler/KV/ops fit
  └─ already chosen
        ↓
Need multi-node runtime or P/D/KV transfer coordination?
  ├─ yes → evaluate Dynamo and engine-native integrations
  └─ no
        ↓
Need Gateway/EPP/InferencePool routing on Kubernetes?
  ├─ yes → evaluate llm-d
  └─ no
        ↓
Need autoscaling, adapters, model lifecycle and broader K8s operations?
  ├─ yes → evaluate AIBrix
  └─ no → keep the smallest sufficient stack
```

- [ ] **Step 4: Add composition and avoid-if guidance**

Add `## 组合方案` with four explicit patterns: minimal engine service; engine + llm-d intelligent routing; engine + Dynamo distributed runtime; engine + selected AIBrix control-plane components. Update existing conclusions so each includes best fit, avoid-if, adoption cost, and what to verify next.

- [ ] **Step 5: Verify and commit**

Run:

```bash
rg -n '^## (先选层，再选项目|决策流程图|组合方案|避坑条件)$' \
  wiki/analysis/llm-serving-engine-selection-map.md
for p in vllm sglang dynamo llm-d aibrix; do
  rg -q "\[\[$p\]\]" wiki/analysis/llm-serving-engine-selection-map.md || exit 1
done
git add wiki/analysis/llm-serving-engine-selection-map.md
git commit -m "query: Reframe M4 serving selection"
```

Expected: required headings/projects exist; commit succeeds.

### Task 4: Synchronize Concept and Entity landing pages

**Files:**

- Modify: `wiki/concepts/llm-inference.md:1-161`
- Modify: `wiki/concepts/inference-routing.md:1-68`
- Modify: `wiki/concepts/disaggregated-serving.md:1-95`
- Modify: `wiki/concepts/kv-cache-offload.md:1-111`
- Modify: `wiki/entities/vllm.md:1-64`
- Modify: `wiki/entities/sglang.md:1-88`
- Modify: `wiki/entities/dynamo.md:1-37`
- Modify: `wiki/entities/llm-d.md:1-25`
- Modify: `wiki/entities/aibrix.md:1-25`

- [ ] **Step 1: Prove the Entity module-position section is absent**

Run:

```bash
for f in wiki/entities/vllm.md wiki/entities/sglang.md wiki/entities/dynamo.md wiki/entities/llm-d.md wiki/entities/aibrix.md; do
  if rg -q '^## 在 M4 模块地图中的位置$' "$f"; then
    exit 1
  fi
  echo "$f"
done
```

Expected: all five paths are printed.

- [ ] **Step 2: Add the M4 entry point to the umbrella concept**

Set `wiki/concepts/llm-inference.md` to `date: 2026-09-22` and add after its introduction:

```markdown
## M4 阅读入口

- 先看 [[llm-inference-serving-project-map]]：理解 engine、routing、distributed runtime、Kubernetes control plane 和 GPU infrastructure 的职责边界。
- 再看 [[llm-serving-engine-selection-map]]：先选择缺失的架构层，再选择项目或组合。
- 需要下钻时进入 [[vllm]]、[[sglang]]、[[dynamo]]、[[llm-d]]、[[aibrix]] 及对应 Source 页面。
```

Keep existing detailed diagrams; do not duplicate D1–D5.

- [ ] **Step 3: Add focused Concept pointers**

Set all three pages to `date: 2026-09-22` and add concise Chinese sections:

```markdown
# wiki/concepts/inference-routing.md
## 在 M4 中的位置
Routing 位于流量入口与 engine execution 之间。[[llm-inference-serving-project-map]] 的 D1/D2 区分 Gateway、Proxy/EPP/Router 与 Model Server；不要把 routing layer 与 engine 当成直接替代品。

# wiki/concepts/disaggregated-serving.md
## 在 M4 中的位置
P/D 分离同时改变 D2 请求路径与 D4 KV 生命周期：Prefill/Decode 独立扩缩，transfer metadata 与 KV data 通过明确的 backend contract 传递。参见 [[llm-inference-serving-project-map]]。

# wiki/concepts/kv-cache-offload.md
## 在 M4 中的位置
KV offload 是 D4 状态生命周期的一条分支。local KV layout 属于 engine；indexing、locality-aware routing、cross-worker transfer 与 remote tier 可由外围 serving layer 提供。参见 [[llm-inference-serving-project-map]]。
```

- [ ] **Step 4: Add project responsibility to each Entity**

Set all five Entity dates to `2026-09-22`. Add `## 在 M4 模块地图中的位置` before `相关页面` or at the end, using these responsibility statements and linking both Analysis pages:

```text
vLLM: engine layer; request scheduling, model execution, attention backend, local KV; external routing/autoscaling is separate.
SGLang: engine/runtime layer; scheduler, RadixCache and execution; P/D/distributed integrations connect to an outer serving layer.
Dynamo: distributed serving runtime around pluggable engines; frontend/routing, discovery/events, worker roles, KV transfer and planning.
llm-d: Kubernetes routing/serving stack; Proxy/EPP and InferencePool connect Gateway traffic, routing signals and model-server pods.
AIBrix: Kubernetes inference control plane; routing, autoscaling, model/adapter lifecycle, runtime and KV/multi-role orchestration.
```

Write the final text in concise Chinese. Do not add another diagram to these short Entity pages.

- [ ] **Step 5: Verify the backlinks**

Run:

```bash
for f in wiki/entities/vllm.md wiki/entities/sglang.md wiki/entities/dynamo.md wiki/entities/llm-d.md wiki/entities/aibrix.md; do
  rg -q '^date: 2026-09-22$' "$f" || exit 1
  rg -q '^## 在 M4 模块地图中的位置$' "$f" || exit 1
  rg -q '\[\[llm-inference-serving-project-map\]\]' "$f" || exit 1
done
for f in wiki/concepts/llm-inference.md wiki/concepts/inference-routing.md wiki/concepts/disaggregated-serving.md wiki/concepts/kv-cache-offload.md; do
  rg -q '^date: 2026-09-22$' "$f" || exit 1
  rg -q '\[\[llm-inference-serving-project-map\]\]' "$f" || exit 1
done
```

Expected: exit 0.

- [ ] **Step 6: Commit Concept/Entity synchronization**

Run:

```bash
git add wiki/concepts/llm-inference.md wiki/concepts/inference-routing.md \
  wiki/concepts/disaggregated-serving.md wiki/concepts/kv-cache-offload.md \
  wiki/entities/vllm.md wiki/entities/sglang.md wiki/entities/dynamo.md \
  wiki/entities/llm-d.md wiki/entities/aibrix.md
git commit -m "query: Link M4 concepts and projects"
```

### Task 5: Publish navigation, log, and generated HTML

**Files:**

- Modify: `wiki/index.md:94-105,157-169,316-338`
- Modify: `wiki/log.md` (append only)
- Regenerate: `wiki/html/index.html`, `wiki/html/log.html`, and HTML counterparts for all pages changed in Tasks 1–4

- [ ] **Step 1: Prove the new navigation wording is absent**

Run:

```bash
rg -n 'M4 模块地图|engine → routing → distributed runtime' wiki/index.md
```

Expected: exit 1 with no matches.

- [ ] **Step 2: Update the existing index sections**

Make these exact changes without adding a new category:

1. In `LLM Serving / AI Gateway`, describe vLLM/SGLang as engines, Dynamo as distributed runtime, llm-d as Kubernetes routing/serving stack, and AIBrix as Kubernetes inference control plane.
2. Describe `[[llm-inference-serving-project-map]]` as the D1–D5 module map.
3. Describe `[[llm-serving-engine-selection-map]]` as “先选架构层，再选项目组合”.
4. Add this wording to the existing LLM Serving reading path:

```text
M4 模块地图：engine → routing → distributed runtime / K8s control plane → KV/GPU infrastructure
```

- [ ] **Step 3: Append one durable log entry**

Append:

```markdown
## [2026-09-22] query | M4 Inference / Serving / Routing 模块地图更新

- 基于 vLLM、SGLang、Dynamo、llm-d、AIBrix 当前官方仓库与文档，重构 [[llm-inference-serving-project-map]]，新增模块边界、在线请求、控制循环、KV 生命周期和故障边界图。
- 更新 [[llm-serving-engine-selection-map]]，把“引擎选型”改成 engine、distributed runtime、Kubernetes routing/control plane 和 infrastructure 的分层组合决策。
- 同步相关 Entity、Concept、[[Wiki 索引]] 与生成 HTML；保留 2026-09-13/14 Source 摘要及其 ASCII 图不变。
```

- [ ] **Step 4: Check frontmatter and wikilink targets**

Run:

```bash
python3 - <<'PY'
from pathlib import Path
import re

root = Path('wiki')
targets = {p.stem.lower() for p in root.rglob('*.md')}
changed = [
    Path('wiki/analysis/llm-inference-serving-project-map.md'),
    Path('wiki/analysis/llm-serving-engine-selection-map.md'),
    Path('wiki/concepts/llm-inference.md'),
    Path('wiki/concepts/inference-routing.md'),
    Path('wiki/concepts/disaggregated-serving.md'),
    Path('wiki/concepts/kv-cache-offload.md'),
    Path('wiki/entities/vllm.md'), Path('wiki/entities/sglang.md'),
    Path('wiki/entities/dynamo.md'), Path('wiki/entities/llm-d.md'),
    Path('wiki/entities/aibrix.md'),
]
missing = []
for path in changed:
    text = path.read_text()
    assert text.startswith('---\n'), f'{path}: missing frontmatter start'
    assert text.count('---\n') >= 2, f'{path}: missing frontmatter end'
    for raw in re.findall(r'\[\[([^\]|#]+)', text):
        key = raw.strip().split('/')[-1].lower()
        if key not in targets and key != 'wiki 索引':
            missing.append((path, raw))
if missing:
    raise SystemExit('\n'.join(f'{p}: missing [[{t}]]' for p, t in missing))
print(f'checked {len(changed)} pages; missing wikilinks: 0')
PY
```

Expected: `checked 11 pages; missing wikilinks: 0`.

- [ ] **Step 5: Rebuild and inspect generated pages**

Run:

```bash
./wiki/html-assets/build.py
rg -n 'D1 · 模块边界图|D2 · 在线请求热路径|D3 · 扩缩与部署控制循环|D4 · KV 状态生命周期|D5 · 故障与降级边界' \
  wiki/html/analysis/llm-inference-serving-project-map.html
rg -n '先选层，再选项目|决策流程图|组合方案' \
  wiki/html/analysis/llm-serving-engine-selection-map.html
rg -n 'M4 模块地图' wiki/html/index.html
```

Expected: build exits 0 and every new heading appears in generated HTML.

- [ ] **Step 6: Check the final diff and commit generated output**

Run:

```bash
git diff --check
git status --short
git diff --stat
git add wiki/index.md wiki/log.md wiki/html
git commit -m "query: Publish M4 inference serving refresh"
```

Expected: no whitespace errors; only planned Markdown/generated files; commit succeeds.

### Task 6: Final requirements audit

**Files:**

- Verify: `docs/superpowers/specs/2026-09-22-wiki-module-map-refresh-design.md`
- Verify: all M4 files named above

- [ ] **Step 1: Review the complete M4 change range**

Resolve the plan commit as the pre-implementation base, then inspect the range:

```bash
M4_BASE_SHA=$(git log --format=%H --grep='^query: Plan M4 inference serving refresh$' -1)
test -n "$M4_BASE_SHA"
git diff --name-only "$M4_BASE_SHA"..HEAD
```

Expected: the base SHA is non-empty; the range contains only planned M4 Markdown and matching generated HTML.

- [ ] **Step 2: Check D1–D5 and L2 backlinks**

Run:

```bash
rg -n '^## D[1-5] · ' wiki/analysis/llm-inference-serving-project-map.md
for f in wiki/entities/vllm.md wiki/entities/sglang.md wiki/entities/dynamo.md wiki/entities/llm-d.md wiki/entities/aibrix.md; do
  rg -q '\[\[llm-inference-serving-project-map\]\]' "$f" || exit 1
done
```

Expected: exactly five D headings and exit 0. The global L0 map remains deferred until all six modules are complete.

- [ ] **Step 3: Confirm protected content stayed unchanged**

Run:

```bash
M4_BASE_SHA=$(git log --format=%H --grep='^query: Plan M4 inference serving refresh$' -1)
test -n "$M4_BASE_SHA"
git diff --name-only "$M4_BASE_SHA"..HEAD | rg '^(raw/|wiki/sources/)' && exit 1 || exit 0
```

Expected: exit 0 and no output.

- [ ] **Step 4: Run final verification**

Run:

```bash
./wiki/html-assets/build.py
git diff --check
git status --short
```

Expected: build exit 0, no whitespace errors, and no uncommitted changes.
