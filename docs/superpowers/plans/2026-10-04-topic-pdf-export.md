# Topic PDF Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate one downloadable PDF for each llm-wiki homepage topic, using the complete set of pages selected by the existing topic rules.

**Architecture:** Extend the existing Python builder with stable topic slugs and a full ordered page list, then render those pages into one print-oriented HTML book. Invoke the installed WeasyPrint CLI with an isolated writable cache to create `wiki/pdf/<slug>.pdf`; ordinary HTML generation continues to use the existing path.

**Tech Stack:** Python 3.11, python-markdown, stdlib `unittest`, WeasyPrint 68, HTML/CSS.

---

### Task 1: Make topic membership a stable, testable model

**Files:**
- Create: `tests/test_wiki_build.py`
- Modify: `wiki/html-assets/build.py:51-96`
- Modify: `wiki/html-assets/build.py:1067-1098`

- [ ] **Step 1: Write the failing topic model tests**

Create `tests/test_wiki_build.py` with a loader for the script module and tests asserting stable slugs, complete membership, and preferred-first ordering:

```python
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_PATH = ROOT / "wiki" / "html-assets" / "build.py"
SPEC = importlib.util.spec_from_file_location("wiki_build", BUILD_PATH)
assert SPEC and SPEC.loader
wiki_build = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = wiki_build
SPEC.loader.exec_module(wiki_build)


class TopicGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = wiki_build.build_topic_groups(wiki_build.collect_page_meta())

    def test_topics_have_stable_unique_slugs(self):
        slugs = [group["slug"] for group in self.groups]
        self.assertEqual(slugs, [
            "ai-agent-memory",
            "agent-runtime-sandbox",
            "llm-inference-serving",
            "kubernetes-cloud-native",
        ])
        self.assertEqual(len(slugs), len(set(slugs)))

    def test_topic_keeps_all_matches_but_only_four_card_links(self):
        group = next(g for g in self.groups if g["slug"] == "ai-agent-memory")
        self.assertEqual(group["count"], len(group["pages"]))
        self.assertGreater(group["count"], 4)
        self.assertEqual(group["links"], group["pages"][:4])

    def test_preferred_pages_are_first(self):
        group = next(g for g in self.groups if g["slug"] == "llm-inference-serving")
        self.assertEqual(
            [page.stem for page in group["pages"][:4]],
            [
                "llm-inference-serving-project-map",
                "llm-inference",
                "paged-attention",
                "radix-attention",
            ],
        )
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest tests.test_wiki_build -v
```

Expected: failures caused by missing `slug` and `pages` keys.

- [ ] **Step 3: Add slugs and expose the complete ordered page list**

Add these values to the four `TOPIC_GROUPS` entries:

```python
"slug": "ai-agent-memory"
"slug": "agent-runtime-sandbox"
"slug": "llm-inference-serving"
"slug": "kubernetes-cloud-native"
```

Return both the complete list and the four-card projection from `build_topic_groups`:

```python
groups.append(
    {
        "slug": cfg["slug"],
        "title": cfg["title"],
        "description": cfg["description"],
        "count": len(unique),
        "pages": ordered,
        "links": ordered[:4],
    }
)
```

- [ ] **Step 4: Run the topic model tests and verify GREEN**

Run the Step 2 command. Expected: 3 tests pass.

- [ ] **Step 5: Commit the topic model**

```bash
git add tests/test_wiki_build.py wiki/html-assets/build.py
git -c commit.gpgsign=false commit -m "query: Model topic PDF membership"
```

### Task 2: Render a self-contained topic book

**Files:**
- Modify: `tests/test_wiki_build.py`
- Modify: `wiki/html-assets/build.py`
- Create: `wiki/html-assets/topic-pdf.css`

- [ ] **Step 1: Write failing tests for book HTML and print CSS**

Add tests using two real wiki pages. They must check cover metadata, TOC order, internal link rewriting, external-link fallback, chapter anchors, and stylesheet loading:

