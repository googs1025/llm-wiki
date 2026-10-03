import importlib.util
import sys
import unittest
from pathlib import Path


BUILD_PATH = Path(__file__).with_name("build.py")
SPEC = importlib.util.spec_from_file_location("wiki_html_build", BUILD_PATH)
build = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = build
SPEC.loader.exec_module(build)


def make_page(body: str) -> "build.Page":
    return build.Page(
        Path("wiki/concepts/test.md"),
        "concepts",
        build.Frontmatter(title="Test"),
        body,
        "Test",
    )


class MermaidRenderingTests(unittest.TestCase):
    def test_render_mermaid_blocks_converts_diagram_fence(self) -> None:
        body = '<pre><code class="language-mermaid">flowchart LR\nA --&gt; B\n</code></pre>'

        rendered, found = build.render_mermaid_blocks(body)

        self.assertTrue(found)
        self.assertIn('class="mermaid-figure"', rendered)
        self.assertIn('class="mermaid-source"', rendered)
        self.assertIn('class="mermaid"', rendered)
        self.assertIn("A --&gt; B", rendered)

    def test_render_mermaid_blocks_leaves_plain_language_text_unchanged(self) -> None:
        body = '<pre><code class="language-text">flowchart LR\nA --&gt; B\n</code></pre>'

        rendered, found = build.render_mermaid_blocks(body)

        self.assertFalse(found)
        self.assertEqual(rendered, body)

    def test_build_page_loads_mermaid_only_for_mermaid_pages(self) -> None:
        mermaid_page = build.build_page(make_page("```mermaid\nflowchart LR\nA --> B\n```"), build.Resolver())
        text_page = build.build_page(make_page("```text\nplain text\n```"), build.Resolver())

        self.assertIn("mermaid@10.9.0", mermaid_page)
        self.assertNotIn("mermaid@10.9.0", text_page)


if __name__ == "__main__":
    unittest.main()
