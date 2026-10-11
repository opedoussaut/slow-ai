"""Tests for the 100 MW-class campus scenario used by the v3 video."""
import json
import unittest
from pathlib import Path

from story.generator.campus import build

BUNDLE = Path(__file__).parent / "data" / "campus-v1.json"


class CampusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = build()

    def test_committed_bundle_is_reproducible(self):
        committed = json.loads(BUNDLE.read_text(encoding="utf-8"))
        self.assertEqual(committed, json.loads(json.dumps(self.b)),
                         "story/data/campus-v1.json differs; run python -m story.generator.campus")

    def test_labelled_as_simulation(self):
        self.assertEqual(self.b["evidence_kind"], "reproducible_simulation")
        self.assertIn("simulated", self.b["disclaimer"])

    def test_route_counts_form_a_pyramid(self):
        c = {int(k): v for k, v in self.b["route_counts"].items()}
        self.assertGreater(c[1], c[2])
        self.assertGreater(c[2], c[3])
        self.assertGreater(c[3], c[4])
        self.assertEqual(c[4], 1)

    def test_escalation_accounting_is_consistent(self):
        e = self.b["escalation_summary"]
        cameras = len(self.b["camera_calls"])
        self.assertEqual(e["count"] + cameras, self.b["route_counts"]["3"])
        self.assertLessEqual(e["compact_correct"], e["count"])
        self.assertLessEqual(e["specialized_correct"], e["count"])

    def test_decision_model_warning_precedes_throttling(self):
        q = self.b["questions"]["throttle_risk"]
        self.assertGreater(q["p_compact"], 0.8)
        self.assertIsNotNone(q["actually_throttled_at"])
        self.assertGreater(q["actually_throttled_at"], "16:40")

    def test_supply_limit_question_answers_no(self):
        q = self.b["questions"]["supply_limit"]
        self.assertLess(q["supply_c"], q["limit_c"])

    def test_scale_matches_reference_range(self):
        c = self.b["campus"]
        self.assertTrue(130 <= c["rack_kw"] <= 150)
        self.assertTrue(70 <= c["it_load_mw"] <= 100)


if __name__ == "__main__":
    unittest.main()
