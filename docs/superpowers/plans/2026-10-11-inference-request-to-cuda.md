# Inference Request to CUDA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a seven-page, source-anchored learning path that traces AIBrix, Dynamo, and llm-d requests through vLLM or SGLang, in aggregated or P/D mode, down to CUDA kernels and NVIDIA GPU execution units.

**Architecture:** Use one navigation/mental-model page, three platform request-flow pages, two engine execution pages, and one shared GPU-kernel page. Keep stable mechanisms in existing Concept pages, version-sensitive call chains in Analysis pages, and use fixed upstream commits plus evidence-status labels so an unsupported combination is never presented as a working path.

**Tech Stack:** Markdown, YAML frontmatter, Obsidian wikilinks, ASCII diagrams, Python `unittest`, GitHub API/official documentation, existing Python Markdown HTML builder, Git.

**Spec:** `docs/superpowers/specs/2026-10-11-inference-request-to-cuda-design.md`

## Global Constraints

- Create all seven new pages under `wiki/analysis/`; do not modify `raw/` or rewrite historical raw-backed Source pages as current facts.
- Cover both engines (`vLLM`, `SGLang`) and both serving shapes (`aggregated`, `P/D`) on every platform page.
- Label each support-matrix cell exactly as `documented`, `tested`, `experimental`, `conceptual`, or `unsupported / not found` and attach a fixed-commit primary source.
- For `conceptual` or `unsupported / not found`, document the confirmed boundary and missing evidence; do not fabricate a success sequence.
- Use Markdown `text` fences for diagrams, with wikilinks in surrounding prose rather than inside diagram fences.
- Distinguish request/control metadata (`──►`), asynchronous event/control feedback (`··►`), and bulk tensor/KV movement (`══►`); label `[CPU]`, `[GPU]`, and `[NET]` boundaries.
- Separate gateway selection, KV index metadata, KV payload transfer, engine execution, CUDA/NCCL kernels, and Kubernetes reconciliation.
- Pin repository observations to official upstream commits resolved during execution on 2026-10-11; do not treat a local fork or default-branch HEAD as a release.
- Preserve the unrelated untracked file `docs/superpowers/specs/2026-09-28-m5d-platform-gpu-integration-design.md`.
- Do not change the HTML builder or add a diagram runtime; existing generated HTML must render the ASCII diagrams unchanged.
- Final durable wiki content must have complete `title`, `tags`, `date`, `sources`, and `related` frontmatter and no new unresolved wikilinks or orphan pages.

## Review Focus

- A local fork or stale clone differs from official upstream: pages must cite the canonical repository and pinned upstream SHA, while clearly identifying local evidence as stale or forked; tested in Task 1 and each repository task.
- A platform/engine/mode combination lacks end-to-end evidence: its section must say what is known and missing, and must not contain a fabricated success sequence; tested in Tasks 5–7.
- A diagram accidentally mixes control metadata, KV payload, and token streaming: each P/D page must use the three arrow classes and explicit execution-location labels; tested in Tasks 5–7.
- “CUDA core” is used as a synonym for all GPU work: the GPU page must distinguish Tensor Core MMA, CUDA-core scalar/vector work, LD/ST, memory hierarchy, and NCCL/NIXL; tested in Task 2.
- New pages render but are undiscoverable or contain broken links: Index, Concept/Entity backlinks, graph nodes, local HTML links, and the no-new-missing baseline must all pass; tested in Tasks 8–9.

---

## File Map

**Create**

- `wiki/analysis/llm-inference-request-lifecycle.md` — navigation, common object lifecycle, shared L0–L8 vocabulary.
- `wiki/analysis/aibrix-inference-request-flow.md` — AIBrix support matrix and four request paths.
- `wiki/analysis/dynamo-inference-request-flow.md` — Dynamo support matrix and four request paths.
- `wiki/analysis/llm-d-inference-request-flow.md` — llm-d support matrix and four request paths.
- `wiki/analysis/vllm-gpu-execution-path.md` — vLLM V1 request, scheduler, KV, model-runner, and kernel handoff.
- `wiki/analysis/sglang-gpu-execution-path.md` — SGLang tokenizer/scheduler/radix-cache/model-runner and kernel handoff.
- `wiki/analysis/llm-gpu-kernel-execution-path.md` — framework-op to SM/warp/Tensor Core/CUDA-core execution.
- `wiki/html-assets/test_request_to_cuda.py` — structural, evidence-label, diagram, backlink, and generated-output contracts.