```python
class TopicBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.resolver = wiki_build.Resolver()
        by_stem = {page.stem: page for page in wiki_build.collect_page_meta()}
        cls.pages = [
            by_stem["agent-memory"],
            by_stem["agent-memory-project-map"],
        ]
        cls.group = {
            "slug": "test-memory",
            "title": "Test Memory",
            "description": "A focused test book.",
            "pages": cls.pages,
            "count": len(cls.pages),
        }
        cls.html = wiki_build.build_topic_book(cls.group, cls.resolver, generated_on="2026-10-04")

    def test_book_has_cover_toc_and_ordered_chapters(self):
        self.assertIn("Test Memory", self.html)
        self.assertIn("2026-10-04", self.html)
        first = self.html.index('id="page-agent-memory"')
        second = self.html.index('id="page-agent-memory-project-map"')
        self.assertLess(first, second)
        self.assertIn('href="#page-agent-memory"', self.html)

    def test_book_rewrites_included_links_and_drops_local_html_links(self):
        rewritten = wiki_build.rewrite_topic_wikilinks(
            "[[agent-memory]] and [[mem0|Mem0]]",
            self.resolver,
            {"agent-memory"},
        )
        self.assertIn("[agent-memory](#page-agent-memory)", rewritten)
        self.assertIn("Mem0", rewritten)
        self.assertNotIn(".html", rewritten)

    def test_book_references_print_stylesheet(self):
        self.assertIn("topic-pdf.css", self.html)
        self.assertTrue((ROOT / "wiki" / "html-assets" / "topic-pdf.css").is_file())
```

- [ ] **Step 2: Run the book tests and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest tests.test_wiki_build.TopicBookTests -v
```

Expected: errors because `build_topic_book`, `rewrite_topic_wikilinks`, and `topic-pdf.css` do not exist.

- [ ] **Step 3: Implement topic-aware link rewriting and chapter rendering**

Add focused helpers to `build.py`:

```python
def page_anchor(stem: str) -> str:
    return f"page-{slugify(stem)}"


def rewrite_topic_wikilinks(body: str, resolver: Resolver, included: set[str]) -> str:
    def repl(match: re.Match) -> str:
        raw = match.group(1)
        target, alias = (raw.split("|", 1) + [""])[:2] if "|" in raw else (raw, "")
        target = target.split("#", 1)[0].strip()
        label = alias.strip() or target
        resolved = resolver.resolve(target)
        if resolved and resolved[1] in included:
            return f"[{label}](#{page_anchor(resolved[1])})"
        return label
    return WIKILINK_RE.sub(repl, body)


def render_topic_chapter(page: Page, resolver: Resolver, included: set[str]) -> str:
    body = inject_heading_ids(page.body_md)
    body = rewrite_topic_wikilinks(body, resolver, included)
    converter = md.Markdown(
        extensions=["fenced_code", "tables", "attr_list", "admonition", "sane_lists", "nl2br"],
        output_format="html5",
    )
    body_html = converter.convert(body)
    body_html = re.sub(r"<h1[^>]*>.*?</h1>\s*", "", body_html, count=1, flags=re.DOTALL)
    return (
        f'<article class="book-chapter" id="{page_anchor(page.md_path.stem)}">'
        f'<h1>{htmllib.escape(page.title)}</h1>{body_html}</article>'
    )
```

Implement `build_topic_book(group, resolver, generated_on=None)` as a complete HTML document with cover, linked ordered list TOC, ordered chapters, UTF-8 metadata, and an absolute `file://` link to `topic-pdf.css`:

```python
def build_topic_book(
    group: dict[str, object],
    resolver: Resolver,
    generated_on: str | None = None,
) -> str:
    generated_on = generated_on or date.today().isoformat()
    page_meta = list(group["pages"])
    pages = [
        load_page(WIKI / item.category / f"{item.stem}.md", item.category)
        for item in page_meta
    ]
    included = {item.stem for item in page_meta}
    toc = "".join(
        f'<li><a href="#{page_anchor(page.md_path.stem)}">'
        f'{htmllib.escape(page.title)}</a></li>'
        for page in pages
    )
    chapters = "".join(render_topic_chapter(page, resolver, included) for page in pages)
    css_uri = (WIKI / "html-assets" / "topic-pdf.css").resolve().as_uri()
    title = htmllib.escape(str(group["title"]))
    description = htmllib.escape(str(group["description"]))
    count = len(pages)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>{title} · llm-wiki</title>
  <link rel="stylesheet" href="{css_uri}" />
</head>
<body>
  <section class="book-cover">
    <p>llm-wiki topic book</p>
    <h1>{title}</h1>
    <p>{description}</p>
    <p>{count} pages · {generated_on}</p>
  </section>
  <nav class="book-toc"><h1>目录</h1><ol>{toc}</ol></nav>
  {chapters}
</body>
</html>
"""
```

Add `from datetime import date` with the existing imports.

- [ ] **Step 4: Add the print stylesheet**

Create `wiki/html-assets/topic-pdf.css` with A4 rules, page numbering, CJK font fallbacks, chapter page breaks, wrapped code, bounded images, and non-overflowing tables:

```css
@page { size: A4; margin: 18mm 16mm 20mm; @bottom-center { content: counter(page); } }
@page:first { @bottom-center { content: none; } }
html { font-family: "PingFang SC", "Noto Sans CJK SC", sans-serif; color: #172033; }
body { margin: 0; font-size: 10.5pt; line-height: 1.65; }
.book-cover { page: cover; min-height: 230mm; display: flex; flex-direction: column; justify-content: center; }
.book-cover h1 { font-size: 32pt; line-height: 1.2; }
.book-toc { break-before: page; }
.book-toc a { color: inherit; text-decoration: none; }
.book-chapter { break-before: page; }
.book-chapter > h1 { bookmark-level: 1; font-size: 24pt; }
h2, h3 { break-after: avoid; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; padding: 10pt; background: #f4f6f8; }
code { font-family: "SFMono-Regular", Menlo, monospace; font-size: 0.9em; }
img, svg { max-width: 100%; height: auto; }
table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }
th, td { border: 0.5pt solid #aeb7c2; padding: 4pt; overflow-wrap: anywhere; }
blockquote { margin-left: 0; padding-left: 10pt; border-left: 3pt solid #6b8afd; }
```

- [ ] **Step 5: Run all unit tests and verify GREEN**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest discover -s tests -v
```

Expected: all topic model and topic book tests pass.

- [ ] **Step 6: Commit topic book rendering**

```bash
git add tests/test_wiki_build.py wiki/html-assets/build.py wiki/html-assets/topic-pdf.css
git -c commit.gpgsign=false commit -m "query: Render topic PDF books"
```

### Task 3: Add PDF CLI commands and robust WeasyPrint execution

**Files:**
- Modify: `tests/test_wiki_build.py`
- Modify: `wiki/html-assets/build.py`

- [ ] **Step 1: Write failing export and CLI tests**

Add tests that use a temporary output directory and an executable fake WeasyPrint script. The fake copies `%PDF-1.7\nfixture\n` into the requested output, allowing the real subprocess boundary to be tested without mocking:

```python
class TopicExportTests(unittest.TestCase):
    def test_export_topic_invokes_renderer_and_writes_pdf(self):
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)
            renderer = temp_path / "weasyprint"
            renderer.write_text(
                "#!/bin/sh\nprintf '%s\\n' '%PDF-1.7' 'fixture' > \"$2\"\n",
                encoding="utf-8",
            )
            renderer.chmod(0o755)
            group = {
                "slug": "test-memory",
                "title": "Test Memory",
                "description": "fixture",
                "pages": [next(
                    page for page in wiki_build.collect_page_meta()
                    if page.stem == "agent-memory"
                )],
                "count": 1,
            }
            output = wiki_build.export_topic_pdf(
                group,
                wiki_build.Resolver(),
                output_dir=temp_path / "pdf",
                renderer=str(renderer),
            )
            self.assertEqual(output.name, "test-memory.pdf")
            self.assertTrue(output.read_bytes().startswith(b"%PDF-"))

    def test_find_topic_rejects_unknown_slug(self):
        with self.assertRaisesRegex(ValueError, "Available topics"):
            wiki_build.find_topic([], "missing")
