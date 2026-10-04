import importlib.util
import re
import shutil
import subprocess
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


class MarkdownPreprocessingTests(unittest.TestCase):
    def test_preprocessing_preserves_fenced_content_byte_for_byte(self) -> None:
        resolver = build.Resolver()
        for fence in ("```", "````", "~~~", "~~~~~"):
            with self.subTest(fence=fence):
                fenced = f"{fence}text\r\n## Heading\r\n[[llm-inference]]\r\n{fence}\r\n"
                body = "## Heading\n\n" + fenced + "\n## Heading\n\n[[llm-inference]]\n"

                rendered = build.rewrite_wikilinks(build.inject_heading_ids(body), resolver, "concepts")

                self.assertIn(fenced, rendered)
                self.assertIn("## Heading {#heading}\n", rendered)
                self.assertIn("## Heading {#heading-2}\n", rendered)
                self.assertIn('<a class="wikilink" href="../concepts/llm-inference.html">', rendered)

    def test_wikilink_fragment_matches_heading_slug(self) -> None:
        resolver = build.Resolver()
        heading = "F2 · KV Block 生命周期"
        slug = "f2--kv-block-生命周期"
        self.assertIn(f"{{#{slug}}}", build.inject_heading_ids(f"## {heading}"))

        self.assertEqual(
            build.rewrite_wikilinks(f"[[llm-inference#{heading}|F2]]", resolver, "concepts"),
            f'<a class="wikilink" href="../concepts/llm-inference.html#{slug}">F2</a>',
        )
        self.assertEqual(
            resolver.href(f"llm-inference#{heading}|F2", from_cat=None),
            f"concepts/llm-inference.html#{slug}",
        )

    def test_toc_ignores_fenced_headings_when_numbering_duplicate_slugs(self) -> None:
        body = "## Heading\n\n~~~text\n## Heading\n~~~\n\n## Heading\n"

        self.assertEqual(
            build.extract_toc(body),
            [(2, "Heading", "heading"), (2, "Heading", "heading-2")],
        )

    def test_wikilink_without_fragment_keeps_alias_and_relative_path(self) -> None:
        resolver = build.Resolver()
        self.assertEqual(
            build.rewrite_wikilinks("[[llm-inference|Inference]]", resolver, "concepts"),
            '<a class="wikilink" href="../concepts/llm-inference.html">Inference</a>',
        )
        self.assertEqual(resolver.href("llm-inference", from_cat=None), "concepts/llm-inference.html")