**Modify**

- `wiki/concepts/llm-inference.md`
- `wiki/concepts/disaggregated-serving.md`
- `wiki/concepts/inference-routing.md`
- `wiki/concepts/paged-attention.md`
- `wiki/concepts/radix-attention.md`
- `wiki/concepts/kv-cache-offload.md`
- `wiki/concepts/gpu-programming-learning.md`
- `wiki/entities/aibrix.md`
- `wiki/entities/dynamo.md`
- `wiki/entities/llm-d.md`
- `wiki/entities/vllm.md`
- `wiki/entities/sglang.md`
- `wiki/index.md`
- `wiki/log.md`
- Generated `wiki/html/**` files produced by `wiki/html-assets/build.py`

## Shared Test Interfaces

`wiki/html-assets/test_request_to_cuda.py` grows with the content. Define and keep these helpers stable:

- `load_markdown(slug: str) -> tuple[Path, str]`
- `parse_page(slug: str) -> tuple[build.Frontmatter, str]`
- `assert_frontmatter(test: unittest.TestCase, slug: str) -> None`
- `assert_headings(test: unittest.TestCase, slug: str, headings: tuple[str, ...]) -> None`
- `count_ascii_diagrams(slug: str) -> int`
- `collect_missing_wikilinks(paths: Iterable[Path]) -> set[str]`

Also capture `BASELINE_MISSING_WIKILINKS: frozenset[str]` in Task 1 from the pre-change wiki so the final check can distinguish pre-existing debt from new breakage.

Every page-specific test also asserts the absence of `TBD`, `TODO`, `FIXME`, and `待补`, balanced code fences, at least one inbound wikilink after Task 8, and `date: 2026-10-11`.

### Task 1: Common Request-Lifecycle Entry Page

**Files:**

- Create: `wiki/analysis/llm-inference-request-lifecycle.md`
- Create: `wiki/html-assets/test_request_to_cuda.py`
- Reference: `wiki/concepts/llm-inference.md`
- Reference: `wiki/analysis/llm-inference-serving-project-map.md`
- Reference: `docs/superpowers/specs/2026-10-11-inference-request-to-cuda-design.md`

**Interfaces:**

- Consumes: Existing wiki frontmatter conventions, builder `parse_frontmatter`, current LLM-serving project vocabulary.
- Produces: Canonical slugs for all seven pages; shared L0–L8 layer names; object lifecycle `JSON → normalized request → token IDs → scheduler request → batch/tensors → logits → sampled token → SSE`; arrow legend used verbatim by Tasks 2–7.

- [ ] **Step 1: Capture the immutable baseline**

Run `git status --short`, `git rev-parse HEAD`, and record hashes for `raw/` plus hand-crafted HTML files. Confirm the existing untracked M5-D design remains outside this change. Check `.codegraph/` in every local target repository before using `rg`; use CodeGraph first only where the index exists.

- [ ] **Step 2: Add the failing overview contract**

Create the shared helpers and `RequestToCudaWikiTest.test_overview_contract`. Assert complete frontmatter; exact headings `如何选择一条路径`, `L0–L8 端到端总图`, `请求对象如何演化`, `聚合式与 P/D 的分叉`, `控制面为什么不在 Token 热路径`, `阅读顺序`; at least four `text` diagrams; links to the six downstream pages; and the three arrow forms.

