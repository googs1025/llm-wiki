import importlib.util
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

    def test_mermaid_runtime_preserves_native_diagram_width(self) -> None:
        self.assertIn("flowchart: { useMaxWidth: false }", build.MERMAID_RUNTIME)
        self.assertIn("sequence: { useMaxWidth: false }", build.MERMAID_RUNTIME)

    def test_mermaid_theme_rerender_is_serialized(self) -> None:
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
const document = {
  documentElement: { getAttribute() { return "dark"; } },
  querySelectorAll(selector) { return selector === ".mermaid-figure" ? [figure] : []; },
  getElementById() { return toggle; },
  createTextNode(text) { return { textContent: text }; },
  createElement() { return {}; },
};
const context = { window: { mermaid }, document, console, Promise };
vm.runInNewContext(runtime, context);

if (pending.length !== 1) throw new Error("initial render did not start exactly one run");
listeners.click();
if (pending.length !== 1) throw new Error("theme click overlapped the in-flight render");

pending.shift().resolve();
const flush = () => new Promise((resolve) => setImmediate(resolve));
(async () => {
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
            [node, "-e", harness],
            input=build.MERMAID_RUNTIME,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