```

- [ ] **Step 2: Run export tests and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest tests.test_wiki_build.TopicExportTests -v
```

Expected: errors because `export_topic_pdf` and `find_topic` do not exist.

- [ ] **Step 3: Implement renderer discovery, isolated execution, and topic lookup**

Add `PDF_OUT = WIKI / "pdf"` and the following functions. Add `subprocess` and `tempfile` with the existing imports:

```python
def find_topic(groups: list[dict[str, object]], slug: str) -> dict[str, object]:
    for group in groups:
        if group["slug"] == slug:
            return group
    available = ", ".join(str(group["slug"]) for group in groups)
    raise ValueError(f"Unknown topic '{slug}'. Available topics: {available}")


def export_topic_pdf(
    group: dict[str, object],
    resolver: Resolver,
    *,
    output_dir: Path = PDF_OUT,
    renderer: str | None = None,
) -> Path:
    renderer = renderer or shutil.which("weasyprint")
    if renderer is None:
        raise RuntimeError("WeasyPrint is required for PDF export")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f'{group["slug"]}.pdf'
    with tempfile.TemporaryDirectory(prefix="llm-wiki-pdf-") as temp:
        temp_dir = Path(temp)
        html_path = temp_dir / "book.html"
        cache_dir = temp_dir / "cache"
        cache_dir.mkdir()
        html_path.write_text(build_topic_book(group, resolver), encoding="utf-8")
        env = os.environ.copy()
        env["XDG_CACHE_HOME"] = str(cache_dir)
        subprocess.run([renderer, str(html_path), str(output)], check=True, env=env)
    if not output.is_file() or not output.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError(f"Renderer did not create a valid PDF: {output}")
    return output
```

- [ ] **Step 4: Add mutually exclusive CLI arguments and dispatch**

In `main`, create an argparse mutually exclusive group:

```python
pdf_args = ap.add_mutually_exclusive_group()
pdf_args.add_argument("--pdf-topic", metavar="SLUG")
pdf_args.add_argument("--pdf-topics", action="store_true")
```

After collecting `pages` and `topic_groups`, export either the selected group or all groups. Convert unknown-topic and renderer errors into `ap.error(...)` messages. Keep the normal HTML build path active so the homepage and PDF links are refreshed in the same invocation:

```python
    try:
        selected_topics = (
            topic_groups
            if args.pdf_topics
            else [find_topic(topic_groups, args.pdf_topic)] if args.pdf_topic
            else []
        )
        for topic in selected_topics:
            output = export_topic_pdf(topic, resolver)
            print(f"  PDF {output.relative_to(ROOT)}")
    except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        ap.error(str(exc))
```

- [ ] **Step 5: Run all tests and CLI error checks**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest discover -s tests -v
./wiki/html-assets/build.py --pdf-topic does-not-exist
```

Expected: unit tests pass; the second command exits 2 and lists all four valid slugs.

- [ ] **Step 6: Commit PDF command support**

```bash
git add tests/test_wiki_build.py wiki/html-assets/build.py
git -c commit.gpgsign=false commit -m "query: Add topic PDF export commands"
```

### Task 4: Expose downloads, document usage, and verify real artifacts

**Files:**
- Modify: `tests/test_wiki_build.py`
- Modify: `wiki/html-assets/build.py:1179-1196`
- Modify: `README.md`
- Modify: `wiki/html/index.html`
- Create: `wiki/pdf/ai-agent-memory.pdf`
- Create: `wiki/pdf/agent-runtime-sandbox.pdf`
- Create: `wiki/pdf/llm-inference-serving.pdf`
- Create: `wiki/pdf/kubernetes-cloud-native.pdf`

- [ ] **Step 1: Write the failing homepage-link test**

Add:

```python
class TopicDownloadLinkTests(unittest.TestCase):
    def test_topic_cards_link_to_their_pdf(self):
        groups = wiki_build.build_topic_groups(wiki_build.collect_page_meta())
        rendered = wiki_build.render_topic_grid(groups)
        for group in groups:
            self.assertIn(f'href="pdf/{group["slug"]}.pdf"', rendered)
            self.assertIn("下载 PDF", rendered)