- [ ] **Step 3: Run the targeted test and verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_overview_contract -v`

Expected: FAIL because `wiki/analysis/llm-inference-request-lifecycle.md` does not exist.

- [ ] **Step 4: Write the overview page**

Add full frontmatter with `sources: []` and related links to the six downstream pages plus existing `[[llm-inference]]`, `[[disaggregated-serving]]`, and `[[inference-routing]]`. Include the L0–L8 diagram, request-object timeline, aggregated/P-D fork, control-plane side loop, route-selection matrix, and terminology table. State that the four platform quadrants are evidence questions, not assumed support.

- [ ] **Step 5: Run the overview contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_overview_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the entry page and test harness**

```bash
git add wiki/analysis/llm-inference-request-lifecycle.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Add inference request lifecycle entry"
```

### Task 2: GPU Kernel and Microarchitecture Downlink

**Files:**

- Create: `wiki/analysis/llm-gpu-kernel-execution-path.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: Official NVIDIA CUDA C++ Programming Guide, PTX ISA, Nsight documentation, NCCL documentation, NIXL documentation, and fixed-commit vLLM/SGLang kernel sources.

**Interfaces:**

- Consumes: Task 1 L6–L8 names and arrow legend.
- Produces: Shared handoff contract `framework op → dispatcher/compiler → host launch → CUDA stream/grid/block → warp/SM → memory/compute units → output`; stable glossary used by Tasks 3–4.

- [ ] **Step 1: Pin primary GPU evidence**

Record access date and official URLs for CUDA programming model, memory hierarchy, Tensor Core/WMMA or MMA, CUDA Graph, Nsight Systems/Compute, NCCL, and NIXL. For vLLM/SGLang kernel examples, resolve official upstream SHAs and fixed-commit paths; do not cite only a local clone.

- [ ] **Step 2: Add the failing GPU-page contract**

Add `test_gpu_kernel_contract`. Require headings `Host 到 Device`, `Grid、Block、Warp 与 SM`, `GPU 内存层级`, `Tensor Core 与 CUDA Core`, `Transformer 单层 Kernel 序列`, `GEMM Tiling`, `Attention Tiling`, `CUDA Graph`, `Kernel Fusion`, `NCCL 与 NIXL`, `性能观测`; at least ten diagrams; and terms `HBM`, `L2`, `shared memory`, `register`, `LD/ST`, `MMA`, `occupancy`, `Nsight Systems`, `Nsight Compute`.

- [ ] **Step 3: Verify the targeted test fails**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_gpu_kernel_contract -v`

Expected: FAIL because the GPU page is missing.

- [ ] **Step 4: Write the GPU page**

Explain host/runtime/driver launch, streams and asynchronous execution; grid/block/warp/SM residency; HBM→L2→shared→register data movement; Tensor Core MMA versus CUDA-core auxiliary arithmetic; embedding, RMSNorm, RoPE, QKV, attention, projection, SwiGLU/MLP, MoE, logits and sampling kernels; GEMM and attention tiling; CUDA Graph; fusion/occupancy trade-offs; NCCL collectives; NIXL/RDMA/IPC KV movement; and profiler symptom mapping. Include one dense Transformer-layer timeline and one single-token-decode timeline.

- [ ] **Step 5: Run and pass the GPU contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_gpu_kernel_contract -v`

Expected: PASS with at least ten diagrams.

- [ ] **Step 6: Commit the GPU downlink**

```bash
git add wiki/analysis/llm-gpu-kernel-execution-path.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Explain LLM kernels down to CUDA execution"
```

### Task 3: vLLM Request-to-Kernel Execution Path

**Files:**

