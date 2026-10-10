#!/usr/bin/env python3
"""UCI Steel Plates Faults: independently supplied seven-class fault labels.

Downloads official UCI archive on explicit --download only. Standard library.
This task is NOT the three-class cooling-loop scenario.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import json
import math
import random
import statistics
import time
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

SOURCE = "https://archive.ics.uci.edu/static/public/198/steel+plates+faults.zip"
CLASSES = ("Pastry", "Z_Scratch", "K_Scatch", "Stains", "Dirtiness", "Bumps", "Other_Faults")
FEATURES = ("X_Minimum X_Maximum Y_Minimum Y_Maximum Pixels_Areas X_Perimeter Y_Perimeter "
            "Sum_of_Luminosity Minimum_of_Luminosity Maximum_of_Luminosity Length_of_Conveyer "
            "TypeOfSteel_A300 TypeOfSteel_A400 Steel_Plate_Thickness Edges_Index Empty_Index "
            "Square_Index Outside_X_Index Edges_X_Index Edges_Y_Index Outside_Global_Index "
            "LogOfAreas Log_X_Index Log_Y_Index Orientation_Index Luminosity_Index SigmoidOfAreas").split()


def download(path: Path) -> None:
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "SlowAI-research/0.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("Archive unexpectedly large")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def parse_archive(blob: bytes) -> list[dict]:
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".nna")]
        if len(names) != 1:
            raise ValueError("Expected exactly one .NNA file in UCI archive")
        text = archive.read(names[0]).decode("utf-8-sig")
    records = []
    for line, raw in enumerate(text.splitlines(), 1):
        if not raw.strip():
            continue
        parts = raw.split()
        if len(parts) != 34:
            raise ValueError(f"Line {line}: expected 27 features and 7 labels, got {len(parts)}")
        numbers = [float(value) for value in parts]
        if not all(math.isfinite(n) for n in numbers):
            raise ValueError(f"Line {line}: nonfinite value")
        targets = numbers[27:]
        if targets.count(1.0) != 1 or any(x not in (0.0, 1.0) for x in targets):
            raise ValueError(f"Line {line}: labels must be one-hot")
        records.append({"id": line, "x": numbers[:27], "label": CLASSES[targets.index(1.0)]})
    if not records:
        raise ValueError("Empty dataset")
    return records


def split(records: list[dict], seed: int = 20261010):
    """Stratified 80/20 split, preserving minority classes."""
    rng = random.Random(seed)
    by_class = {label: [] for label in CLASSES}
    for row in records:
        by_class[row["label"]].append(row)
    train, test = [], []
    for label in CLASSES:
        rows = by_class[label][:]
        if len(rows) < 2:
            raise ValueError(f"Too few rows for {label}")
        rng.shuffle(rows)
        n_test = max(1, round(len(rows) * 0.2))
        test.extend(rows[:n_test])
        train.extend(rows[n_test:])
    train.sort(key=lambda r: r["id"])
    test.sort(key=lambda r: r["id"])
    return train, test


def fit(train):
    lo = [min(row["x"][j] for row in train) for j in range(27)]
    span = [max(max(row["x"][j] for row in train) - lo[j], 1e-12) for j in range(27)]
    return lo, span


def transform(rows, lo, span):
    return [(row["id"], [(v-lo[j])/span[j] for j, v in enumerate(row["x"])], row["label"]) for row in rows]


def predict_knn(point, train, k=3):
    distances = []
    for ident, x, label in train:
        d = sum((a-b)**2 for a,b in zip(point, x))
        distances.append((d, ident, label))
    nearest = sorted(distances)[:k]
    counts = Counter(label for _,_,label in nearest)
    return max(CLASSES, key=lambda label: counts[label])


def predict_majority(train):
    counts = Counter(row["label"] for row in train)
    return max(CLASSES, key=lambda label: counts[label])


def evaluate(test, predict):
    predictions = []
    start = time.perf_counter_ns()
    for row in test:
        predicted = predict(row)
        predictions.append({"id": row[0], "expected": row[2], "predicted": predicted})
    elapsed = time.perf_counter_ns() - start
    correct = sum(p["expected"] == p["predicted"] for p in predictions)
    metrics = {}
    for label in CLASSES:
        tp = sum(p["expected"] == p["predicted"] == label for p in predictions)
        support = sum(p["expected"] == label for p in predictions)
        predicted_count = sum(p["predicted"] == label for p in predictions)
        precision = tp / predicted_count if predicted_count else 0.0
        recall = tp / support if support else 0.0
        metrics[label] = {"support": support, "precision": precision, "recall": recall,
                          "f1": 2*precision*recall/(precision+recall) if precision+recall else 0.0}
    return {"accuracy": correct/len(test), "macro_f1": statistics.mean(v["f1"] for v in metrics.values()),
            "correct": correct, "total": len(test), "per_class": metrics,
            "wall_ms_per_case": elapsed / 1e6 / len(test), "predictions": predictions}


def run(blob: bytes, k=3):
    if k < 1:
        raise ValueError("k must be >=1")
    rows = parse_archive(blob)
    train, test = split(rows)
    if k > len(train):
        raise ValueError("k exceeds train size")
    lo, span = fit(train)
    train_scaled = transform(train, lo, span)
    test_scaled = transform(test, lo, span)
    majority = predict_majority(train)
    return {
        "experiment": "UCI Steel Plates Faults 7-class classification",
        "source": SOURCE,
        "citation": "Buscema, M., Terzi, S., & Tastle, W. (2010). Steel Plates Faults. UCI ML Repository. DOI:10.24432/C5J88N",
        "license": "CC BY 4.0",
        "source_sha256": hashlib.sha256(blob).hexdigest(),
        "dataset_size": len(rows), "train_count": len(train), "test_count": len(test),
        "split": "stratified 80/20; seed 20261010; test not used for fitting",
        "features": FEATURES, "classes": CLASSES,
        "results": {
            "majority_class_non_ai": evaluate(test_scaled, lambda row: majority),
            "knn_3": evaluate(test_scaled, lambda row: predict_knn(row[1], train_scaled, k)),
        },
        "measurements": {"energy_joules": None, "carbon_gco2e": None, "financial_cost": None},
        "limitations": [
            "This is 7-class fault-type classification on feature vectors; not anomaly detection or safety action.",
            "The majority-class baseline is intentionally weak; add a meaningful domain-rule baseline before making minimum-AI claims.",
            "Single train/test split; no tuning/validation set, confidence intervals or grouped leakage audit.",
            "Wall-clock timing is local and not a cross-hardware performance benchmark.",
            "Original label provenance and independent annotation quality are not established by the UCI metadata.",
            "No frontier model, energy, CO2e or financial cost measured.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path("challenge/data/steel-plates-faults.zip"))
    parser.add_argument("--download", action="store_true", help="Fetch official UCI archive")
    parser.add_argument("--output", type=Path, default=Path("challenge/steel-evidence.json"))
    args = parser.parse_args()
    if args.download:
        download(args.archive)
    if not args.archive.exists():
        parser.error("Archive missing; pass --download to fetch it from UCI")
    report = run(args.archive.read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    for name, result in report["results"].items():
        print(f"{name}: accuracy {result['accuracy']:.1%}, macro-F1 {result['macro_f1']:.3f}")
    print(f"Evidence: {args.output}")


if __name__ == "__main__":
    main()
