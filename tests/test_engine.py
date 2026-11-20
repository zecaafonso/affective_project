"""Testes do Engine (tópicos 1/2) e dos cenários obrigatórios.
Run with:  python -m unittest discover tests -v"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from harness.contract import normalize                    # noqa: E402
from harness.loader import load_engine                    # noqa: E402
from harness.scenarios import load_scenario, run_scenario  # noqa: E402
from harness.session import Session                       # noqa: E402


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = load_engine(ROOT)

    def fresh(self, text):
        """Processa uma mensagem numa conversa nova (sem memória anterior)."""
        self.engine.reset()
        return normalize(self.engine.process(text))

    def test_negation_and_intensifier(self):
        good = self.fresh("This is good")["valence"]
        self.assertLess(self.fresh("This is not good")["valence"], 0)
        self.assertGreater(self.fresh("This is very good")["valence"], good)

    def test_dominance(self):
        self.assertGreater(self.fresh("I demand a refund now!")["dominance"], 0)
        self.assertLess(self.fresh("Sorry, I am confused, could you help please?")["dominance"], 0)


class MandatoryScenarioTests(unittest.TestCase):
    """Comportamento esperado nos cenários obrigatórios (cada cenário numa sessão nova)."""

    def actions(self, name):
        session = Session(load_engine(ROOT), log=False)
        sc = load_scenario(os.path.join(ROOT, "scenarios", "mandatory", name))
        return [e["action"] for e in run_scenario(session, sc, ROOT)]

    def test_m1_calm_faq(self):
        a = self.actions("M1_calm_faq.json")
        self.assertEqual(a[:-1], ["ANSWER"] * (len(a) - 1))
        self.assertEqual(a[-1], "CLOSE_POSITIVE")

    def test_m2_growing_frustration(self):
        a = self.actions("M2_growing_frustration.json")
        self.assertEqual(a[0], "ANSWER")
        self.assertIn("OFFER_HUMAN", a)
        self.assertEqual(a[-1], "ESCALATE")

    def test_m3_explicit_requests(self):
        a = self.actions("M3_explicit_requests.json")
        self.assertIn(a[1], ("OFFER_HUMAN", "ESCALATE"))   # pediu um humano
        self.assertEqual(a[2], "ESCALATE")                 # ameaça de queixa formal

    def test_m4_ambiguity_and_robustness(self):
        a = self.actions("M4_ambiguity_and_robustness.json")
        self.assertEqual(a[0], "ASK_CLARIFICATION")        # "ok"
        self.assertEqual(a[2], "ANSWER_EMPATHIC")          # sarcasmo
        self.assertEqual(a[-1], "CLOSE_POSITIVE")          # "Obrigado, ficou tudo resolvido."


if __name__ == "__main__":
    unittest.main(verbosity=2)