- Create: `wiki/analysis/vllm-gpu-execution-path.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: `/Users/zhenyu.jiang/vllm` only if its commit matches official upstream evidence; otherwise use fixed-commit GitHub content.

**Interfaces:**

- Consumes: Task 1 request-object vocabulary and Task 2 GPU handoff/glossary.
- Produces: vLLM handoff anchors for Tasks 5–7: API/EngineClient, EngineCore, Scheduler, KVCacheManager, Worker/GPUModelRunner, model forward, logits/sampler, streamed output.

- [ ] **Step 1: Resolve the current official vLLM snapshot and critical symbols**

Use `gh api repos/vllm-project/vllm/commits/main` to pin the SHA. Check `.codegraph/`; if present, use `codegraph explore` before `rg`. Trace one request upward and downward through API server/EngineClient, EngineCore queue/step, Scheduler, KVCacheManager, GPUModelRunner, attention backend, model layers/custom ops, sampler, and output update. Keep the critical-path reading set targeted; when it exceeds ten files, finish one call chain before starting the next.

- [ ] **Step 2: Add the failing vLLM contract**

Add `test_vllm_contract`. Require headings `进程与队列边界`, `请求进入 EngineCore`, `Scheduler 与 Continuous Batch`, `KVCacheManager 与 Block Table`, `GPUModelRunner`, `Prefill、Chunked Prefill 与 Decode`, `CUDA Graph 与 Attention Backend`, `TP、PP、EP、DP`, `P/D Connector 边界`, `Token 返回与取消`; at least seven diagrams; fixed-SHA links; and a source-entry table containing exact current symbols found in Step 1.

- [ ] **Step 3: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_vllm_contract -v`

Expected: FAIL because the vLLM page is missing.

- [ ] **Step 4: Write the vLLM page from the traced symbols**

Describe object transformations and CPU/process/GPU boundaries, token-budget scheduling, prefix lookup/block allocation, model input preparation, eager/compile/CUDA Graph selection, Dense and MoE layer paths, collectives, logits/sampling, and the exact point where a platform P/D connector hands KV metadata/data into or out of vLLM. Mark every version-sensitive statement with its pinned commit.

- [ ] **Step 5: Run and pass the vLLM contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_vllm_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the vLLM path**

```bash
git add wiki/analysis/vllm-gpu-execution-path.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Trace vLLM requests to GPU kernels"
```

### Task 4: SGLang Request-to-Kernel Execution Path

**Files:**

- Create: `wiki/analysis/sglang-gpu-execution-path.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: `/Users/zhenyu.jiang/sglang` only if its commit matches official upstream evidence; otherwise use fixed-commit GitHub content.

**Interfaces:**

- Consumes: Task 1 object vocabulary and Task 2 GPU handoff/glossary.
- Produces: SGLang handoff anchors for Tasks 5–7: HTTP server/TokenizerManager, IPC, Scheduler event loop, ScheduleBatch/forward mode, RadixCache, token-to-KV allocator, ModelRunner, logits/sampling, detokenizer/stream.

- [ ] **Step 1: Resolve the current official SGLang snapshot and critical symbols**

Pin `sgl-project/sglang` main SHA, prefer CodeGraph if indexed, and trace one request through server/TokenizerManager, IPC, Scheduler event loop, waiting/running queues, ScheduleBatch/forward modes, RadixCache, KV allocator, ModelRunner, attention backend/model ops, sampler, and detokenizer. Separately trace overlap scheduling and P/D bootstrap/connector boundaries only after the base path is complete.

- [ ] **Step 2: Add the failing SGLang contract**

Add `test_sglang_contract`. Require headings `进程与 IPC 边界`, `TokenizerManager`, `Scheduler Event Loop`, `ScheduleBatch 与 ForwardMode`, `RadixCache`, `Token 到 KV 分配`, `ModelRunner`, `Overlap 与 CUDA Graph`, `TP、PP、EP`, `P/D Bootstrap 边界`, `Detokenizer 与流式返回`; at least seven diagrams; fixed-SHA links; and current symbols from Step 1.

- [ ] **Step 3: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_sglang_contract -v`

Expected: FAIL because the SGLang page is missing.

- [ ] **Step 4: Write the SGLang page from the traced symbols**

Explain the true SGLang abstractions rather than substituting vLLM terminology. Cover extend/decode forward modes, RadixCache ownership/refcounts/eviction, batch construction, input preparation, backend selection, overlap boundaries, Dense/MoE and collectives, sampling/detokenization, and the engine-side P/D bootstrap/handoff contract.

