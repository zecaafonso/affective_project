"""Tópico 3: testes da política de decisão (engine/policy.py), um por regra.
Run with:  python -m unittest discover tests -v

O ConversationManager é testado diretamente com valores fixos de valência/atividade/confiança,
para que os testes não dependam do léxico (tópicos 1/2)."""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.policy import BILINGUAL_CLARIFICATION, ConversationManager  # noqa: E402


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.cm = ConversationManager()

    def say(self, text, valence=0.0, activity=0.0, confidence=0.9, label="neutral"):
        """Envia uma mensagem e devolve um dict com o resultado (mais fácil de ler nos testes)."""
        action, reply, conf, flags, details = self.cm.update_and_decide(text, valence, activity, confidence, label)
        return {"action": action, "reply": reply, "confidence": conf, "flags": flags, "details": details}

    def test_legal_threat_escalates_even_when_calm(self):
        r = self.say("I will talk to my lawyer about this", valence=0.3)
        self.assertEqual(r["action"], "ESCALATE")
        self.assertIn("legal_or_escalation_threat", r["flags"])

    def test_human_request_offers_then_escalates(self):
        self.assertEqual(self.say("I want to speak to a human please")["action"], "OFFER_HUMAN")
        self.assertEqual(self.say("Just let me talk to a real person")["action"], "ESCALATE")

    def test_yes_to_human_offer_hands_off(self):
        self.say("I want to speak to a human please")
        r = self.say("yes")
        self.assertEqual(r["action"], "ESCALATE")
        self.assertEqual(r["details"]["rule"], "accepted_human_offer")

    def test_negative_streak_offers_then_escalates(self):
        actions = [self.say(t, valence=-0.5, activity=0.2)["action"] for t in (
            "My order arrived broken",
            "Nobody answered my emails about the broken order",
            "This keeps getting worse and worse for me every day",
        )]
        self.assertEqual(actions, ["ANSWER_EMPATHIC", "OFFER_HUMAN", "ESCALATE"])

    def test_ambiguous_message_asks_clarification_only_once(self):
        self.assertEqual(self.say("ok")["action"], "ASK_CLARIFICATION")
        self.assertNotEqual(self.say("whatever")["action"], "ASK_CLARIFICATION")

    def test_sarcasm_is_treated_as_negative(self):
        r = self.say("Great, another delay", valence=0.6)
        self.assertIn("sarcasm_suspected", r["flags"])
        self.assertEqual(r["action"], "ANSWER_EMPATHIC")

    def test_closing(self):
        self.assertEqual(self.say("Thank you, that is all I needed", valence=0.6)["action"], "CLOSE_POSITIVE")
        self.cm.reset()
        self.assertNotEqual(self.say("Thanks but it is still broken", valence=0.3)["action"], "CLOSE_POSITIVE")

    def test_language(self):
        self.assertEqual(self.say("Onde está a minha encomenda?")["details"]["lang"], "pt")
        self.cm.reset()
        r = self.say("Wo ist meine Bestellung")
        self.assertEqual(r["action"], "ASK_CLARIFICATION")
        self.assertEqual(r["reply"], BILINGUAL_CLARIFICATION)

    def test_reset_clears_memory(self):
        self.say("I want to speak to a human please")
        self.say("My order is a total disaster", valence=-0.9, activity=0.8)
        self.cm.reset()
        self.assertEqual((self.cm.state_valence, self.cm.neg_streak, self.cm.offered_human), (0.0, 0, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