class MermaidRenderingTests(unittest.TestCase):
    def test_build_page_preserves_mermaid_subroutine_syntax(self) -> None:
        body = "```mermaid\nflowchart LR\nA[[Subroutine]] --> B\n```\n\nSee [[llm-inference]]."

        rendered = build.build_page(make_page(body), build.Resolver())

        figure = re.search(r'<figure class="mermaid-figure">.*?</figure>', rendered, re.DOTALL)
        self.assertIsNotNone(figure)
        self.assertIn("A[[Subroutine]] --&gt; B", figure.group(0))
        self.assertNotIn("wikilink", figure.group(0))
        self.assertIn('<a class="wikilink" href="../concepts/llm-inference.html">', rendered)

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
        loader = re.search(r'<script[^>]+src="[^"]*mermaid@10\.9\.0[^"]*"[^>]*>', mermaid_page)
        self.assertIsNotNone(loader)
        self.assertIn('id="mermaid-loader"', loader.group(0))
        self.assertRegex(loader.group(0), r"\sdefer(?:\s|>)")
        self.assertLess(mermaid_page.index(loader.group(0)), mermaid_page.index("</head>"))
        self.assertNotIn("mermaid@10.9.0", text_page)
        self.assertNotIn("mermaid-loader", text_page)

    def test_mermaid_runtime_preserves_native_diagram_width(self) -> None:
        self.assertIn("flowchart: { useMaxWidth: false }", build.MERMAID_RUNTIME)
        self.assertIn("sequence: { useMaxWidth: false }", build.MERMAID_RUNTIME)

    def test_mermaid_theme_rerender_is_serialized(self) -> None:
        self.run_mermaid_runtime("serialized")

    def test_mermaid_waits_for_delayed_loader(self) -> None:
        self.run_mermaid_runtime("delayed")

    def test_mermaid_loader_timeout_recovers_after_late_load(self) -> None:
        self.run_mermaid_runtime("timeout")

    def test_mermaid_loader_error_recovers_after_late_load(self) -> None:
        self.run_mermaid_runtime("error")

    def run_mermaid_runtime(self, scenario: str) -> None:
        node = shutil.which("node")
        if not node:
            self.skipTest("Node.js is not available")

        harness = r'''
const vm = require("vm");
const runtime = require("fs").readFileSync(0, "utf8")
  .replace(/^<script>\n/, "")
  .replace(/\n<\/script>$/, "");

const pending = [];
const listeners = {};
const loaderListeners = {};
const timers = new Map();
let timerId = 0;
const source = { textContent: "flowchart LR\nA --> B\n" };
const target = {
  hidden: true,
  attributes: {},
  children: [],
  removeAttribute(name) { delete this.attributes[name]; },
  replaceChildren(...children) { this.children = children; },
  setAttribute(name, value) { this.attributes[name] = value; },
};
const classValues = new Set();
const errors = [];
const figure = {
  classList: {
    add(name) { classValues.add(name); },
    remove(name) { classValues.delete(name); },
    contains(name) { return classValues.has(name); },
  },
  querySelector(selector) {
    if (selector === ".mermaid-source") return source;
    if (selector === ".mermaid") return target;
    return null;
  },
  querySelectorAll(selector) {
    return selector === ".mermaid-error" ? errors : [];
  },
  appendChild(node) { errors.push(node); },
};
const mermaid = {
  initialize() {},
  run() {
    const call = { resolve: null, reject: null, promise: null };
    call.promise = new Promise((resolve, reject) => {
      call.resolve = resolve;
      call.reject = reject;
    });
    pending.push(call);
    return call.promise;
  },
};
const toggle = {
  addEventListener(event, callback) { listeners[event] = callback; },
};
const loader = {
  addEventListener(event, callback) { loaderListeners[event] = callback; },
};
const document = {
  documentElement: { getAttribute() { return "dark"; } },
  querySelectorAll(selector) { return selector === ".mermaid-figure" ? [figure] : []; },
  getElementById(id) { return id === "mermaid-loader" ? loader : toggle; },
  createTextNode(text) { return { textContent: text }; },
  createElement() {
    return { remove() { errors.splice(errors.indexOf(this), 1); } };
  },
};
const scenario = process.argv[1];
const context = {
  window: scenario === "serialized" ? { mermaid } : {},
  document, console, Promise,
  setTimeout(callback, delay) {
    const id = ++timerId;
    timers.set(id, { callback, delay });
    return id;
  },
  clearTimeout(id) { timers.delete(id); },
};
vm.runInNewContext(runtime, context);

const flush = () => new Promise((resolve) => setImmediate(resolve));
(async () => {
  if (scenario !== "serialized") {
    if (pending.length || classValues.has("is-rendered") || !target.hidden || errors.length) {
      throw new Error("pending loader must leave source visible without rendering or an error");
    }
    if (source.textContent !== "flowchart LR\nA --> B\n") throw new Error("pending loader changed source");
    listeners.click();
    if (pending.length) throw new Error("theme change rendered before the library loaded");

    if (scenario === "timeout") {
      if (timers.size !== 1) throw new Error("pending loader needs one finite timeout");
      const timer = [...timers.values()][0];
      if (!(timer.delay > 0 && timer.delay <= 10000)) throw new Error("loader timeout is not bounded");
      timer.callback();
    } else if (scenario === "error") {
      if (!loaderListeners.error) throw new Error("loader error handler is missing");
      loaderListeners.error();
    }
    if (scenario !== "delayed") {
      if (pending.length || classValues.has("is-rendered") || !target.hidden) {
        throw new Error("loader failure must keep source visible and leave render target hidden");
      }
      if (errors.length !== 1 || errors[0].className !== "mermaid-error" || !errors[0].textContent) {
        throw new Error("loader failure must show one nonblocking error message");
      }
    }
    if (!loaderListeners.load) throw new Error("delayed loader load handler is missing");
    context.window.mermaid = mermaid;
    loaderListeners.load();
    if (pending.length !== 1) throw new Error("late loader did not start rendering");
    pending.shift().resolve();
    await flush();
    if (!classValues.has("is-rendered") || target.hidden || errors.length) {
      throw new Error("late load did not clear errors and replace the source with a diagram");
    }
    if (timers.size) throw new Error("loader success left a stale timeout");
    process.stdout.write("ok\n");
    return;
  }

  if (pending.length !== 1) throw new Error("initial render did not start exactly one run");
  listeners.click();
  if (pending.length !== 1) throw new Error("theme click overlapped the in-flight render");
  pending.shift().resolve();
  await flush();
  await flush();
  if (pending.length !== 1) throw new Error("theme change did not schedule one follow-up render");
  pending.shift().reject(new Error("simulated theme render failure"));
  await flush();
  await flush();
  if (classValues.has("is-rendered")) throw new Error("failed render left is-rendered set");
  if (!target.hidden || target.attributes["aria-hidden"] !== "true") {
    throw new Error("failed render did not hide the target");
  }
  if (errors.length !== 1 || errors[0].textContent !== "图表渲染失败，以下保留 Mermaid 源码。") {
    throw new Error("failed render did not leave one fallback error");
  }
  process.stdout.write("ok\n");
})().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
'''
        result = subprocess.run(
            [node, "-e", harness, scenario],
            input=build.MERMAID_RUNTIME,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