- [ ] **Step 5: Run and pass the SGLang contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_sglang_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the SGLang path**

```bash
git add wiki/analysis/sglang-gpu-execution-path.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Trace SGLang requests to GPU kernels"
```

### Task 5: AIBrix Four-Quadrant Request Flow

**Files:**

- Create: `wiki/analysis/aibrix-inference-request-flow.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: Official fixed-commit `vllm-project/aibrix` content; existing `wiki/entities/aibrix.md` and `wiki/sources/src-aibrix-architecture.md` only as historical context.

**Interfaces:**

- Consumes: Task 3 vLLM and Task 4 SGLang handoff anchors plus Task 1 arrow legend.
- Produces: AIBrix support matrix and platform-to-engine handoff descriptions used by navigation/backlink Task 8.

- [ ] **Step 1: Pin AIBrix upstream and trace platform paths**

Resolve canonical URL and main SHA with GitHub API. Trace Gateway/Envoy extension or plugin request handling, model/routing selection, endpoint dispatch, streaming response, vLLM P/D handoff, SGLang handoff, and relevant tests/configs. Use architecture and P/D documents as primary explanation, but downgrade any combination that appears only in development mocks or isolated unit tests.

- [ ] **Step 2: Add the failing AIBrix contract**

Add `test_aibrix_contract`. Require a 2×2 support matrix with all allowed statuses, headings for all four combinations, `KV Metadata / KV Payload / Token Stream`, `失败与取消`, `控制面旁路`, and `源码入口`; at least six diagrams. Add an assertion that any non-`documented`/non-`tested` quadrant contains `缺失证据` and does not contain a success-only sequence labeled as production.

- [ ] **Step 3: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_aibrix_contract -v`

Expected: FAIL because the AIBrix page is missing.

- [ ] **Step 4: Write the AIBrix page**

Follow the common platform template. Draw separate diagrams only for evidence-supported quadrants; for weaker quadrants draw the confirmed boundary and explicitly stop where evidence ends. Explain gateway selection versus request proxying, routing signals, P/D metadata and payload, engine handoff, stream return, cancel/timeout, stale state, KV miss, worker loss, and model/adapter/autoscaling control loops outside the token hot path.

- [ ] **Step 5: Run and pass the AIBrix contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_aibrix_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the AIBrix path**

```bash
git add wiki/analysis/aibrix-inference-request-flow.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Trace AIBrix inference request flows"
```

### Task 6: Dynamo Four-Quadrant Request Flow

**Files:**

- Create: `wiki/analysis/dynamo-inference-request-flow.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: Official fixed-commit `ai-dynamo/dynamo`; local `/Users/zhenyu.jiang/dynamo` is a fork and must not define current truth unless its commit matches upstream.

**Interfaces:**

- Consumes: Engine handoffs from Tasks 3–4 and GPU/NIXL boundary from Task 2.
- Produces: Dynamo support matrix; Frontend/Router/Runtime/worker/KV-transfer request flow; control-plane side-loop description for Task 8 backlinks.

- [ ] **Step 1: Pin Dynamo upstream and trace the four paths**

Resolve main SHA and inspect architecture, router, disaggregated-serving, vLLM backend, SGLang backend, NIXL/KV transfer, request cancellation/migration, and relevant recipe/test paths. Trace aggregated and P/D call chains independently for each engine; do not infer one backend from the other.

- [ ] **Step 2: Add the failing Dynamo contract**

Add `test_dynamo_contract`. Require headings for Frontend/Runtime ownership, support matrix, all four combinations, KV-aware routing, request/event/discovery planes, NIXL transfer, token return, failure/migration, Planner/Operator side loop, and source entries; at least six diagrams and all three arrow classes.

- [ ] **Step 3: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_dynamo_contract -v`

Expected: FAIL because the Dynamo page is missing.

- [ ] **Step 4: Write the Dynamo page**

