import ast
from pathlib import Path
import unittest


RUNTIME_PATH = Path(__file__).resolve().parents[1] / "backend" / "chat" / "runtime.py"


def _read_system_prompt() -> str:
    tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "SYSTEM_PROMPT"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("SYSTEM_PROMPT is missing")


class MuseumPromptTests(unittest.TestCase):
    def test_system_prompt_uses_museum_guide_identity(self):
        prompt = _read_system_prompt()

        self.assertIn("智博导览", prompt)
        self.assertIn("湖南省博物馆", prompt)
        self.assertIn("search_knowledge_base", prompt)
        self.assertIn("[1]", prompt)

    def test_system_prompt_rejects_legacy_mascot_tone(self):
        prompt = _read_system_prompt().lower()
        forbidden = (
            "\u55b5",
            "\u4e3b\u4eba",
            "cute" + " cat",
            "cat" + " bot",
            "\U0001f431",
        )

        self.assertTrue(all(term not in prompt for term in forbidden))

    def test_system_prompt_requires_grounded_fallbacks(self):
        prompt = _read_system_prompt()

        self.assertIn("PARTIAL_EVIDENCE", prompt)
        self.assertIn("NO_KNOWLEDGE", prompt)
        self.assertIn("INSUFFICIENT_EVIDENCE", prompt)
        self.assertIn("不得使用模型常识补造", prompt)

    def test_system_prompt_requires_spoken_guide_style(self):
        prompt = _read_system_prompt()

        self.assertIn("先给结论", prompt)
        self.assertIn("现场感", prompt)
        self.assertIn("约80到180字", prompt)
        self.assertIn("不使用固定小标题", prompt)
        self.assertIn("不要把缺口扩写成大段免责声明", prompt)
        self.assertIn("最小有效解释", prompt)
        self.assertIn("不要直接拒答", prompt)


if __name__ == "__main__":
    unittest.main()
