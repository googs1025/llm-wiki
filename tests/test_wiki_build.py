import importlib.util
import io
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pypdf import PdfWriter


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


class TopicDownloadLinkTests(unittest.TestCase):
    def test_every_topic_card_links_to_existing_pdf_with_topic_context(self):
        self.assertEqual(BUILD.PDF_OUT, BUILD.OUT / "pdf")
        groups = BUILD.build_topic_groups(BUILD.collect_page_meta())
        topic_grid = BUILD.render_topic_grid(groups)
        pdf_links = re.findall(
            r'<a class="topic-pdf-link" href="([^"]+)"(?: aria-label="([^"]*)")?>([^<]*)</a>',
            topic_grid,
        )

        self.assertEqual(len(pdf_links), len(groups))
        for group, (href, aria_label, visible_text) in zip(groups, pdf_links):
            with self.subTest(slug=group["slug"]):
                self.assertEqual(href, f'pdf/{group["slug"]}.pdf')
                resolved_target = (BUILD.OUT / href).resolve()
                expected_target = (BUILD.PDF_OUT / f'{group["slug"]}.pdf').resolve()
                self.assertEqual(resolved_target, expected_target)
                self.assertTrue(resolved_target.is_file())
                accessible_label = aria_label or visible_text
                self.assertIn(group["title"], accessible_label)


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

    def test_topic_images_resolve_locally_without_touching_urls_or_code(self):
        source = (
            '![diagram](../../raw/assets/demo.png "Architecture")\n'
            "![external](https://example.com/demo.png)\n"
            "![embedded](data:image/png;base64,AAAA)\n"
            "![anchor](#diagram)\n"
            "Inline `![literal](../../raw/assets/inline.png)` stays literal.\n\n"
            "```markdown\n"
            "![literal](../../raw/assets/fenced.png)\n"
            "```\n"
        )
        page_path = BUILD.WIKI / "concepts" / "synthetic.md"

        rewritten = BUILD.rewrite_topic_image_destinations(source, page_path.parent)

        expected = (BUILD.WIKI / "concepts" / "../../raw/assets/demo.png").resolve().as_uri()
        self.assertIn(f'![diagram]({expected} "Architecture")', rewritten)
        self.assertIn("![external](https://example.com/demo.png)", rewritten)
        self.assertIn("![embedded](data:image/png;base64,AAAA)", rewritten)
        self.assertIn("![anchor](#diagram)", rewritten)
        self.assertIn("`![literal](../../raw/assets/inline.png)`", rewritten)
        self.assertIn("![literal](../../raw/assets/fenced.png)", rewritten)

    def test_topic_images_support_balanced_escaped_and_angled_destinations(self):
        source = (
            "![balanced](../../raw/assets/a(b).png)\n"
            "![escaped](../../raw/assets/a\\(b\\).png)\n"
            '![angled](<../../raw/assets/a (b).png> "Diagram title")\n'
        )
        page_path = BUILD.WIKI / "concepts" / "synthetic.md"

        rewritten = BUILD.rewrite_topic_image_destinations(source, page_path.parent)

        balanced = (page_path.parent / "../../raw/assets/a(b).png").resolve().as_uri()
        angled = (page_path.parent / "../../raw/assets/a (b).png").resolve().as_uri()
        self.assertIn(f"![balanced]({balanced})", rewritten)
        self.assertIn(f"![escaped]({balanced})", rewritten)
        self.assertIn(f'![angled](<{angled}> "Diagram title")', rewritten)

    def test_render_chapter_uses_absolute_file_uri_for_local_images(self):
        page_path = BUILD.WIKI / "concepts" / "synthetic.md"
        page = BUILD.Page(
            md_path=page_path,
            category="concepts",
            fm=BUILD.Frontmatter(title="Synthetic"),
            body_md="![diagram](../../raw/assets/demo.png)",
            title="Synthetic",
        )

        chapter = BUILD.render_topic_chapter(page, self.resolver, {"synthetic"})

        expected = (page_path.parent / "../../raw/assets/demo.png").resolve().as_uri()
        self.assertIn(f'<img alt="diagram" src="{expected}"', chapter)

    def test_render_chapter_keeps_full_parenthesized_image_destination(self):
        page_path = BUILD.WIKI / "concepts" / "synthetic.md"
        page = BUILD.Page(
            md_path=page_path,
            category="concepts",
            fm=BUILD.Frontmatter(title="Synthetic"),
            body_md="![diagram](../../raw/assets/a(b).png)",
            title="Synthetic",
        )

        chapter = BUILD.render_topic_chapter(page, self.resolver, {"synthetic"})

        expected = (page_path.parent / "../../raw/assets/a(b).png").resolve().as_uri()
        self.assertIn(f'<img alt="diagram" src="{expected}">', chapter)
        self.assertNotIn(".png)</p>", chapter)

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

    def test_print_stylesheet_uses_only_bundled_open_fonts(self):
        fonts = BUILD.WIKI / "html-assets" / "fonts"
        expected_files = [
            "NotoSansCJKsc-Regular.otf",
            "NotoSansMonoCJKsc-Regular.otf",
            "NotoSansSymbols2-Regular.ttf",
            "NotoEmoji-Regular.ttf",
            "NotoEmoji-Variable.ttf",
            "OFL.txt",
            "NotoEmoji-OFL.txt",
            "NotoSansSymbols2-OFL.txt",
            "README.md",
        ]
        for filename in expected_files:
            with self.subTest(filename=filename):
                asset = fonts / filename
                self.assertTrue(asset.is_file())
                self.assertGreater(asset.stat().st_size, 0)

        css = (BUILD.WIKI / "html-assets" / "topic-pdf.css").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(css.count("@font-face"), 3)
        for filename in expected_files[:4]:
            self.assertIn(f'url("fonts/{filename}")', css)
        for proprietary_font in (
            "PingFang",
            "Songti",
            "Andale",
            "Apple",
            "Hiragino",
            "SFMono",
        ):
            self.assertNotIn(proprietary_font, css)

    def test_book_forces_text_presentation_for_emoji_symbols(self):
        pages_by_stem = {page.stem: page for page in BUILD.collect_page_meta()}
        group = {
            "slug": "emoji-presentation-test",
            "title": "Emoji Presentation Test",
            "description": "Use bundled monochrome glyphs.",
            "pages": [pages_by_stem["src-agent-sandbox-architecture"]],
            "count": 1,
        }

        book = BUILD.build_topic_book(
            group,
            self.resolver,
            generated_on="2026-10-04",
        )

        for symbol in ("✅", "⚠", "❌"):
            with self.subTest(symbol=symbol):
                self.assertIn(f"{symbol}\ufe0e", book)
                self.assertNotRegex(book, rf"{symbol}(?!\ufe0e)")