Show Frontend normalization/tokenization where supported, router cost inputs, Runtime endpoint/request/event interactions, aggregated workers, PrefillRouter and decode selection, NIXL metadata/data movement, vLLM/SGLang handoffs, token streaming, and cancellation/migration limits. Draw Planner/Operator/discovery as asynchronous side paths rather than inline token calls.

- [ ] **Step 5: Run and pass the Dynamo contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_dynamo_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the Dynamo path**

```bash
git add wiki/analysis/dynamo-inference-request-flow.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Trace Dynamo inference request flows"
```

### Task 7: llm-d Four-Quadrant Request Flow

**Files:**

- Create: `wiki/analysis/llm-d-inference-request-flow.md`
- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Reference: Official fixed-commit `llm-d/llm-d` and canonical current router repository returned by GitHub API; existing Source pages remain historical snapshots.

**Interfaces:**

- Consumes: Engine handoffs from Tasks 3–4 and shared platform template.
- Produces: llm-d Gateway/Proxy/EPP/InferencePool/coordinator request flow and support matrix for Task 8 backlinks.

- [ ] **Step 1: Pin llm-d repositories and trace the four paths**

Resolve current SHAs and canonical URLs for the docs/recipes repository and router/inference-scheduler repository. Trace Gateway/Proxy request handling, ext-proc/EPP scheduling, InferencePool endpoint selection, request forwarding, vLLM and SGLang request preparation, P/D coordinator, KV index/offloader signals, and DisaggregatedSet/LeaderWorkerSet orchestration. Separate guide/CI evidence from runtime code evidence.

- [ ] **Step 2: Add the failing llm-d contract**

Add `test_llmd_contract`. Require headings for ownership, support matrix, all four combinations, EPP selection, InferencePool, P/D coordinator, KV index versus payload, streaming return, failure/cancel, KEDA/HPA/DisaggregatedSet side loops, and source entries; at least six diagrams and all three arrow classes.

- [ ] **Step 3: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_llmd_contract -v`

Expected: FAIL because the llm-d page is missing.

- [ ] **Step 4: Write the llm-d page**

Show Client→Gateway/Proxy→EPP decision→InferencePool endpoint→engine for aggregated paths, then coordinator-driven prefill/decode selection and KV transfer for P/D. Explain whether the selected endpoint is returned or proxied for each integration, keep KV index metadata distinct from KV bytes, and isolate Kubernetes orchestration/autoscaling from the request hot path.

- [ ] **Step 5: Run and pass the llm-d contract**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_llmd_contract -v`

Expected: PASS.

- [ ] **Step 6: Commit the llm-d path**

```bash
git add wiki/analysis/llm-d-inference-request-flow.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Trace llm-d inference request flows"
```

### Task 8: Connect Concepts, Entities, Index, and Log

**Files:**

- Modify: Seven Concept pages, five Entity pages, `wiki/index.md`, `wiki/log.md`, and `wiki/html-assets/test_request_to_cuda.py` listed in the File Map.

**Interfaces:**

- Consumes: All seven new page slugs, support summaries, and handoff terminology.
- Produces: Inbound links for every new Analysis page; one discoverable “请求到 CUDA” reading path; durable operation log entry.

- [ ] **Step 1: Add failing navigation and backlink contracts**

Add `test_navigation_and_backlinks`. Assert every new page has an inbound link outside itself; `wiki/index.md` contains all seven slugs under an Analysis entry and a reading path ordered overview→platform→engine→GPU; each of the five Entity pages links its corresponding flow/downlink; related Concept pages link only the layer they explain; and `wiki/log.md` contains exactly one `## [2026-10-11] query | Trace inference requests from gateways to CUDA` entry.

