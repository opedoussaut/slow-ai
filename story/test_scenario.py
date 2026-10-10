"""Tests for the SlowAI story scenario generator.

The committed bundle must be exactly what the generator produces, so every
number on the public story page can be regenerated from the seed.
"""
import json
import unittest
from pathlib import Path

from story.generator.scenario import SEED, VARIANTS, build_bundle, build_raw, curate, evidence_recall, predict

BUNDLE = Path(__file__).parent / "data" / "scenario-v1.json"


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = build_bundle(SEED)

    def test_committed_bundle_is_reproducible(self):
        committed = json.loads(BUNDLE.read_text(encoding="utf-8"))
        regenerated = json.loads(json.dumps(self.bundle, ensure_ascii=False))
        self.assertEqual(committed, regenerated,
                         "story/data/scenario-v1.json differs from the generator; run "
                         "python -m story.generator.scenario")

    def test_labelled_as_simulation(self):
        self.assertEqual(self.bundle["evidence_kind"], "reproducible_simulation")
        self.assertIn("not a measurement", self.bundle["disclaimer"])

    def test_every_ledger_item_has_provenance(self):
        for variant in self.bundle["variants"].values():
            for item in variant["curation"]["ledger"]:
                self.assertTrue(item.get("records"), item["label"])

    def test_curation_reduces_and_retains_main_fault_evidence(self):
        main = self.bundle["variants"]["main"]
        stages = main["curation"]["stages"]
        self.assertEqual(stages[0]["kept"], main["raw"]["total"])
        self.assertLess(len(main["curation"]["ledger"]), main["raw"]["total"] / 1000)
        self.assertEqual(main["recall"]["recall"], 1.0)

    def test_subtle_variant_exposes_a_curation_miss(self):
        subtle = self.bundle["variants"]["subtle"]
        self.assertLess(subtle["recall"]["recall"], 1.0)
        self.assertTrue(subtle["recall"]["missed"])

    def test_conflicting_sensor_is_flagged_not_used(self):
        main = self.bundle["variants"]["main"]
        conflicts = [x for x in main["curation"]["ledger"] if x["type"] == "conflict"]
        self.assertEqual(len(conflicts), 1)
        self.assertIn("stuck", conflicts[0]["detail"].lower())

    def test_routing_story_holds_with_trained_models(self):
        models = self.bundle["models"]
        f = self.bundle["variants"]["main"]["features"]
        actionable = predict(models["actionable"], [f[k] for k in models["actionable"]["features"]])
        compact = predict(models["compact_fault"], [f[k] for k in models["compact_fault"]["features"]])
        special = predict(models["specialized_fault"], [f[k] for k in models["specialized_fault"]["features"]])
        self.assertGreater(actionable[1], 0.9)       # decision model is confident
        self.assertLess(max(compact), 0.8)            # compact model is not -> escalate
        self.assertEqual(special.index(max(special)), 0)  # specialized: branch restriction
        self.assertGreater(max(special), 0.8)

    def test_supply_limit_question_is_deterministic(self):
        main = self.bundle["variants"]["main"]
        self.assertLess(main["supply_c_now"], self.bundle["supply_limit_c"])

    def test_raw_generation_is_seeded(self):
        a = build_raw(VARIANTS[0])
        b = build_raw(VARIANTS[0])
        self.assertEqual(a["rack"][:50], b["rack"][:50])
        self.assertEqual(evidence_recall(VARIANTS[0], curate(a))["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
