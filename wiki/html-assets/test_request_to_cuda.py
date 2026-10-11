#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import re
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


def assert_frontmatter(test: unittest.TestCase, slug: str) -> None:
    _path, text = load_markdown(slug)
    frontmatter, _body = build.parse_frontmatter(text)
    for key in ("title", "tags", "date", "sources", "related"):
        test.assertRegex(text, rf"(?m)^{key}:", f"{slug}: missing {key}")
    test.assertTrue(frontmatter.title, f"{slug}: empty title")
    test.assertTrue(frontmatter.tags, f"{slug}: empty tags")
    test.assertEqual(frontmatter.date, "2026-10-11")
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
    def assert_common_page_contract(self, slug: str) -> str:
        assert_frontmatter(self, slug)
        _path, text = load_markdown(slug)
        for placeholder in PLACEHOLDERS:
            self.assertNotIn(placeholder, text, f"{slug}: placeholder {placeholder}")
        self.assertEqual(text.count("```" ) % 2, 0, f"{slug}: unbalanced fences")
        return text

    def test_overview_contract(self) -> None:
        slug = "llm-inference-request-lifecycle"
        text = self.assert_common_page_contract(slug)
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
        text = self.assert_common_page_contract(slug)
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
        slugs = (
            "llm-inference-request-lifecycle",
            "aibrix-inference-request-flow",
            "dynamo-inference-request-flow",
            "llm-d-inference-request-flow",
            "vllm-gpu-execution-path",
            "sglang-gpu-execution-path",
            "llm-gpu-kernel-execution-path",
        )
        wiki_paths = [
            candidate
            for category in CATEGORIES
            for candidate in (WIKI / category).glob("*.md")
        ] + [WIKI / "index.md", WIKI / "log.md"]
        for slug in slugs:
            inbound = [
                candidate
                for candidate in wiki_paths
                if candidate.stem != slug
                and f"[[{slug}" in candidate.read_text(encoding="utf-8")
            ]
            self.assertTrue(inbound, f"{slug}: no inbound wikilink")

        index = (WIKI / "index.md").read_text(encoding="utf-8")
        for slug in slugs:
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


if __name__ == "__main__":
    unittest.main()
