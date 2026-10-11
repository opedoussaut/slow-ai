import json
from pathlib import Path

import pytest

from experiments.minimum_ai import Case, evaluate, load_cases, rules, simple_score


DATA = Path(__file__).resolve().parents[1] / "experiments" / "synthetic_cases.json"


def test_fixture_and_reproducibility():
    cases = load_cases(DATA)
    assert len(cases) == 12
    assert [rules(c) for c in cases] == [rules(c) for c in cases]


def test_safety_alarm_and_thresholds():
    assert rules(Case("a", 20, 1, True, "stop")) == "stop"
    assert rules(Case("b", 90, 1, False, "stop")) == "stop"
    assert rules(Case("c", 20, 12, False, "stop")) == "stop"


def test_metrics_and_missing_measurements():
    result = evaluate(load_cases(DATA), rules)
    assert result["cases"] == 12
    assert sum(sum(row.values()) for row in result["confusion"].values()) == 12
    assert result["energy_joules"] is None
    assert result["cost_usd"] is None
    assert 0 <= result["accuracy"] <= 1


def test_additive_baseline_returns_valid_labels():
    assert all(simple_score(c) in {"normal", "inspect", "stop"} for c in load_cases(DATA))


def test_reject_duplicate_ids(tmp_path):
    case = dict(id="duplicate", temperature_c=40, vibration_mm_s=1, alarm=False, expected="normal")
    path = tmp_path / "cases.json"
    path.write_text(json.dumps([case, case]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_cases(path)