- [ ] **Step 2: Verify failure**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_navigation_and_backlinks -v`

Expected: FAIL because the existing pages do not link the new learning path.

- [ ] **Step 3: Update Concept pages without duplicating Analysis content**

Add concise “请求到 CUDA 中的位置” sections and frontmatter related links. Route routing concepts to platform pages, P/D/KV concepts to the platform/engine handoff, and GPU-programming concepts to the kernel page. Preserve historical claims and existing Source references.

- [ ] **Step 4: Update Entity pages**

Add current request-flow links and a compact support-boundary note to AIBrix, Dynamo, llm-d, vLLM, and SGLang. Do not copy diagrams or long call chains into Entity pages.

- [ ] **Step 5: Update Index and Log**

Add the seven Analysis entries and one reading path. Append the exact log heading from Step 1. Keep filenames lowercase-hyphenated and avoid duplicate index entries.

- [ ] **Step 6: Run and pass navigation/backlink contracts**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_navigation_and_backlinks -v`

Expected: PASS.

- [ ] **Step 7: Commit wiki integration**

```bash
git add wiki/concepts wiki/entities wiki/index.md wiki/log.md wiki/html-assets/test_request_to_cuda.py
git commit -m "query: Link the request-to-CUDA learning path"
```

### Task 9: Full Integrity, HTML Build, and Final Durable Commit

**Files:**

- Modify: `wiki/html-assets/test_request_to_cuda.py`
- Generate: `wiki/html/analysis/*.html`, affected Concept/Entity HTML, `wiki/html/index.html`, `wiki/html/log.html`, `wiki/html/graph.html`, `wiki/html/graph.json`, copied assets as produced by the builder.

**Interfaces:**

- Consumes: All content and links from Tasks 1–8.
- Produces: Reproducible HTML/graph output and final repository-wide evidence that the seven-page path is complete.

- [ ] **Step 1: Add failing final-integrity contracts before the build**

Add tests `test_global_content_integrity` and `test_generated_output`. The content test asserts all seven complete frontmatters, no placeholders, balanced fences, at least 40 total ASCII diagrams, every support status is from the allowed enum, fixed-SHA evidence links exist, `raw/` is unchanged, and no new missing wikilinks relative to the Task 1 baseline. The generated test asserts seven HTML files exist, contain their required headings/diagram text, have no `wikilink-missing` for new slugs, all local `href` targets/fragments exist, and all seven nodes plus expected edges appear in `graph.json`.

- [ ] **Step 2: Verify the generated-output test fails before rebuilding**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_generated_output -v`

Expected: FAIL because generated HTML/graph is stale or missing.

- [ ] **Step 3: Run the Markdown/content suite**

Run: `python3 wiki/html-assets/test_request_to_cuda.py -k test_global_content_integrity -v`

Expected: PASS. Fix content rather than weakening assertions if it fails.

- [ ] **Step 4: Build twice and prove idempotence**

Run `./wiki/html-assets/build.py`, capture hashes of generated files, run it again, and compare hashes.

Expected: Both builds succeed and the second build changes no generated-file hash.

- [ ] **Step 5: Run the complete verification set**

Run:

```bash
python3 wiki/html-assets/test_request_to_cuda.py -v
git diff --check
git status --short
```

Expected: All tests PASS; no whitespace errors; no `raw/`, unrelated M5-D spec, or hand-crafted HTML changes; only scoped Markdown, test, and generated files remain.

- [ ] **Step 6: Manually inspect representative generated pages**

Inspect overview, one platform P/D page, one engine page, and the GPU page at desktop and narrow widths. Verify code-block horizontal scrolling, diagram line preservation, readable tables, page navigation, and Concept/Entity backlinks.

- [ ] **Step 7: Commit final generated output and any verification fixes**

```bash
git add wiki/html wiki/html-assets/test_request_to_cuda.py wiki/analysis wiki/concepts wiki/entities wiki/index.md wiki/log.md
git commit -m "query: Trace inference requests from gateways to CUDA"
```

- [ ] **Step 8: Verify the committed tree**

Run the full unittest command, builder once, `git diff --check`, and `git status --short` after the commit.

Expected: Tests and build pass; tracked worktree is clean; only the pre-existing untracked `docs/superpowers/specs/2026-09-28-m5d-platform-gpu-integration-design.md` remains.
