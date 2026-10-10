import csv
import tempfile
import unittest
from pathlib import Path
from challenge.external_benchmark import run, load

class ExternalBenchmarkTests(unittest.TestCase):
    def create_csv(self, directory, rows):
        path = Path(directory) / "cases.csv"
        with path.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["id", "split", "label", "temperature_c", "vibration_mm_s", "alarm"])
            writer.writerows(rows)
        return path

    def test_separate_split_and_metrics(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.create_csv(d, [
                ["a", "train", "normal", 40, 2, 0],
                ["b", "train", "inspect", 78, 8, 0],
                ["c", "train", "stop", 99, 14, 1],
                ["d", "test", "normal", 42, 2, 0],
                ["e", "test", "stop", 100, 15, 1],
            ])
            report = run(path, 1)
            self.assertEqual(report["train_count"], 3)
            self.assertEqual(report["test_count"], 2)
            self.assertEqual(report["results"]["threshold_rules"]["correct"], 2)
            self.assertEqual(report["results"]["knn"]["correct"], 2)
            self.assertIsNone(report["measurements"]["energy_joules"])

    def test_duplicate_id_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.create_csv(d, [
                ["a", "train", "normal", 40, 2, 0],
                ["a", "test", "normal", 40, 2, 0],
            ])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load(path)

    def test_invalid_k_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = self.create_csv(d, [
                ["a", "train", "normal", 40, 2, 0],
                ["b", "test", "normal", 40, 2, 0],
            ])
            with self.assertRaisesRegex(ValueError, "k must not exceed"):
                run(path, 3)

if __name__ == "__main__":
    unittest.main()
