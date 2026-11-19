"""Run with:  python tests/test_contract.py   (or: python -m unittest discover tests)
Checks that your engine respects the contract. Add your own tests next to this file."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from harness.contract import ACTIONS, normalize     # noqa: E402
from harness.loader import load_engine              # noqa: E402
from harness.scenarios import list_scenarios, load_scenario   # noqa: E402


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.engine = load_engine(ROOT)
        self.engine.reset()

    def test_result_is_valid(self):
        for text in ("Hello", "I am furious!!!", "", "   ", "\U0001F621\U0001F621", "x" * 5000, "\u00e7\u00e3o \u00e9"):
            res = normalize(self.engine.process(text))
            self.assertEqual(res["problems"], [], "%r -> %s" % (text[:20], res["problems"]))
            self.assertIn(res["action"], ACTIONS)

    def test_reset_clears_state(self):
        a = normalize(self.engine.process("This is terrible!"))
        self.engine.reset()
        b = normalize(self.engine.process("This is terrible!"))
        self.assertEqual((a["valence"], a["activity"], a["action"]), (b["valence"], b["activity"], b["action"]))

    def test_scenarios_exist_and_are_valid(self):
        items = list_scenarios(os.path.join(ROOT, "scenarios"))
        self.assertGreaterEqual(len([n for n, _ in items if "MANDATORY" in n]), 4)
        for _, path in items:
            self.assertTrue(load_scenario(path)["messages"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
