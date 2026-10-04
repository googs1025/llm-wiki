import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


BUILD_PATH = Path(__file__).resolve().parents[1] / "wiki" / "html-assets" / "build.py"
SPEC = importlib.util.spec_from_file_location("wiki_html_build", BUILD_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load wiki builder from {BUILD_PATH}")
BUILD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BUILD
SPEC.loader.exec_module(BUILD)


class TopicGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = BUILD.build_topic_groups(BUILD.collect_page_meta())

    def test_topic_slugs_are_stable_and_unique(self):
        slugs = [group["slug"] for group in self.groups]

        self.assertEqual(
            slugs,
            [
                "ai-agent-memory",
                "agent-runtime-sandbox",
                "llm-inference-serving",
                "kubernetes-cloud-native",
            ],
        )
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_ai_agent_memory_keeps_full_membership_and_four_card_links(self):
        group = self.groups[0]

        self.assertEqual(group["count"], len(group["pages"]))
        self.assertGreater(group["count"], 4)
        self.assertEqual(group["links"], group["pages"][:4])

    def test_llm_inference_serving_starts_with_preferred_pages(self):
        group = self.groups[2]

        self.assertEqual(
            [page.stem for page in group["pages"][:4]],
            [
                "llm-inference-serving-project-map",
                "llm-inference",
                "paged-attention",
                "radix-attention",
            ],
        )


class TopicBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pages_by_stem = {page.stem: page for page in BUILD.collect_page_meta()}
        cls.pages = [
            pages_by_stem["agent-memory"],
            pages_by_stem["agent-memory-project-map"],
        ]
        cls.group = {
            "slug": "test-memory",
            "title": "Test Memory",
            "description": "A focused test book.",
            "pages": cls.pages,
            "count": 2,
        }
        cls.resolver = BUILD.Resolver()

    def test_book_cover_includes_title_and_generation_date(self):
        book = BUILD.build_topic_book(
            self.group,
            self.resolver,
            generated_on="2026-10-04",
        )

        self.assertIn("Test Memory", book)
        self.assertIn("2026-10-04", book)

    def test_book_keeps_chapter_order_and_links_table_of_contents(self):
        book = BUILD.build_topic_book(
            self.group,
            self.resolver,
            generated_on="2026-10-04",
        )

        first = book.index('id="page-agent-memory"')
        second = book.index('id="page-agent-memory-project-map"')
        self.assertLess(first, second)
        self.assertIn('href="#page-agent-memory"', book)

    def test_topic_wikilinks_only_link_pages_in_the_book(self):
        rewritten = BUILD.rewrite_topic_wikilinks(
            "[[agent-memory]] and [[mem0|Mem0]]",
            self.resolver,
            {"agent-memory"},
        )

        self.assertIn("[agent-memory](#page-agent-memory)", rewritten)
        self.assertIn("Mem0", rewritten)
        self.assertNotIn("[[mem0|Mem0]]", rewritten)
        self.assertNotIn(".html", rewritten)

    def test_topic_wikilink_fragment_targets_namespaced_heading(self):
        rewritten = BUILD.rewrite_topic_wikilinks(
            "[[agent-memory#核心挑战|Jump]]",
            self.resolver,
            {"agent-memory"},
        )

        self.assertEqual("[Jump](#page-agent-memory--核心挑战)", rewritten)

    def test_topic_wikilinks_preserve_fenced_and_inline_code(self):
        source = (
            "Outside [[agent-memory]].\n\n"
            "```text\n"
            "┌────────────────────┐\n"
            "│ [[agent-memory]]   │\n"
            "└────────────────────┘\n"
            "```\n\n"
            "Inline `[[agent-memory]]` stays literal.\n"
        )

        rewritten = BUILD.rewrite_topic_wikilinks(
            source,
            self.resolver,
            {"agent-memory"},
        )

        self.assertIn("Outside [agent-memory](#page-agent-memory).", rewritten)
        self.assertIn(
            "```text\n"
            "┌────────────────────┐\n"
            "│ [[agent-memory]]   │\n"
            "└────────────────────┘\n"
            "```",
            rewritten,
        )
        self.assertIn("`[[agent-memory]]`", rewritten)

    def test_render_chapter_preserves_fence_immediately_after_heading(self):
        page = BUILD.Page(
            md_path=Path("synthetic.md"),
            category="concepts",
            fm=BUILD.Frontmatter(title="Synthetic"),
            body_md=(
                "# Synthetic\n\n"
                "## Diagram\n"
                "```text\n"
                "┌────────────────────┐\n"
                "│ [[agent-memory]]   │\n"
                "└────────────────────┘\n"
                "```\n"
            ),
            title="Synthetic",
        )

        chapter = BUILD.render_topic_chapter(
            page,
            self.resolver,
            {"agent-memory", "synthetic"},
        )
        code_block = re.search(r"<pre><code[^>]*>(.*?)</code></pre>", chapter, re.DOTALL)

        self.assertIn('id="page-synthetic--diagram"', chapter)
        self.assertIsNotNone(code_block)
        assert code_block is not None
        self.assertIn("[[agent-memory]]", code_block.group(1))
        self.assertNotIn("<a ", code_block.group(1))
        self.assertNotIn("```", chapter)

    def test_chapter_heading_ids_are_unique_across_book(self):
        pages_by_stem = {page.stem: page for page in BUILD.collect_page_meta()}
        group = {
            "slug": "shared-heading-test",
            "title": "Shared Heading Test",
            "description": "Pages with overlapping heading names.",
            "pages": [
                pages_by_stem["agent-memory-project-map"],
                pages_by_stem["agent-runtime-sandbox-project-map"],
            ],
            "count": 2,
        }

        book = BUILD.build_topic_book(
            group,
            self.resolver,
            generated_on="2026-10-04",
        )
        ids = re.findall(r'\sid="([^"]+)"', book)

        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('id="page-agent-memory-project-map--一句话分层"', book)

    def test_book_uses_existing_print_stylesheet(self):
        book = BUILD.build_topic_book(
            self.group,
            self.resolver,
            generated_on="2026-10-04",
        )

        self.assertIn("topic-pdf.css", book)
        stylesheet = BUILD.WIKI / "html-assets" / "topic-pdf.css"
        self.assertTrue(stylesheet.is_file())
        css = stylesheet.read_text(encoding="utf-8")
        self.assertNotIn("word-break: break-word", css)
        self.assertRegex(css, r"img\s*,\s*svg\s*\{")


class TopicExportTests(unittest.TestCase):
    def setUp(self):
        self.page = BUILD.PageMeta(
            title="Agent Memory",
            href="concepts/agent-memory.html",
            category="concepts",
            category_label="概念",
            stem="agent-memory",
            tags=["agent-memory"],
            date="2026-10-04",
        )
        self.group = {
            "slug": "test-memory",
            "title": "Test Memory",
            "description": "A focused test book.",
            "pages": [self.page],
            "count": 1,
        }

    def test_export_topic_pdf_runs_renderer_and_writes_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\n"
                "test -f \"$1\" || exit 3\n"
                "test \"$XDG_CACHE_HOME\" = \"${1%/*}/cache\" || exit 4\n"
                "printf '%%PDF-1.7\\nfixture\\n' > \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(renderer.stat().st_mode | 0o111)

            output = BUILD.export_topic_pdf(
                self.group,
                BUILD.Resolver(),
                output_dir=temp / "pdf",
                renderer=str(renderer),
            )

            self.assertEqual(output.name, "test-memory.pdf")
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))

    def test_find_topic_selects_exact_slug(self):
        self.assertIs(BUILD.find_topic([self.group], "test-memory"), self.group)

    def test_find_topic_lists_available_topics_for_unknown_slug(self):
        with self.assertRaisesRegex(ValueError, "Available topics"):
            BUILD.find_topic([], "missing")

    def test_cli_unknown_topic_exits_two_and_lists_all_topics(self):
        result = subprocess.run(
            [
                sys.executable,
                os.fspath(BUILD_PATH),
                "--dry-run",
                "--pdf-topic",
                "does-not-exist",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 2)
        for slug in (
            "ai-agent-memory",
            "agent-runtime-sandbox",
            "llm-inference-serving",
            "kubernetes-cloud-native",
        ):
            self.assertIn(slug, result.stderr)

    def test_cli_dry_run_does_not_require_renderer_or_write_pdf(self):
        output = BUILD.PDF_OUT / "ai-agent-memory.pdf"
        existed_before = output.exists()
        env = os.environ.copy()
        env["PATH"] = ""

        result = subprocess.run(
            [
                sys.executable,
                os.fspath(BUILD_PATH),
                "--dry-run",
                "--pdf-topic",
                "ai-agent-memory",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("would write: wiki/pdf/ai-agent-memory.pdf", result.stdout)
        self.assertEqual(output.exists(), existed_before)

    def test_export_topic_pdf_requires_weasyprint(self):
        with mock.patch.object(BUILD.shutil, "which", return_value=None):
            with self.assertRaisesRegex(
                RuntimeError,
                "^WeasyPrint is required for PDF export$",
            ):
                BUILD.export_topic_pdf(self.group, BUILD.Resolver())

    def test_export_topic_pdf_rejects_invalid_renderer_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\nprintf 'not a pdf\\n' > \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output = temp / "pdf" / "test-memory.pdf"
            output.parent.mkdir()
            original = b"%PDF-1.7\nexisting\n"
            output.write_bytes(original)

            with self.assertRaises(RuntimeError):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=temp / "pdf",
                    renderer=os.fspath(renderer),
                )
            self.assertEqual(output.read_bytes(), original)

    def test_export_topic_pdf_rejects_missing_new_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output = temp / "pdf" / "test-memory.pdf"
            output.parent.mkdir()
            output.write_bytes(b"%PDF-1.7\nstale\n")

            with self.assertRaises(RuntimeError):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=temp / "pdf",
                    renderer=os.fspath(renderer),
                )

    def test_export_topic_pdf_wraps_renderer_spawn_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "Unable to run PDF renderer"):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=Path(temp_dir) / "pdf",
                    renderer=os.fspath(Path(temp_dir) / "missing-renderer"),
                )


if __name__ == "__main__":
    unittest.main()
