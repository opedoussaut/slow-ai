import unittest

from challenge.benchmark import make_data, policy, rules, predict_knn, evaluate


class BenchmarkTests(unittest.TestCase):
    def test_seeded_data_reproducible(self):
        self.assertEqual(make_data(20, 202604), make_data(20, 202604))
        self.assertNotEqual(make_data(20, 202604), make_data(20, 202610))

    def test_rules(self):
        self.assertEqual(rules({"temperature_c": 55, "vibration_mm_s": 2, "alarm": False}), "normal")
        self.assertEqual(rules({"temperature_c": 80, "vibration_mm_s": 2, "alarm": False}), "inspect")
        self.assertEqual(rules({"temperature_c": 55, "vibration_mm_s": 2, "alarm": True}), "stop")

    def test_policy(self):
        self.assertEqual(policy({"temperature_c": 55, "vibration_mm_s": 2, "alarm": False}), "normal")
        self.assertEqual(policy({"temperature_c": 90, "vibration_mm_s": 11, "alarm": False}), "stop")

    def test_knn_returns_known_class(self):
        training = make_data(180, 202604)
        self.assertIn(predict_knn(make_data(1, 202610)[0], training), {"normal", "inspect", "stop"})

    def test_empty_training_rejected(self):
        with self.assertRaises(ValueError):
            predict_knn(make_data(1, 202610)[0], [])

    def test_evaluation_count(self):
        testing = make_data(90, 202610)
        result = evaluate(testing, rules, 2)
        self.assertEqual(result["total"], 90)
        self.assertEqual(result["correct"] + result["errors"], 90)
        self.assertGreaterEqual(result["median_wall_ms_per_case"], 0)


if __name__ == "__main__":
    unittest.main()
