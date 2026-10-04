import importlib.util
import re
import sys
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
