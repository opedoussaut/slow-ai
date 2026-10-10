"""Dependency-free, reproducible baseline for SlowAI's minimum-sufficient-AI method.

This is a synthetic toy routing task, NOT a benchmark of any model or provider.
No external API, model download, energy meter, or token counter is used.
"""
from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

LABELS = ("normal", "inspect", "stop")


@dataclass(frozen=True)
class Case:
    id: str
    temperature_c: float
    vibration_mm_s: float
    alarm: bool
    expected: str


def load_cases(path: Path) -> list[Case]:
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = [Case(**row) for row in data]
    if not cases or len({c.id for c in cases}) != len(cases):
        raise ValueError("Expected non-empty dataset with unique IDs")
    for case in cases:
        if case.expected not in LABELS:
            raise ValueError(f"Invalid expected label: {case.expected}")
    return cases


def rules(case: Case) -> str:
    """Explicit safety-oriented thresholds, not learned from evaluation labels."""
    if case.alarm or case.temperature_c >= 90 or case.vibration_mm_s >= 12:
        return "stop"
    if case.temperature_c >= 75 or case.vibration_mm_s >= 7:
        return "inspect"
    return "normal"


def simple_score(case: Case) -> str:
    """A second non-ML baseline: additive risk score and fixed cutoffs."""
    score = int(case.alarm) * 3 + int(case.temperature_c >= 75) + int(case.temperature_c >= 85) + int(case.vibration_mm_s >= 7) + int(case.vibration_mm_s >= 10)
    return "stop" if score >= 3 else "inspect" if score >= 1 else "normal"


def evaluate(cases: list[Case], predictor) -> dict:
    started = time.perf_counter_ns()
    predictions = [predictor(case) for case in cases]
    elapsed_ns = time.perf_counter_ns() - started
    correct = sum(actual == case.expected for actual, case in zip(predictions, cases))
    confusion = {expected: {predicted: 0 for predicted in LABELS} for expected in LABELS}
    for case, predicted in zip(cases, predictions):
        if predicted not in LABELS:
            raise ValueError(f"Invalid predicted label: {predicted}")
        confusion[case.expected][predicted] += 1
    return {
        "cases": len(cases),
        "accuracy": correct / len(cases),
        "errors": len(cases) - correct,
        "confusion": confusion,
        "elapsed_ns": elapsed_ns,
        "mean_latency_ns": elapsed_ns / len(cases),
        "measurement_scope": "Local Python function calls only; single run, no warmup",
        "energy_joules": None,
        "cost_usd": None,
        "tokens": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SlowAI synthetic non-AI baselines")
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("synthetic_cases.json"))
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    cases = load_cases(args.data)
    report = {
        "experiment": "minimum-sufficient-ai / synthetic non-AI baselines",
        "dataset": str(args.data),
        "dataset_type": "synthetic, hand-authored, illustrative",
        "results": {"threshold_rules": evaluate(cases, rules), "additive_score": evaluate(cases, simple_score)},
        "caveats": ["Illustrative toy task; not an industrial validation.", "Timing is noisy and not comparable across hardware or environments.", "No energy, cost, token or AI model measurements were performed.", "Do not use these rules for operational safety decisions."],
    }
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
