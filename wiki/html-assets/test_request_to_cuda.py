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


if __name__ == "__main__":
    unittest.main()