```

- [ ] **Step 2: Run the homepage test and verify RED**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest tests.test_wiki_build.TopicDownloadLinkTests -v
```

Expected: failure because topic cards contain no PDF links.

- [ ] **Step 3: Add the download link and README instructions**

Extend each card in `render_topic_grid` with:

```python
f'<a class="topic-pdf-link" href="pdf/{esc(group["slug"])}.pdf">下载 PDF</a>'
```

Document both commands, output paths, WeasyPrint requirement, and the fact that `--pdf-topics` refreshes all four downloadable files in `README.md` using this section:

````markdown
## 主题 PDF 导出

主题 PDF 需要本机安装 WeasyPrint。生成单个主题或全部主题：

```bash
./wiki/html-assets/build.py --pdf-topic ai-agent-memory
./wiki/html-assets/build.py --pdf-topics
```

文件输出到 `wiki/pdf/`。`--pdf-topics` 会刷新首页四个主题入口对应的全部 PDF。
````

- [ ] **Step 4: Run tests and build all real PDFs**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest discover -s tests -v
XDG_CACHE_HOME=/private/tmp/llm-wiki-xdg-cache ./wiki/html-assets/build.py --pdf-topics
```

Expected: all tests pass; four PDFs are written under `wiki/pdf/` and normal HTML output is rebuilt.

- [ ] **Step 5: Verify PDF signatures, sizes, links, and HTML regression**

Run:

```bash
for pdf in wiki/pdf/*.pdf; do test "$(head -c 5 "$pdf")" = '%PDF-' || exit 1; test -s "$pdf" || exit 1; done
find wiki/pdf -name '*.pdf' -maxdepth 1 -print
rg -n 'pdf/(ai-agent-memory|agent-runtime-sandbox|llm-inference-serving|kubernetes-cloud-native)\.pdf' wiki/html/index.html
./wiki/html-assets/build.py --dry-run
git diff --check
```

Expected: four non-empty valid PDF files, four homepage links, dry-run completes, and no whitespace errors.

- [ ] **Step 6: Update the durable wiki log**

Append this entry to `wiki/log.md`, then rebuild HTML so `wiki/html/log.html` matches:

```markdown
## [2026-10-04] query | Add topic-scoped PDF exports

- Added one-command PDF export for each homepage topic and download links from topic cards.
```

- [ ] **Step 7: Commit the completed operation**

```bash
git add README.md tests/test_wiki_build.py wiki/html-assets/build.py wiki/html-assets/topic-pdf.css wiki/html/index.html wiki/html/log.html wiki/log.md wiki/pdf/*.pdf
git -c commit.gpgsign=false commit -m "query: Export wiki topics as PDF"
```

- [ ] **Step 8: Run final verification from the committed tree**

Run:

```bash
UV_CACHE_DIR=/private/tmp/llm-wiki-uv-cache uv run --quiet --with markdown python -m unittest discover -s tests -v
for pdf in wiki/pdf/*.pdf; do test "$(head -c 5 "$pdf")" = '%PDF-' || exit 1; test -s "$pdf" || exit 1; done
./wiki/html-assets/build.py --dry-run
git status --short
```

Expected: all tests pass, all committed artifacts remain valid, the dry-run succeeds, and status contains only the user's pre-existing untracked M5-D design file.
