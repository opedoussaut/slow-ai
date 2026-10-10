#!/usr/bin/env python3
"""Evaluate rules and a trained k-NN classifier on a user-supplied labeled CSV.

No data downloaded. Requires independent labels and a predeclared train/test split.
Standard library only. Energy and carbon are not measured.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

FEATURES = ("temperature_c", "vibration_mm_s", "alarm")
LABELS = {"normal", "inspect", "stop"}


def load(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"id", "split", "label", *FEATURES}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV needs columns: " + ", ".join(sorted(required)))
        records = []
        seen = set()
        for line, item in enumerate(reader, 2):
            ident = item["id"].strip()
            split = item["split"].strip().lower()
            label = item["label"].strip().lower()
            if not ident or ident in seen:
                raise ValueError(f"Line {line}: empty or duplicate ID")
            seen.add(ident)
            if split not in {"train", "test"} or label not in LABELS:
                raise ValueError(f"Line {line}: invalid split or label")
            try:
                t = float(item["temperature_c"])
                v = float(item["vibration_mm_s"])
                alarm_text = item["alarm"].strip().lower()
                if alarm_text not in {"0", "1", "false", "true"}:
                    raise ValueError("alarm must be 0/1 or true/false")
                alarm = alarm_text in {"1", "true"}
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Line {line}: invalid feature: {exc}") from exc
            if not all(math.isfinite(n) for n in (t, v)):
                raise ValueError(f"Line {line}: non-finite features")
            records.append({"id": ident, "split": split, "label": label, "t": t, "v": v, "a": alarm})
    if not any(r["split"] == "train" for r in records) or not any(r["split"] == "test" for r in records):
        raise ValueError("Both train and test rows are required")
    return records


def rules(row):
    if row["a"] or row["t"] >= 90 or row["v"] >= 12:
        return "stop"
    if row["t"] >= 75 or row["v"] >= 7:
        return "inspect"
    return "normal"


def fit_scale(training):
    result = {}
    for key in ("t", "v"):
        values = [row[key] for row in training]
        lo, hi = min(values), max(values)
        result[key] = (lo, max(hi - lo, 1e-12))
    return result


def knn(row, training, scale, k):
    def distance(other):
        return (
            ((row["t"] - other["t"]) / scale["t"][1]) ** 2
            + ((row["v"] - other["v"]) / scale["v"][1]) ** 2
            + float(row["a"] != other["a"])
        )
    nearest = sorted(training, key=lambda other: (distance(other), other["id"]))[:k]
    counts = Counter(other["label"] for other in nearest)
    return max(("stop", "inspect", "normal"), key=lambda name: counts[name])


def score(rows, predictor):
    predictions = []
    for row in rows:
        predicted = predictor(row)
        predictions.append({"id": row["id"], "expected": row["label"], "predicted": predicted})
    correct = sum(p["expected"] == p["predicted"] for p in predictions)
    by_class = {}
    for label in sorted(LABELS):
        support = sum(p["expected"] == label for p in predictions)
        tp = sum(p["expected"] == p["predicted"] == label for p in predictions)
        predicted_count = sum(p["predicted"] == label for p in predictions)
        by_class[label] = {
            "support": support,
            "precision": tp / predicted_count if predicted_count else None,
            "recall": tp / support if support else None,
        }
    return {"accuracy": correct / len(rows), "correct": correct, "total": len(rows), "by_class": by_class, "predictions": predictions}


def run(path, k):
    records = load(path)
    training = [r for r in records if r["split"] == "train"]
    testing = [r for r in records if r["split"] == "test"]
    if k > len(training):
        raise ValueError("k must not exceed the number of training rows")
    scale = fit_scale(training)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "protocol": "slowai-external-labels-v1",
        "dataset_sha256": digest,
        "dataset_path": str(path),
        "train_count": len(training),
        "test_count": len(testing),
        "knn_k": k,
        "normalization": "min-max range derived from training only; no test-set fitting",
        "results": {
            "threshold_rules": score(testing, rules),
            "knn": score(testing, lambda row: knn(row, training, scale, k)),
        },
        "measurements": {"energy_joules": None, "carbon_gco2e": None, "cost_usd": None, "latency_ms": None, "frontier_ai": None},
        "limitations": [
            "User must establish that labels are independent, appropriate, and legally usable.",
            "Predefined train/test split is supplied by user; no leakage checks beyond duplicate IDs.",
            "Threshold rules are illustrative and not calibrated to this dataset.",
            "No model-selection validation set or uncertainty intervals in this first protocol.",
            "No energy, carbon, cost or latency measured.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("challenge/real-data-report.json"))
    parser.add_argument("--k", type=int, default=3)
    args = parser.parse_args()
    if args.k < 1:
        parser.error("--k must be >= 1")
    result = run(args.csv, args.k)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for name, values in result["results"].items():
        print(f"{name}: {values['correct']}/{values['total']} = {values['accuracy']:.1%}")
    print(f"Evidence: {args.output}")


if __name__ == "__main__":
    main()
