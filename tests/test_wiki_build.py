import importlib.util
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


if __name__ == "__main__":
    unittest.main()
