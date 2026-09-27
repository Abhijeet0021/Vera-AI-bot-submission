"""Unit tests for Vera AI Engagement Engine."""

import unittest
import json
from pathlib import Path

from engine.models import CategoryContext, MerchantContext, TriggerContext, CustomerContext
from engine.context_store import ContextStore
from engine.grounding_validator import GroundingValidator
from engine.voice_adapter import VoiceAdapter
from engine.composer import EngagementComposer
from engine.conversation_handlers import ConversationHandler
import bot

DATASET_DIR = Path(__file__).parent.parent / "dataset"


class TestGroundingValidator(unittest.TestCase):
    def setUp(self):
        self.category = {
            "slug": "dentists",
            "voice": {"vocab_taboo": ["guaranteed", "100% safe", "miracle cure"]},
            "peer_stats": {"avg_ctr": 0.030}
        }
        self.merchant = {
            "merchant_id": "m_001",
            "identity": {"name": "Dr. Meera Clinic", "owner_first_name": "Meera"},
            "performance": {"views": 2410, "calls": 18, "ctr": 0.021},
            "offers": [{"title": "Dental Cleaning @ ₹299", "status": "active"}]
        }
        self.trigger = {
            "kind": "perf_dip",
            "payload": {"metric": "calls", "delta_pct": -0.50}
        }

    def test_valid_grounded_message(self):
        body = "Dr. Meera, your calls dropped 50% this week. Peer CTR is 3.0% vs your 2.1%. Dental Cleaning @ ₹299 is active."
        is_valid, errors = GroundingValidator.validate(body, self.category, self.merchant, self.trigger)
        self.assertTrue(is_valid, f"Validation failed unexpectedly: {errors}")

    def test_taboo_word_detection(self):
        body = "Dr. Meera, we offer a guaranteed cleaning procedure!"
        is_valid, errors = GroundingValidator.validate(body, self.category, self.merchant, self.trigger)
        self.assertFalse(is_valid)
        self.assertTrue(any("taboo" in e.lower() for e in errors))

    def test_hallucinated_number_detection(self):
        body = "Dr. Meera, your calls dropped 99% and we have a 75% discount!"
        is_valid, errors = GroundingValidator.validate(body, self.category, self.merchant, self.trigger)
        self.assertFalse(is_valid)
        self.assertTrue(any("ungrounded" in e.lower() for e in errors))

    def test_url_detection(self):
        body = "Check our website at https://magicpin.com/dentists"
        is_valid, errors = GroundingValidator.validate(body, self.category, self.merchant, self.trigger)
        self.assertFalse(is_valid)
        self.assertTrue(any("url" in e.lower() for e in errors))


class TestVoiceAdapter(unittest.TestCase):
    def test_dentist_salutation(self):
        merchant = {"identity": {"owner_first_name": "Meera", "name": "Dental Clinic"}}
        sal = VoiceAdapter.get_salutation(merchant, "dentists")
        self.assertEqual(sal, "Dr. Meera")

    def test_pharmacy_salutation_hinglish(self):
        merchant = {"identity": {"owner_first_name": "Ramesh", "languages": ["en", "hi"]}}
        sal = VoiceAdapter.get_salutation(merchant, "pharmacies")
        self.assertEqual(sal, "Ramesh ji")

    def test_hinglish_detection(self):
        merchant_hi = {"identity": {"languages": ["hi", "en"]}}
        self.assertTrue(VoiceAdapter.is_hinglish(merchant_hi))
        merchant_en = {"identity": {"languages": ["en"]}}
        self.assertFalse(VoiceAdapter.is_hinglish(merchant_en))


class TestContextStore(unittest.TestCase):
    def setUp(self):
        self.store = ContextStore()

    def test_push_and_idempotency(self):
        ok, reason, ver = self.store.push_context("category", "dentists", 1, {"slug": "dentists"})
        self.assertTrue(ok)
        self.assertEqual(ver, 1)

        # Stale version reject
        ok, reason, ver = self.store.push_context("category", "dentists", 1, {"slug": "dentists"})
        self.assertFalse(ok)
        self.assertEqual(reason, "stale_version")

        # Version bump accept
        ok, reason, ver = self.store.push_context("category", "dentists", 2, {"slug": "dentists", "updated": True})
        self.assertTrue(ok)
        self.assertEqual(self.store.get_version("category", "dentists"), 2)


class TestConversationHandler(unittest.TestCase):
    def setUp(self):
        self.handler = ConversationHandler()

    def test_auto_reply_detection(self):
        resp = self.handler.handle_reply(
            conversation_id="c1",
            merchant_id="m1",
            customer_id=None,
            from_role="merchant",
            message="Thank you for contacting us! Our team will respond shortly.",
            turn_number=1
        )
        self.assertIn(resp["action"], ("wait", "end"))

    def test_intent_transition_mode(self):
        resp = self.handler.handle_reply(
            conversation_id="c2",
            merchant_id="m1",
            customer_id=None,
            from_role="merchant",
            message="Ok lets do it. Whats next?",
            turn_number=2
        )
        self.assertEqual(resp["action"], "send")
        body_lower = resp["body"].lower()
        actioning = ["done", "sending", "draft", "here", "confirm", "proceed", "next"]
        qualifying = ["would you", "do you", "can you tell", "what if", "how about"]
        self.assertTrue(any(w in body_lower for w in actioning), f"Missing actioning words in: {resp['body']}")
        self.assertFalse(any(w in body_lower for w in qualifying), f"Contained qualifying words in: {resp['body']}")

    def test_hostile_handling(self):
        resp = self.handler.handle_reply(
            conversation_id="c3",
            merchant_id="m1",
            customer_id=None,
            from_role="merchant",
            message="Stop messaging me. This is useless spam.",
            turn_number=2
        )
        self.assertEqual(resp["action"], "end")


class TestComposerEndToEnd(unittest.TestCase):
    def setUp(self):
        with open(DATASET_DIR / "categories" / "dentists.json") as f:
            self.dentist_cat = json.load(f)
        with open(DATASET_DIR / "merchants_seed.json") as f:
            self.merchants = {m["merchant_id"]: m for m in json.load(f)["merchants"]}
        with open(DATASET_DIR / "triggers_seed.json") as f:
            self.triggers = {t["id"]: t for t in json.load(f)["triggers"]}

    def test_dentist_research_digest(self):
        trg = self.triggers["trg_001_research_digest_dentists"]
        merch = self.merchants[trg["merchant_id"]]
        composed = EngagementComposer.compose(self.dentist_cat, merch, trg)
        self.assertEqual(composed.send_as, "vera")
        self.assertIn("JIDA", composed.body)
        self.assertIn("2100", composed.body)
        self.assertIn("38%", composed.body)
        self.assertNotIn("guaranteed", composed.body.lower())
        self.assertLessEqual(len(composed.body.split()), 85)

    def test_customer_recall(self):
        trg = self.triggers["trg_003_recall_due_priya"]
        merch = self.merchants[trg["merchant_id"]]
        with open(DATASET_DIR / "customers_seed.json") as f:
            customers = {c["customer_id"]: c for c in json.load(f)["customers"]}
        cust = customers[trg["customer_id"]]
        composed = EngagementComposer.compose(self.dentist_cat, merch, trg, cust)
        self.assertEqual(composed.send_as, "merchant")
        self.assertIn("Priya", composed.body)
        self.assertIn("₹299", composed.body)
        self.assertIn("slots", composed.body.lower())


if __name__ == "__main__":
    unittest.main()