class TopicExportTests(unittest.TestCase):
    def setUp(self):
        valid_pdf = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.write(valid_pdf)
        self.valid_pdf = valid_pdf.getvalue()
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

    def test_export_topic_pdf_rejects_marker_shaped_malformed_output(self):
        malformed_pdf = b"%PDF-1.7\nnot a PDF object graph\nstartxref\n0\n%%EOF\n"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' '%PDF-1.7' 'not a PDF object graph' "
                "'startxref' '0' '%%EOF' > \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output = temp / "pdf" / "test-memory.pdf"
            output.parent.mkdir()
            output.write_bytes(self.valid_pdf)

            with self.assertRaisesRegex(RuntimeError, "valid PDF"):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=output.parent,
                    renderer=os.fspath(renderer),
                )

            self.assertEqual(output.read_bytes(), self.valid_pdf)
            self.assertNotEqual(output.read_bytes(), malformed_pdf)
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_export_topic_pdf_runs_renderer_and_writes_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fixture = temp / "valid.pdf"
            fixture.write_bytes(self.valid_pdf)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\n"
                "test -f \"$1\" || exit 3\n"
                "test \"$XDG_CACHE_HOME\" = \"${1%/*}/cache\" || exit 4\n"
                "test \"${2%/*}\" = \"${0%/*}/pdf\" || exit 5\n"
                f"cp {shlex.quote(os.fspath(fixture))} \"$2\"\n",
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
            self.assertEqual(output.read_bytes(), self.valid_pdf)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)

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

    def test_cli_unknown_topic_is_rejected_before_html_writes(self):
        with tempfile.TemporaryDirectory(dir=BUILD.ROOT) as temp_dir:
            output_dir = Path(temp_dir) / "html"
            output_dir.mkdir()
            sentinel = output_dir / "index.html"
            original = f"{BUILD.AUTO_MARKER}\nsentinel\n"
            sentinel.write_text(original, encoding="utf-8")

            with (
                mock.patch.object(BUILD, "OUT", output_dir),
                mock.patch.object(
                    sys,
                    "argv",
                    [os.fspath(BUILD_PATH), "--pdf-topic", "does-not-exist"],
                ),
                mock.patch.object(sys, "stdout", io.StringIO()),
                mock.patch.object(sys, "stderr", io.StringIO()),
                self.assertRaisesRegex(SystemExit, "2"),
            ):
                BUILD.main()

            self.assertEqual(sentinel.read_text(encoding="utf-8"), original)

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
        self.assertIn("would write: wiki/html/pdf/ai-agent-memory.pdf", result.stdout)
        self.assertEqual(output.exists(), existed_before)

    def test_direct_cli_uses_inline_dependencies(self):
        env = os.environ.copy()
        env["UV_CACHE_DIR"] = "/private/tmp/llm-wiki-test-uv-cache"

        result = subprocess.run(
            [
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

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("would write: wiki/html/pdf/ai-agent-memory.pdf", result.stdout)

    def test_export_topic_pdf_requires_weasyprint(self):
        with mock.patch.object(BUILD.shutil, "which", return_value=None):
            with self.assertRaisesRegex(
                RuntimeError,
                "^WeasyPrint is required for PDF export$",
            ):
                BUILD.export_topic_pdf(self.group, BUILD.Resolver())

    def test_export_topic_pdf_rejects_truncated_output_and_preserves_destination(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\nprintf '%s\\n' '%PDF-1.7' 'truncated' > \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output = temp / "pdf" / "test-memory.pdf"
            output.parent.mkdir()
            original = self.valid_pdf
            output.write_bytes(original)

            with self.assertRaises(RuntimeError):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=temp / "pdf",
                    renderer=os.fspath(renderer),
                )
            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_export_topic_pdf_rejects_missing_new_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output = temp / "pdf" / "test-memory.pdf"
            output.parent.mkdir()
            output.write_bytes(self.valid_pdf)

            with self.assertRaises(RuntimeError):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=temp / "pdf",
                    renderer=os.fspath(renderer),
                )
            self.assertEqual(list(output.parent.iterdir()), [output])

    def test_export_topic_pdf_wraps_renderer_spawn_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(RuntimeError, "Unable to run PDF renderer"):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=Path(temp_dir) / "pdf",
                    renderer=os.fspath(Path(temp_dir) / "missing-renderer"),
                )

    def test_export_topic_pdf_times_out_and_cleans_staging_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            renderer = temp / "fake-weasyprint"
            renderer.write_text("#!/bin/sh\nwhile :; do :; done\n", encoding="utf-8")
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output_dir = temp / "pdf"
            output_dir.mkdir()
            output = output_dir / "test-memory.pdf"
            output.write_bytes(self.valid_pdf)

            with self.assertRaisesRegex(RuntimeError, "timed out"):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=output_dir,
                    renderer=os.fspath(renderer),
                    timeout=0.05,
                )

            self.assertEqual(output.read_bytes(), self.valid_pdf)
            self.assertEqual(list(output_dir.iterdir()), [output])

    def test_export_topic_pdf_publish_error_preserves_destination_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fixture = temp / "valid.pdf"
            fixture.write_bytes(self.valid_pdf)
            renderer = temp / "fake-weasyprint"
            renderer.write_text(
                "#!/bin/sh\n"
                f"cp {shlex.quote(os.fspath(fixture))} \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(renderer.stat().st_mode | 0o111)
            output_dir = temp / "pdf"
            output_dir.mkdir()
            output = output_dir / "test-memory.pdf"
            original = self.valid_pdf
            output.write_bytes(original)

            with (
                mock.patch.object(BUILD.os, "replace", side_effect=OSError("read-only")),
                self.assertRaisesRegex(RuntimeError, "Unable to publish PDF"),
            ):
                BUILD.export_topic_pdf(
                    self.group,
                    BUILD.Resolver(),
                    output_dir=output_dir,
                    renderer=os.fspath(renderer),
                )

            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(list(output_dir.iterdir()), [output])


if __name__ == "__main__":
    unittest.main()
