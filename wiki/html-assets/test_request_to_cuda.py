#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "wiki"
BUILD_PATH = Path(__file__).with_name("build.py")

SPEC = importlib.util.spec_from_file_location("wiki_build", BUILD_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load wiki builder: {BUILD_PATH}")
build = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build
SPEC.loader.exec_module(build)

CATEGORIES = ("analysis", "concepts", "entities", "sources")
PLACEHOLDERS = ("TBD", "TODO", "FIXME", "待补")
NEW_SLUGS = (
    "llm-inference-request-lifecycle",
    "aibrix-inference-request-flow",
    "dynamo-inference-request-flow",
    "llm-d-inference-request-flow",
    "vllm-gpu-execution-path",
    "sglang-gpu-execution-path",
    "llm-gpu-kernel-execution-path",
)
OPS_SLUGS = (
    "vllm-operational-lifecycle",
    "vllm-production-operations-runbook",
)
PAGE_EXPECTED_DATES = {
    "llm-inference-request-lifecycle": "2026-10-12",
    "vllm-gpu-execution-path": "2026-10-12",
    "vllm-operational-lifecycle": "2026-10-12",
    "vllm-production-operations-runbook": "2026-10-12",
}
HANDCRAFTED_HTML_SHA256 = {
    "src-agent-sandbox-architecture.html": "fdba44d4044ebb43d079e64312961ea190b6604ad13c57abf4bae1fcb288a622",
    "src-agentgateway-architecture.html": "c8c864b2974cc837e7f1e867a00cbf2a7964de323ae8ad24ee38bbc7b23c1b3b",
    "src-claude-context-architecture.html": "d0e989a760a3694b3498ba64ac908c00046be4a3abe4e729ebbbd75367eaed59",
    "src-claude-mem-architecture.html": "08d79f7f87c78cc52f1fccc95a95f825f74bc36aaff211a1ac29e0b8e27bc374",
    "src-hiclaw-architecture.html": "1cd6e513069ef9dc1065153393a67fb9232b9360ed3e685e143f0a0dbb155f1a",
    "src-nanobot-architecture.html": "4dced8e8b319128eda6ad6566528df712750cfe4f134f5575f7041f9af7d30d2",
    "src-powermem-architecture.html": "fd83f3357f37f16d53c41fe8ee4e9500107fbd180d9b5d01dba2edf3aa040466",
}
BASELINE_MISSING_WIKILINKS = frozenset(
    {
        "AI Agent",
        "Hermes",
        "NVIDIA",
        "OpenClaw",
        "Wiki 索引",
        "[agent-memory-selection-matrix",
        "[agent-runtime-sandbox-selection-map",
        "[ai-ops",
        "[code-semantic-search-rag-map",
        "[coding-agent-selection-map",
        "[gateway-api",
        "[llm-serving-engine-selection-map",
        "[mcp-gateway-tooling-map",
        "agent-credential-isolation\\",
        "autogen",
        "cel",
        "crewai",
        "dra",
        "ebpf",
        "flash-attention",
        "gvisor",
        "hbone",
        "ingress-nginx",
        "istio",
        "k8s-crd",
        "k8s-operator",
        "kata-containers",
        "kine",
        "langgraph",
        "llm-d-core-projects-architecture",
        "matrix-protocol",
        "mooncake",
        "nacos",
        "network-policy",
        "openclaw",
        "opentelemetry",
        "prefill-decode-disaggregation",
        "speculative-decoding",
        "xds",
    }
)


def load_markdown(slug: str) -> tuple[Path, str]:
    for category in CATEGORIES:
        path = WIKI / category / f"{slug}.md"
        if path.is_file():
            return path, path.read_text(encoding="utf-8")
    raise AssertionError(f"missing wiki page: {slug}")


def parse_page(slug: str) -> tuple[build.Frontmatter, str]:
    _path, text = load_markdown(slug)
    return build.parse_frontmatter(text)


def assert_frontmatter(
    test: unittest.TestCase, slug: str, expected_date: str = "2026-10-11"
) -> None:
    _path, text = load_markdown(slug)
    frontmatter, _body = build.parse_frontmatter(text)
    for key in ("title", "tags", "date", "sources", "related"):
        test.assertRegex(text, rf"(?m)^{key}:", f"{slug}: missing {key}")
    test.assertTrue(frontmatter.title, f"{slug}: empty title")
    test.assertTrue(frontmatter.tags, f"{slug}: empty tags")
    test.assertEqual(frontmatter.date, expected_date)
    test.assertTrue(frontmatter.related, f"{slug}: empty related")


def assert_headings(
    test: unittest.TestCase, slug: str, headings: tuple[str, ...]
) -> None:
    _frontmatter, body = parse_page(slug)
    for heading in headings:
        test.assertRegex(body, rf"(?m)^##+\s+{re.escape(heading)}\s*$", heading)


def count_ascii_diagrams(slug: str) -> int:
    _path, text = load_markdown(slug)
    return text.count("```text\n")


def collect_missing_wikilinks(paths: Iterable[Path]) -> set[str]:
    resolver = build.Resolver()
    missing: set[str] = set()
    for path in paths:
        for raw in build.WIKILINK_RE.findall(path.read_text(encoding="utf-8")):
            if resolver.resolve(raw) is None:
                target = raw.split("|", 1)[0].split("#", 1)[0].strip()
                missing.add(target)
    return missing


class RequestToCudaWikiTest(unittest.TestCase):
    def assert_common_page_contract(
        self, slug: str, expected_date: str = "2026-10-11"
    ) -> str:
        assert_frontmatter(self, slug, expected_date)
        _path, text = load_markdown(slug)
        for placeholder in PLACEHOLDERS:
            self.assertNotIn(placeholder, text, f"{slug}: placeholder {placeholder}")
        self.assertEqual(text.count("```" ) % 2, 0, f"{slug}: unbalanced fences")
        return text

    def test_overview_contract(self) -> None:
        slug = "llm-inference-request-lifecycle"
        text = self.assert_common_page_contract(slug, PAGE_EXPECTED_DATES[slug])
        assert_headings(
            self,
            slug,
            (
                "如何选择一条路径",
                "L0–L8 端到端总图",
                "请求对象如何演化",
                "聚合式与 P/D 的分叉",
                "控制面为什么不在 Token 热路径",
                "阅读顺序",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 4)
        downstream = (
            "aibrix-inference-request-flow",
            "dynamo-inference-request-flow",
            "llm-d-inference-request-flow",
            "vllm-gpu-execution-path",
            "sglang-gpu-execution-path",
            "llm-gpu-kernel-execution-path",
        )
        for target in downstream:
            self.assertIn(f"[[{target}]]", text)
        for arrow in ("──►", "··►", "══►"):
            self.assertIn(arrow, text)

    def test_gpu_kernel_contract(self) -> None:
        slug = "llm-gpu-kernel-execution-path"
        text = self.assert_common_page_contract(slug)
        assert_headings(
            self,
            slug,
            (
                "Host 到 Device",
                "Grid、Block、Warp 与 SM",
                "GPU 内存层级",
                "Tensor Core 与 CUDA Core",
                "Transformer 单层 Kernel 序列",
                "GEMM Tiling",
                "Attention Tiling",
                "CUDA Graph",
                "Kernel Fusion",
                "NCCL 与 NIXL",
                "性能观测",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 10)
        terms = (
            "HBM",
            "L2",
            "shared memory",
            "register",
            "LD/ST",
            "MMA",
            "occupancy",
            "Nsight Systems",
            "Nsight Compute",
        )
        for term in terms:
            self.assertIn(term, text)
        self.assertIn("276fbcff2717bd934cfa37c8a2e4c391f3e7237b", text)
        self.assertIn("e328c7ecbd69ebf77f38db9aa64eecefd760fe4b", text)

    def test_vllm_contract(self) -> None:
        slug = "vllm-gpu-execution-path"
        text = self.assert_common_page_contract(slug, PAGE_EXPECTED_DATES[slug])
        assert_headings(
            self,
            slug,
            (
                "进程与队列边界",
                "请求进入 EngineCore",
                "Scheduler 与 Continuous Batch",
                "KVCacheManager 与 Block Table",
                "GPUModelRunner",
                "Prefill、Chunked Prefill 与 Decode",
                "CUDA Graph 与 Attention Backend",
                "TP、PP、EP、DP",
                "P/D Connector 边界",
                "Token 返回与取消",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 7)
        self.assertIn("276fbcff2717bd934cfa37c8a2e4c391f3e7237b", text)
        symbols = (
            "AsyncLLM.generate",
            "EngineCore.step",
            "Scheduler.schedule",
            "Scheduler.update_from_output",
            "KVCacheManager.get_computed_blocks",
            "KVCacheManager.allocate_slots",
            "GPUModelRunner.execute_model",
            "GPUModelRunner.sample_tokens",
        )
        for symbol in symbols:
            self.assertIn(symbol, text)

    def test_vllm_operational_lifecycle_contract(self) -> None:
        slug = "vllm-operational-lifecycle"
        text = self.assert_common_page_contract(slug, "2026-10-12")
        assert_headings(
            self,
            slug,
            (
                "版本与证据边界",
                "Lifecycle 状态机",
                "Process / Engine / Worker / Daemon 所有权",
                "普通启动与 Preload 启动",
                "Warmup 与 Ready",
                "Drain 与 Pause",
                "Sleep Level 0/1/2",
                "Partial Wake 与 Reload Weights",
                "Preload Cache Modes",
                "LoRA 生命周期",
                "Shutdown 与 Restart",
                "资源状态矩阵",
                "失败与恢复边界",
                "外部控制面接口",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 7)
        for evidence_label in (
            "release-documented",
            "main-documented",
            "development-endpoint",
            "integration-dependent",
            "external-control-plane",
        ):
            self.assertIn(evidence_label, text)
        self.assertIn("v0.31.0", text)
        self.assertIn("c85616efc6f0eaa50ca1f1a09c32368aedffd3d8", text)
        for term in (
            "zero_copy",
            "ipc_cache",
            "weights",
            "kv_cache",
            "scheduling",
            "CUDA Graph",
            "NCCL",
        ):
            self.assertIn(term, text)
        self.assertRegex(
            text,
            r"zero_copy.{0,160}(?:不能|禁止|不兼容).{0,160}Sleep",
        )

    def test_vllm_operations_runbook_contract(self) -> None:
        slug = "vllm-production-operations-runbook"
        text = self.assert_common_page_contract(slug, "2026-10-12")
        assert_headings(
            self,
            slug,
            (
                "使用方式与版本标签",
                "启动前检查",
                "普通启动",
                "Preload Daemon",
                "Health、Startup 与 Readiness",
                "安全 Drain",
                "Sleep Level 0",
                "只释放 KV Cache",
                "Sleep Level 1",
                "Sleep Level 2 与权重更新",
                "Wake 与恢复流量",
                "LoRA 运维",
                "Graceful Shutdown",
                "Kubernetes Rolling Upgrade",
                "故障诊断树",
                "回滚",
                "Post-operation Checklist",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 5)
        for phase in (
            "PRECHECK",
            "REMOVE FROM ROUTING",
            "DRAIN/POLICY",
            "EXECUTE",
            "VERIFY",
            "RECOVER/ROLLBACK",
            "POSTCHECK",
        ):
            self.assertIn(phase, text)
        self.assertIn("VLLM_SERVER_DEV_MODE=1", text)
        self.assertRegex(text, r"zero_copy.{0,180}(?:不能|禁止|不兼容).{0,180}Sleep")
        self.assertRegex(text, r"(?:已输出|已经输出).{0,80}token.{0,100}(?:不能|不可).{0,80}透明")
        self.assertRegex(text, r"(?:单个|部分).{0,40}rank.{0,120}(?:整个|全部).{0,40}(?:group|实例组).{0,80}(?:unready|不可用|退出)")

    def test_vllm_operations_navigation_and_backlinks(self) -> None:
        wiki_paths = [
            candidate
            for category in CATEGORIES
            for candidate in (WIKI / category).glob("*.md")
        ] + [WIKI / "index.md", WIKI / "log.md"]
        for slug in OPS_SLUGS:
            inbound = [
                candidate
                for candidate in wiki_paths
                if candidate.stem not in OPS_SLUGS
                and f"[[{slug}" in candidate.read_text(encoding="utf-8")
            ]
            self.assertTrue(inbound, f"{slug}: no external inbound wikilink")

        _path, vllm_entity = load_markdown("vllm")
        for slug in OPS_SLUGS:
            self.assertIn(f"[[{slug}]]", vllm_entity)

        _path, reliability = load_markdown("llm-serving-reliability")
        self.assertIn("[[vllm-production-operations-runbook]]", reliability)
        _path, operator = load_markdown("model-serving-operator")
        self.assertIn("[[vllm-operational-lifecycle]]", operator)
        for analysis_slug in (
            "vllm-gpu-execution-path",
            "llm-inference-request-lifecycle",
        ):
            _path, analysis_text = load_markdown(analysis_slug)
            self.assertIn("[[vllm-operational-lifecycle]]", analysis_text)

        index = (WIKI / "index.md").read_text(encoding="utf-8")
        reading_path = (
            "[[vllm-operational-lifecycle]] → "
            "[[vllm-production-operations-runbook]]"
        )
        self.assertIn(reading_path, index)
        for slug in OPS_SLUGS:
            self.assertIn(f"[[{slug}]]", index)

        log = (WIKI / "log.md").read_text(encoding="utf-8")
        entry = "## [2026-10-12] query | Add vLLM operations lifecycle and runbook"
        self.assertEqual(log.count(entry), 1)

    def test_sglang_contract(self) -> None:
        slug = "sglang-gpu-execution-path"
        text = self.assert_common_page_contract(slug)
        assert_headings(
            self,
            slug,
            (
                "进程与 IPC 边界",
                "TokenizerManager",
                "Scheduler Event Loop",
                "ScheduleBatch 与 ForwardMode",
                "RadixCache",
                "Token 到 KV 分配",
                "ModelRunner",
                "Overlap 与 CUDA Graph",
                "TP、PP、EP",
                "P/D Bootstrap 边界",
                "Detokenizer 与流式返回",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 7)
        self.assertIn("e328c7ecbd69ebf77f38db9aa64eecefd760fe4b", text)
        symbols = (
            "TokenizerManager.generate_request",
            "TokenizerManager._send_one_request",
            "Scheduler.event_loop_normal",
            "Scheduler.get_next_batch_to_run",
            "ScheduleBatch.prepare_for_extend",
            "ScheduleBatch.prepare_for_decode",
            "RadixCache.match_prefix",
            "PagedTokenToKVPoolAllocator.alloc_extend",
            "PagedTokenToKVPoolAllocator.alloc_decode",
            "ModelRunner.forward",
            "ModelRunner.sample",
            "DetokenizerManager.event_loop",
        )
        for symbol in symbols:
            self.assertIn(symbol, text)

    def test_aibrix_contract(self) -> None:
        slug = "aibrix-inference-request-flow"
        text = self.assert_common_page_contract(slug)
        assert_headings(
            self,
            slug,
            (
                "支持矩阵",
                "vLLM × Aggregated",
                "vLLM × P/D",
                "SGLang × Aggregated",
                "SGLang × P/D",
                "KV Metadata / KV Payload / Token Stream",
                "失败与取消",
                "控制面旁路",
                "源码入口",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 6)
        self.assertIn("1d6472b83d2b70ce873dbd953add835e1ccc6a71", text)
        matrix_rows = (
            "| vLLM | Aggregated | documented |",
            "| vLLM | P/D | documented |",
            "| SGLang | Aggregated | tested |",
            "| SGLang | P/D | documented |",
        )
        for row in matrix_rows:
            self.assertIn(row, text)
        symbols = (
            "Server.Process",
            "Server.HandleRequestHeaders",
            "Server.HandleRequestBody",
            "pdRouter.Route",
            "pdRouter.filterPrefillDecodePods",
            "VLLMHandler.MergePrefillResponse",
            "SGLangHandler.AugmentPrefillRequest",
        )
        for symbol in symbols:
            self.assertIn(symbol, text)

    def test_dynamo_contract(self) -> None:
        slug = "dynamo-inference-request-flow"
        text = self.assert_common_page_contract(slug)
        assert_headings(
            self,
            slug,
            (
                "Frontend 与 Runtime 所有权",
                "支持矩阵",
                "vLLM × Aggregated",
                "vLLM × P/D",
                "SGLang × Aggregated",
                "SGLang × P/D",
                "KV-aware Routing",
                "Request / Event / Discovery Planes",
                "NIXL KV Transfer",
                "Token 返回",
                "失败、取消与迁移",
                "Planner / Operator 旁路",
                "源码入口",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 6)
        for arrow in ("──►", "··►", "══►"):
            self.assertIn(arrow, text)
        self.assertIn("b208989fbe1cfbfde64d11334d8af4ff04fe1a99", text)
        for row in (
            "| vLLM | Aggregated | documented |",
            "| vLLM | P/D | documented |",
            "| SGLang | Aggregated | documented |",
            "| SGLang | P/D | documented |",
        ):
            self.assertIn(row, text)
        symbols = (
            "frontend.async_main",
            "SelectionCore.select",
            "KvIndexer.find_match_details",
            "dynamo.vllm.handlers.DecodeWorkerHandler.generate",
            "dynamo.vllm.handlers.PrefillWorkerHandler.generate",
            "dynamo.sglang.request_handlers.llm.DecodeWorkerHandler.generate",
            "dynamo.sglang.request_handlers.llm.PrefillWorkerHandler.generate",
        )
        for symbol in symbols:
            self.assertIn(symbol, text)

    def test_llmd_contract(self) -> None:
        slug = "llm-d-inference-request-flow"
        text = self.assert_common_page_contract(slug)
        assert_headings(
            self,
            slug,
            (
                "Proxy / EPP / InferencePool 所有权",
                "支持矩阵",
                "vLLM × Aggregated",
                "vLLM × P/D",
                "SGLang × Aggregated",
                "SGLang × P/D",
                "EPP Filter → Score → Pick",
                "InferencePool",
                "P/D Coordinator",
                "KV Index 与 KV Payload",
                "流式返回",
                "失败与取消",
                "KEDA / HPA / DisaggregatedSet 旁路",
                "源码入口",
            ),
        )
        self.assertGreaterEqual(count_ascii_diagrams(slug), 6)
        for arrow in ("──►", "··►", "══►"):
            self.assertIn(arrow, text)
        self.assertIn("a9cf07a77a3016db21ae87134e5745b3a2d45ba6", text)
        self.assertIn("d870bcd132fc118b1433940a7842140275cc6cc9", text)
        for row in (
            "| vLLM | Aggregated | documented |",
            "| vLLM | P/D | documented |",
            "| SGLang | Aggregated | documented |",
            "| SGLang | P/D | documented |",
        ):
            self.assertIn(row, text)
        symbols = (
            "StreamingServer.Process",
            "Director.HandleRequest",
            "Scheduler.Schedule",
            "InferencePoolReconciler.Reconcile",
            "Server.handleInference",
            "sglangKV.PreparePrefillKVParams",
            "nixlKV.PrepareDecodeKVParams",
        )
        for symbol in symbols:
            self.assertIn(symbol, text)

    def test_navigation_and_backlinks(self) -> None:
        wiki_paths = [
            candidate
            for category in CATEGORIES
            for candidate in (WIKI / category).glob("*.md")
        ] + [WIKI / "index.md", WIKI / "log.md"]
        for slug in NEW_SLUGS:
            inbound = [
                candidate
                for candidate in wiki_paths
                if candidate.stem != slug
                and f"[[{slug}" in candidate.read_text(encoding="utf-8")
            ]
            self.assertTrue(inbound, f"{slug}: no inbound wikilink")

        index = (WIKI / "index.md").read_text(encoding="utf-8")
        for slug in NEW_SLUGS:
            self.assertIn(f"[[{slug}]]", index)
        reading_path = (
            "[[llm-inference-request-lifecycle]] → "
            "[[aibrix-inference-request-flow]] / [[dynamo-inference-request-flow]] / "
            "[[llm-d-inference-request-flow]] → [[vllm-gpu-execution-path]] / "
            "[[sglang-gpu-execution-path]] → [[llm-gpu-kernel-execution-path]]"
        )
        self.assertIn(reading_path, index)

        entity_targets = {
            "aibrix": "aibrix-inference-request-flow",
            "dynamo": "dynamo-inference-request-flow",
            "llm-d": "llm-d-inference-request-flow",
            "vllm": "vllm-gpu-execution-path",
            "sglang": "sglang-gpu-execution-path",
        }
        for entity, target in entity_targets.items():
            _path, text = load_markdown(entity)
            self.assertIn(f"[[{target}]]", text)

        concept_targets = {
            "llm-inference": "llm-inference-request-lifecycle",
            "inference-routing": "aibrix-inference-request-flow",
            "disaggregated-serving": "llm-d-inference-request-flow",
            "paged-attention": "vllm-gpu-execution-path",
            "radix-attention": "sglang-gpu-execution-path",
            "kv-cache-offload": "dynamo-inference-request-flow",
            "gpu-programming-learning": "llm-gpu-kernel-execution-path",
        }
        for concept, target in concept_targets.items():
            _path, text = load_markdown(concept)
            self.assertIn(f"[[{target}]]", text)

        log = (WIKI / "log.md").read_text(encoding="utf-8")
        entry = "## [2026-10-11] query | Trace inference requests from gateways to CUDA"
        self.assertEqual(log.count(entry), 1)

    def test_global_content_integrity(self) -> None:
        total_diagrams = 0
        fixed_shas = {
            "aibrix-inference-request-flow": "1d6472b83d2b70ce873dbd953add835e1ccc6a71",
            "dynamo-inference-request-flow": "b208989fbe1cfbfde64d11334d8af4ff04fe1a99",
            "llm-d-inference-request-flow": "d870bcd132fc118b1433940a7842140275cc6cc9",
            "vllm-gpu-execution-path": "276fbcff2717bd934cfa37c8a2e4c391f3e7237b",
            "sglang-gpu-execution-path": "e328c7ecbd69ebf77f38db9aa64eecefd760fe4b",
        }
        for slug in NEW_SLUGS:
            text = self.assert_common_page_contract(
                slug, PAGE_EXPECTED_DATES.get(slug, "2026-10-11")
            )
            total_diagrams += count_ascii_diagrams(slug)
            if slug in fixed_shas:
                self.assertIn(fixed_shas[slug], text)
                self.assertIn("https://github.com/", text)
        self.assertGreaterEqual(total_diagrams, 40)

        allowed_statuses = {
            "documented",
            "tested",
            "experimental",
            "conceptual",
            "unsupported / not found",
        }
        support_row = re.compile(
            r"(?m)^\| (vLLM|SGLang) \| (Aggregated|P/D) \| ([^|]+?) \|"
        )
        for slug in (
            "aibrix-inference-request-flow",
            "dynamo-inference-request-flow",
            "llm-d-inference-request-flow",
        ):
            _path, text = load_markdown(slug)
            rows = support_row.findall(text)
            self.assertEqual(len(rows), 4, f"{slug}: support matrix size")
            self.assertEqual(
                {(engine, mode) for engine, mode, _status in rows},
                {
                    ("vLLM", "Aggregated"),
                    ("vLLM", "P/D"),
                    ("SGLang", "Aggregated"),
                    ("SGLang", "P/D"),
                },
            )
            for _engine, _mode, status in rows:
                self.assertIn(status.strip(), allowed_statuses)

        all_markdown = [
            candidate
            for category in CATEGORIES
            for candidate in (WIKI / category).glob("*.md")
        ] + [WIKI / "index.md", WIKI / "log.md"]
        current_missing = collect_missing_wikilinks(all_markdown)
        self.assertFalse(
            current_missing - BASELINE_MISSING_WIKILINKS,
            f"new missing wikilinks: {sorted(current_missing - BASELINE_MISSING_WIKILINKS)}",
        )

        raw_diff = subprocess.run(
            ["git", "diff", "--quiet", "71030f1", "--", "raw"], cwd=ROOT
        )
        self.assertEqual(raw_diff.returncode, 0, "raw/ changed from implementation base")
        for filename, expected in HANDCRAFTED_HTML_SHA256.items():
            content = (WIKI / "html" / "sources" / filename).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), expected, filename)

    def test_generated_output(self) -> None:
        generated_pages: dict[str, Path] = {}
        for slug in NEW_SLUGS:
            html_path = WIKI / "html" / "analysis" / f"{slug}.html"
            self.assertTrue(html_path.is_file(), f"missing generated page: {slug}")
            generated_pages[slug] = html_path
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("<pre><code class=\"language-text\">", html)
            self.assertNotIn("wikilink-missing", html)

            for href in re.findall(r'href="([^"]+)"', html):
                if href.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                target_ref = href.split("#", 1)[0].split("?", 1)[0]
                if not target_ref:
                    continue
                target = (html_path.parent / target_ref).resolve()
                self.assertTrue(target.exists(), f"{slug}: missing href target {href}")

        overview_html = generated_pages[
            "llm-inference-request-lifecycle"
        ].read_text(encoding="utf-8")
        self.assertIn("L0–L8 端到端总图", overview_html)
        self.assertIn("──►", overview_html)

        graph = json.loads((WIKI / "html" / "graph.json").read_text(encoding="utf-8"))
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertTrue(set(NEW_SLUGS) <= node_ids)
        edges = {(edge["source"], edge["target"]) for edge in graph["edges"]}
        overview = "llm-inference-request-lifecycle"
        for target in NEW_SLUGS[1:]:
            self.assertIn((overview, target), edges)


if __name__ == "__main__":
    unittest.main()
