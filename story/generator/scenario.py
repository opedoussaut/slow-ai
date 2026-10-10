#!/usr/bin/env python3
"""SlowAI story scenario: a seeded, reproducible AI Factory cooling-loop simulation.

Everything here is SYNTHETIC. It exists to demonstrate the SlowAI method
(curate first, then allocate the minimum sufficient intelligence) with numbers
that anyone can regenerate byte for byte. Nothing produced here is a measurement
of a real facility, a real model provider or real resource consumption.

Standard library only. Run:

    python -m story.generator.scenario --output story/data/scenario-v1.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "slowai-story-scenario/1"
SEED = 20261010
MINUTES = 24 * 60
NOW = 21 * 60  # decision time: 21:00 simulated
RACKS_A = [f"R{i:02d}" for i in range(1, 13)]   # cooling loop A (CDU-A)
RACKS_B = [f"R{i:02d}" for i in range(13, 25)]  # cooling loop B (CDU-B)
TARGET = "R07"
NOMINAL_FLOW = 60.0      # l/min per rack branch
SUPPLY_LIMIT_C = 32.0    # illustrative approved limit for Route 1
THROTTLE_C = 87.0        # GPU temperature at which throttling starts
CLASSES = ("branch_restriction", "pump_degradation", "sensor_drift", "air_ingress")
CLASS_LABELS = {
    "branch_restriction": "Branch restriction",
    "pump_degradation": "Pump degradation",
    "sensor_drift": "Flow-sensor drift",
    "air_ingress": "Air ingress",
}


def r3(x: float) -> float:
    return round(x, 3)


def hhmm(t: int) -> str:
    return f"{(t // 60) % 24:02d}:{t % 60:02d}"


# ---------------------------------------------------------------------------
# 1. Raw source universe
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Variant:
    key: str
    title: str
    restriction_max: float  # fraction of flow lost on the target branch
    onset: int = 17 * 60
    ramp: int = 150


VARIANTS = (
    Variant("main", "Branch restriction on rack R07", 0.36),
    Variant("subtle", "Subtle restriction on rack R07 (curation stress test)", 0.07),
)


def restriction(v: Variant, t: int) -> float:
    if t < v.onset:
        return 0.0
    return v.restriction_max * min(1.0, (t - v.onset) / v.ramp)


def build_raw(v: Variant, seed: int = SEED) -> dict:
    """Return every raw record of the 24-hour window, keyed by source."""
    rng = random.Random(f"{seed}:{v.key}")
    rack_rows, cdu_rows, events, tickets = [], [], [], []
    load = {r: rng.uniform(0.82, 0.97) for r in RACKS_A + RACKS_B}
    stuck_from = 15 * 60 + 42  # R07 secondary flow meter sticks (conflicting evidence)
    for t in range(MINUTES):
        diurnal = 0.06 * math.sin((t - 9 * 60) / MINUTES * 2 * math.pi)
        for cdu, racks in (("CDU-A", RACKS_A), ("CDU-B", RACKS_B)):
            maint = cdu == "CDU-B" and 13 * 60 <= t < 14 * 60  # planned maintenance decoy
            supply = 24.0 + 0.6 * diurnal * 10 + rng.gauss(0, 0.15) + (1.4 if maint else 0.0)
            pump = 72.0 + rng.gauss(0, 0.6) + (-12.0 if maint else 0.0)
            dp = 118.0 + rng.gauss(0, 1.2) + (-15.0 if maint else 0.0)
            if cdu == "CDU-A":
                dp += 9.0 * restriction(v, t) / max(v.restriction_max, 1e-9) * (v.restriction_max / 0.36)
            cdu_rows.append({"id": f"C{len(cdu_rows):06d}", "t": t, "cdu": cdu,
                             "supply_c": r3(supply), "pump_pct": r3(pump), "dp_kpa": r3(dp)})
            for rack in racks:
                r = restriction(v, t) if rack == TARGET else 0.0
                util = min(1.0, load[rack] + diurnal + rng.gauss(0, 0.02))
                power_kw = 95.0 * util
                valve = 55.0 + 120.0 * r + rng.gauss(0, 0.8)
                flow = NOMINAL_FLOW * (1 - r) * (1 + 0.004 * (valve - 55.0) / 10) + rng.gauss(0, 0.7)
                if rack == "R03" and 8 * 60 <= t < 8 * 60 + 25:
                    flow = 0.0  # sensor dropout decoy: reads zero, temperatures stay normal
                delta_t = power_kw * 60 / (max(flow, 1.0) * 4.18) if flow > 0 else 22.8
                ret = supply + min(delta_t, 40.0) + rng.gauss(0, 0.2)
                gpu = 64.5 + 0.62 * (ret - 24.0) + 6.0 * util + rng.gauss(0, 0.6)
                throttle = max(0, int((gpu - THROTTLE_C) * 2.2 + rng.gauss(0, 0.6))) if gpu > THROTTLE_C else 0
                flow_b = 60.0 if (rack == TARGET and t >= stuck_from) else flow + rng.gauss(0, 0.5)
                rack_rows.append({"id": f"K{len(rack_rows):06d}", "t": t, "rack": rack, "cdu": cdu,
                                  "flow_lpm": r3(flow), "flow_b_lpm": r3(flow_b), "valve_pct": r3(valve),
                                  "return_c": r3(ret), "gpu_c": r3(gpu), "throttle": throttle,
                                  "util": r3(util)})
        # Event noise: scheduler, nuisance alarms, network flaps on pod 2
        for _ in range(rng.choice((0, 1, 1, 2, 2, 3))):
            events.append({"id": f"E{len(events):06d}", "t": t, "kind": "scheduler",
                           "rack": rng.choice(RACKS_A + RACKS_B), "detail": rng.choice(("job start", "job end", "checkpoint"))})
        if rng.random() < 0.55:
            events.append({"id": f"E{len(events):06d}", "t": t, "kind": "nuisance_alarm",
                           "rack": rng.choice(RACKS_A + RACKS_B), "detail": rng.choice(("door open", "fan rpm deviation", "humidity transient", "PDU phase imbalance"))})
        if 18 * 60 <= t < 18 * 60 + 40 and rng.random() < 0.8:
            events.append({"id": f"E{len(events):06d}", "t": t, "kind": "network_flap",
                           "rack": rng.choice(("R05", "R06", "R07", "R08")), "detail": "fabric link retrain"})
    for i in range(48):
        tickets.append({"id": f"T{i:04d}", "t": rng.randrange(MINUTES), "asset": rng.choice(RACKS_A + RACKS_B + ["CDU-A", "CDU-B"]),
                        "detail": rng.choice(("filter inspection", "firmware update", "leak-check", "valve calibration", "fan replacement"))})
    tickets.append({"id": "T9001", "t": 13 * 60, "asset": "CDU-B", "detail": "planned pump service (scheduled)"})
    tickets.sort(key=lambda x: x["t"])
    docs = [
        {"id": "D-RB-12", "title": "Runbook: low branch flow with high valve demand", "tags": ["flow_drop", "valve_rise"]},
        {"id": "D-RB-07", "title": "Runbook: CDU pump degradation", "tags": ["pump_drop", "dp_drop"]},
        {"id": "D-RB-03", "title": "Runbook: suspected flow-meter fault", "tags": ["sensor_stuck"]},
        {"id": "D-RB-21", "title": "Runbook: GPU thermal throttling", "tags": ["throttle"]},
        {"id": "D-PL-02", "title": "Policy: workload drain requires Infrastructure Operations approval", "tags": ["throttle", "flow_drop"]},
        {"id": "D-RB-30", "title": "Runbook: fabric link retraining", "tags": ["network_flap"]},
    ] + [{"id": f"D-AR-{i:03d}", "title": f"Archived procedure {i:03d}", "tags": ["archive"]} for i in range(60)]
    return {"rack": rack_rows, "cdu": cdu_rows, "events": events, "tickets": tickets, "docs": docs}


def raw_counts(raw: dict) -> dict:
    return {k: len(v) for k, v in raw.items()}


def raw_bytes(raw: dict) -> int:
    return sum(len(json.dumps(row, separators=(",", ":"))) + 1 for rows in raw.values() for row in rows)


# ---------------------------------------------------------------------------
# 2. Deterministic curation pipeline
# ---------------------------------------------------------------------------

SIGNALS = ("flow_lpm", "valve_pct", "return_c", "gpu_c", "throttle")
BASELINE = (6 * 60, 12 * 60)  # baseline window used for change detection
WINDOW = (NOW - 6 * 60, NOW)  # decision window: last six hours


def _stats(values):
    m = sum(values) / len(values)
    sd = math.sqrt(sum((x - m) ** 2 for x in values) / max(len(values) - 1, 1))
    return m, max(sd, 1e-6)


def curate(raw: dict, k: float = 4.0, min_run: int = 10) -> dict:
    """Filter, validate, detect, aggregate, correlate and attach provenance.

    Returns per-stage counts, the evidence ledger and the decision context.
    `k` is the change-detection sensitivity (z-score), `min_run` the minimum
    number of consecutive deviating minutes that make an episode.
    """
    total = sum(len(v) for v in raw.values())
    stages = [{"stage": "Collected", "kept": total, "rule": "All records of the last 24 hours"}]

    # Stage 1 - scope: decision window and the affected cooling loop
    scoped_rack = [x for x in raw["rack"] if x["cdu"] == "CDU-A" and WINDOW[0] <= x["t"] < WINDOW[1]]
    scoped_cdu = [x for x in raw["cdu"] if x["cdu"] == "CDU-A" and WINDOW[0] <= x["t"] < WINDOW[1]]
    scoped_events = [x for x in raw["events"] if x["rack"] in RACKS_A and WINDOW[0] <= x["t"] < WINDOW[1]
                     and x["kind"] != "nuisance_alarm"]
    scoped_tickets = [x for x in raw["tickets"] if x["asset"] in RACKS_A + ["CDU-A"] and WINDOW[0] - 18 * 60 <= x["t"] < WINDOW[1]]
    n1 = len(scoped_rack) + len(scoped_cdu) + len(scoped_events) + len(scoped_tickets)
    stages.append({"stage": "Scoped", "kept": n1,
                   "rule": "Loop A only, last 6 hours; nuisance alarms and loop B removed"})

    # Stage 2 - validity: detect stuck or dropped-out sensors (deterministic)
    invalid, validity_flags = set(), []
    by_rack = {}
    for row in scoped_rack:
        by_rack.setdefault(row["rack"], []).append(row)
    for rack, rows in by_rack.items():
        rows.sort(key=lambda x: x["t"])
        run_start = None
        for i in range(1, len(rows)):
            same = rows[i]["flow_b_lpm"] == rows[i - 1]["flow_b_lpm"]
            if same and run_start is None:
                run_start = i - 1
            if (not same or i == len(rows) - 1) and run_start is not None:
                end = i if same else i - 1
                if end - run_start >= 15:
                    validity_flags.append({"rack": rack, "signal": "flow_b_lpm", "issue": "secondary flow meter stuck",
                                           "since": hhmm(rows[run_start]["t"]), "value": rows[run_start]["flow_b_lpm"],
                                           "records": [rows[run_start]["id"], rows[end]["id"]]})
                    invalid.add((rack, "flow_b_lpm"))
                run_start = None
    stages.append({"stage": "Validated", "kept": n1,
                   "rule": f"Stuck or dropped-out sensors flagged ({len(validity_flags)} found); their readings are excluded from reasoning"})

    # Stage 3 - change detection against each rack's own baseline
    base_rows = {}
    for row in raw["rack"]:
        if row["cdu"] == "CDU-A" and BASELINE[0] <= row["t"] < BASELINE[1]:
            base_rows.setdefault(row["rack"], []).append(row)
    deviating = {}
    for rack, rows in by_rack.items():
        for sig in SIGNALS:
            m, sd = _stats([x[sig] for x in base_rows[rack]])
            if sig == "throttle":
                hits = [x for x in rows if x[sig] > 0]
            else:
                hits = [x for x in rows if abs(x[sig] - m) / sd >= k]
            if hits:
                deviating[(rack, sig)] = (hits, m, sd)
    n3 = sum(len(h) for h, _, _ in deviating.values())
    stages.append({"stage": "Changes detected", "kept": n3,
                   "rule": f"Readings at least {k:g} standard deviations from each rack's own morning baseline"})

    # Stage 4 - aggregate consecutive deviations into episodes
    episodes = []
    for (rack, sig), (hits, m, sd) in sorted(deviating.items()):
        hits.sort(key=lambda x: x["t"])
        gap = 10 if sig == "throttle" else 2  # throttling is intermittent by nature
        run = [hits[0]]
        for row in hits[1:] + [None]:
            if row is not None and row["t"] - run[-1]["t"] <= gap:
                run.append(row)
                continue
            if len(run) >= min_run:
                vals = [x[sig] for x in run]
                episodes.append({"rack": rack, "signal": sig, "start": run[0]["t"], "end": run[-1]["t"],
                                 "minutes": run[-1]["t"] - run[0]["t"] + 1, "samples": len(run),
                                 "baseline": r3(m), "latest": r3(vals[-1]),
                                 "peak": r3(max(vals) if sig != "flow_lpm" else min(vals)),
                                 "records": [run[0]["id"], run[-1]["id"]]})
            run = [row] if row is not None else []
    stages.append({"stage": "Aggregated", "kept": len(episodes),
                   "rule": f"Consecutive deviations of at least {min_run} minutes merged into episodes"})

    # Stage 5 - correlate: keep episodes that co-occur with another signal on the same asset,
    # plus loop-level context (CDU), events and tickets on implicated assets, and tagged documents
    implicated = {}
    for ep in episodes:
        implicated.setdefault(ep["rack"], set()).add(ep["signal"])
    correlated = [ep for ep in episodes if len(implicated[ep["rack"]]) >= 2]
    assets = sorted({ep["rack"] for ep in correlated})
    cdu_window = [x for x in scoped_cdu if x["t"] >= NOW - 60]
    cdu_base = [x for x in raw["cdu"] if x["cdu"] == "CDU-A" and BASELINE[0] <= x["t"] < BASELINE[1]]
    related_events = [x for x in scoped_events if x["rack"] in assets and x["kind"] == "network_flap"]
    related_tickets = [x for x in scoped_tickets if x["asset"] in assets + ["CDU-A"]]
    tags = set()
    for ep in correlated:
        tags |= {"flow_lpm": {"flow_drop"}, "valve_pct": {"valve_rise"}, "throttle": {"throttle"}}.get(ep["signal"], set())
    if validity_flags:
        tags.add("sensor_stuck")
    if related_events:
        tags.add("network_flap")
    related_docs = [d for d in raw["docs"] if set(d["tags"]) & tags]

    ledger = []
    for ep in correlated:
        ledger.append({"type": "episode", "label": f"{ep['rack']} {SIGNAL_NAMES[ep['signal']]}",
                       "detail": _episode_text(ep), **ep})
    for f in validity_flags:
        ledger.append({"type": "conflict", "label": f"{f['rack']} secondary flow meter",
                       "detail": f"Stuck at {f['value']} l/min since {f['since']}; excluded, flagged for the human decision", **f})
    if cdu_window:
        sup = sum(x["supply_c"] for x in cdu_window) / len(cdu_window)
        pump = sum(x["pump_pct"] for x in cdu_window) / len(cdu_window)
        pump0 = sum(x["pump_pct"] for x in cdu_base) / len(cdu_base)
        dp = sum(x["dp_kpa"] for x in cdu_window) / len(cdu_window)
        dp0 = sum(x["dp_kpa"] for x in cdu_base) / len(cdu_base)
        ledger.append({"type": "context", "label": "CDU-A loop state (last 60 min)",
                       "detail": f"Supply {sup:.1f} °C · pump {pump:.1f} % (baseline {pump0:.1f}) · ΔP {dp:.1f} kPa (baseline {dp0:.1f})",
                       "supply_c": r3(sup), "pump_pct": r3(pump), "pump_base": r3(pump0), "dp_kpa": r3(dp), "dp_base": r3(dp0),
                       "records": [cdu_window[0]["id"], cdu_window[-1]["id"]], "samples": len(cdu_window)})
    if related_events:
        ledger.append({"type": "context", "label": "Fabric link retrains near affected rack",
                       "detail": f"{len(related_events)} events {hhmm(related_events[0]['t'])}–{hhmm(related_events[-1]['t'])}; kept as context, not correlated with flow",
                       "records": [related_events[0]["id"], related_events[-1]["id"]], "samples": len(related_events)})
    for tk in related_tickets:
        ledger.append({"type": "context", "label": f"Ticket {tk['id']} · {tk['asset']}", "detail": f"{tk['detail']} at {hhmm(tk['t'])}",
                       "records": [tk["id"]], "samples": 1})
    for d in related_docs:
        ledger.append({"type": "document", "label": d["id"], "detail": d["title"], "records": [d["id"]], "samples": 1})
    stages.append({"stage": "Correlated", "kept": len(ledger),
                   "rule": "Episodes confirmed by a second signal on the same asset, plus loop context, related events, tickets and procedures"})

    represented = sum(item.get("samples", 1) for item in ledger)
    return {"k": k, "min_run": min_run, "stages": stages, "ledger": ledger, "episodes": episodes,
            "validity_flags": validity_flags, "represented_records": represented, "total_records": total}


SIGNAL_NAMES = {"flow_lpm": "coolant flow", "valve_pct": "branch valve opening", "return_c": "return temperature",
                "gpu_c": "GPU temperature", "throttle": "GPU throttling"}


def _episode_text(ep: dict) -> str:
    unit = {"flow_lpm": "l/min", "valve_pct": "%", "return_c": "°C", "gpu_c": "°C", "throttle": "events/min"}[ep["signal"]]
    return (f"From {hhmm(ep['start'])} for {ep['minutes']} min: baseline {ep['baseline']:.1f} {unit}, "
            f"latest {ep['latest']:.1f} {unit}")


def ground_truth(v: Variant) -> list[dict]:
    """Fault effects that the injected restriction causes on the target rack."""
    if v.restriction_max <= 0:
        return []
    return [{"rack": TARGET, "signal": s} for s in ("flow_lpm", "valve_pct", "return_c", "gpu_c")] + \
           ([{"rack": TARGET, "signal": "throttle"}] if v.restriction_max >= 0.2 else [])


def evidence_recall(v: Variant, cur: dict) -> dict:
    truth = ground_truth(v)
    kept = {(x["rack"], x["signal"]) for x in cur["ledger"] if x["type"] == "episode"}
    found = [t for t in truth if (t["rack"], t["signal"]) in kept]
    unrelated = [x for x in cur["ledger"] if x["type"] == "episode" and x["rack"] != TARGET]
    return {"fault_effects": len(truth), "retained": len(found),
            "recall": r3(len(found) / len(truth)) if truth else None,
            "missed": [f"{t['rack']} {SIGNAL_NAMES[t['signal']]}" for t in truth if t not in found],
            "unrelated_episodes": len(unrelated)}


# ---------------------------------------------------------------------------
# 3. Small models, trained on separately generated synthetic episodes
# ---------------------------------------------------------------------------

def _softmax(z):
    m = max(z)
    e = [math.exp(x - m) for x in z]
    s = sum(e)
    return [x / s for x in e]


def train_softmax(X, y, n_classes, epochs=600, lr=0.3, l2=1e-3):
    """Multinomial logistic regression by full-batch gradient descent (pure Python)."""
    d = len(X[0])
    mu = [sum(r[j] for r in X) / len(X) for j in range(d)]
    sd = [max(math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / len(X)), 1e-9) for j in range(d)]
    Xs = [[(r[j] - mu[j]) / sd[j] for j in range(d)] for r in X]
    W = [[0.0] * d for _ in range(n_classes)]
    b = [0.0] * n_classes
    for _ in range(epochs):
        gW = [[0.0] * d for _ in range(n_classes)]
        gb = [0.0] * n_classes
        for xi, yi in zip(Xs, y):
            p = _softmax([sum(W[c][j] * xi[j] for j in range(d)) + b[c] for c in range(n_classes)])
            for c in range(n_classes):
                g = p[c] - (1.0 if c == yi else 0.0)
                gb[c] += g
                for j in range(d):
                    gW[c][j] += g * xi[j]
        n = len(Xs)
        for c in range(n_classes):
            b[c] -= lr * gb[c] / n
            for j in range(d):
                W[c][j] -= lr * (gW[c][j] / n + l2 * W[c][j])
    return {"mean": [round(x, 6) for x in mu], "scale": [round(x, 6) for x in sd],
            "weights": [[round(x, 6) for x in row] for row in W], "bias": [round(x, 6) for x in b]}


def predict(model, x):
    xs = [(x[j] - model["mean"][j]) / model["scale"][j] for j in range(len(x))]
    return _softmax([sum(w * v for w, v in zip(model["weights"][c], xs)) + model["bias"][c]
                     for c in range(len(model["bias"]))])


def evaluate(model, X, y, n_classes):
    probs = [predict(model, x) for x in X]
    correct = sum(max(range(n_classes), key=lambda c: p[c]) == t for p, t in zip(probs, y))
    brier = sum(sum((p[c] - (1.0 if c == t else 0.0)) ** 2 for c in range(n_classes)) for p, t in zip(probs, y)) / len(y)
    bins = [[] for _ in range(10)]
    for p, t in zip(probs, y):
        conf = max(p)
        bins[min(9, int(conf * 10))].append((conf, max(range(n_classes), key=lambda c: p[c]) == t))
    ece = sum(len(bn) / len(y) * abs(sum(c for c, _ in bn) / len(bn) - sum(ok for _, ok in bn) / len(bn)) for bn in bins if bn)
    return {"n": len(y), "accuracy": r3(correct / len(y)), "brier": r3(brier), "ece": r3(ece)}


# Feature extractors shared by training episodes and the live scenario.
ACTIONABLE_FEATURES = ("flow_drop_pct", "duration_min", "gpu_rise_c", "throttle_30min")
COMPACT_FEATURES = ("flow_drop_pct", "return_rise_c")
SPECIALIZED_FEATURES = ("flow_drop_pct", "return_rise_c", "valve_rise_pct", "dp_change_kpa",
                        "pump_change_pct", "flow_cv", "neighbour_flow_drop_pct", "temp_flow_consistency")


def synth_episode(rng: random.Random, cls: str, actionable: bool = True) -> dict:
    """One synthetic labelled episode summarised as features (training data)."""
    sev = rng.uniform(0.08, 0.45)
    f = {"flow_drop_pct": 0.0, "return_rise_c": 0.0, "valve_rise_pct": 0.0, "dp_change_kpa": 0.0,
         "pump_change_pct": 0.0, "flow_cv": rng.uniform(0.008, 0.02), "neighbour_flow_drop_pct": rng.gauss(0, 0.8),
         "temp_flow_consistency": 1.0, "duration_min": rng.uniform(60, 300), "gpu_rise_c": 0.0, "throttle_30min": 0.0}
    if cls == "branch_restriction":
        f.update(flow_drop_pct=100 * sev, valve_rise_pct=120 * sev + rng.gauss(0, 3), dp_change_kpa=9 * sev / 0.36 + rng.gauss(0, 1.2),
                 pump_change_pct=rng.gauss(0, 0.8))
    elif cls == "pump_degradation":
        f.update(flow_drop_pct=100 * sev, valve_rise_pct=rng.gauss(4, 3), dp_change_kpa=-30 * sev + rng.gauss(0, 1.5),
                 pump_change_pct=rng.gauss(10 * sev, 1.5), neighbour_flow_drop_pct=100 * sev * rng.uniform(0.7, 1.0))
    elif cls == "sensor_drift":
        f.update(flow_drop_pct=100 * sev, valve_rise_pct=rng.gauss(0, 2), dp_change_kpa=rng.gauss(0, 1.2),
                 pump_change_pct=rng.gauss(0, 0.8), temp_flow_consistency=rng.uniform(0.0, 0.25))
    elif cls == "air_ingress":
        f.update(flow_drop_pct=100 * sev * rng.uniform(0.4, 0.8), valve_rise_pct=rng.gauss(10, 5),
                 dp_change_kpa=rng.gauss(-2, 2), pump_change_pct=rng.gauss(1, 1), flow_cv=rng.uniform(0.06, 0.15))
    physical = cls != "sensor_drift"
    if physical:
        f["return_rise_c"] = 22.8 * (1 / (1 - f["flow_drop_pct"] / 100) - 1) + rng.gauss(0, 0.4)
    else:
        f["return_rise_c"] = rng.gauss(0, 0.4)
    if not actionable:  # short transient that recovers
        f["duration_min"] = rng.uniform(4, 25)
        f["flow_drop_pct"] *= rng.uniform(0.3, 0.8)
        f["return_rise_c"] = max(0.0, f["return_rise_c"] * 0.3)
    f["gpu_rise_c"] = 0.62 * f["return_rise_c"] + rng.gauss(0, 0.4)
    f["throttle_30min"] = max(0.0, (f["gpu_rise_c"] - 7.5) * 30) if physical and actionable else 0.0
    return f


def build_models(seed: int = SEED) -> dict:
    rng = random.Random(f"{seed}:training")
    def dataset(n_per_class, rng):
        rows = []
        for ci, cls in enumerate(CLASSES):
            for _ in range(n_per_class):
                rows.append((synth_episode(rng, cls, True), ci, 1))
                rows.append((synth_episode(rng, cls, False), ci, 0))
        return rows
    train = dataset(150, rng)
    test = dataset(75, random.Random(f"{seed}:test"))

    def xy(rows, feats, target):
        X = [[r[0][f] for f in feats] for r in rows if target != "class" or r[2] == 1]
        y = [(r[1] if target == "class" else r[2]) for r in rows if target != "class" or r[2] == 1]
        return X, y

    out = {}
    Xa, ya = xy(train, ACTIONABLE_FEATURES, "actionable")
    m = train_softmax(Xa, ya, 2)
    out["actionable"] = {"features": ACTIONABLE_FEATURES, "classes": ["transient", "actionable"], **m,
                         "evaluation": evaluate(m, *xy(test, ACTIONABLE_FEATURES, "actionable"), 2)}
    for key, feats in (("compact_fault", COMPACT_FEATURES), ("specialized_fault", SPECIALIZED_FEATURES)):
        Xc, yc = xy(train, feats, "class")
        m = train_softmax(Xc, yc, len(CLASSES))
        out[key] = {"features": feats, "classes": list(CLASSES), **m,
                    "evaluation": evaluate(m, *xy(test, feats, "class"), len(CLASSES))}
    out["_training"] = {"train_episodes": len(train), "test_episodes": len(test),
                        "note": "Synthetic labelled episodes from the generator's own fault models; separate seeds for training and test."}
    return out


def live_features(raw: dict, cur: dict) -> dict:
    """Features of the target rack at decision time, computed from curated evidence only."""
    eps = {(e["rack"], e["signal"]): e for e in cur["ledger"] if e["type"] == "episode"}
    ctx = next((x for x in cur["ledger"] if x["label"].startswith("CDU-A loop state")), None)
    def recent(rack, sig, minutes=30):
        rows = [x[sig] for x in raw["rack"] if x["rack"] == rack and NOW - minutes <= x["t"] < NOW]
        return sum(rows) / len(rows), rows
    flow_now, flows = recent(TARGET, "flow_lpm")
    mean = sum(flows) / len(flows)
    cv = math.sqrt(sum((x - mean) ** 2 for x in flows) / len(flows)) / max(mean, 1e-9)
    flow_base = eps.get((TARGET, "flow_lpm"), {}).get("baseline", NOMINAL_FLOW)
    ret_now, _ = recent(TARGET, "return_c")
    gpu_now, _ = recent(TARGET, "gpu_c")
    thr = sum(x["throttle"] for x in raw["rack"] if x["rack"] == TARGET and NOW - 30 <= x["t"] < NOW)
    valve_now, _ = recent(TARGET, "valve_pct")
    neighbours = [r for r in RACKS_A if r != TARGET]
    nd = []
    for r in neighbours:
        now, _ = recent(r, "flow_lpm")
        base = [x["flow_lpm"] for x in raw["rack"] if x["rack"] == r and BASELINE[0] <= x["t"] < BASELINE[1]]
        nd.append(100 * (1 - now / (sum(base) / len(base))))
    base_rows = [x for x in raw["rack"] if x["rack"] == TARGET and BASELINE[0] <= x["t"] < BASELINE[1]]
    b = lambda k: sum(x[k] for x in base_rows) / len(base_rows)
    flow_ep = eps.get((TARGET, "flow_lpm"))
    feats = {
        "flow_drop_pct": 100 * (1 - flow_now / b("flow_lpm")),
        "duration_min": float(NOW - flow_ep["start"]) if flow_ep else 0.0,
        "gpu_rise_c": gpu_now - b("gpu_c"),
        "throttle_30min": float(thr),
        "return_rise_c": ret_now - b("return_c"),
        "valve_rise_pct": valve_now - b("valve_pct"),
        "dp_change_kpa": (ctx["dp_kpa"] - ctx["dp_base"]) if ctx else 0.0,
        "pump_change_pct": (ctx["pump_pct"] - ctx["pump_base"]) if ctx else 0.0,
        "flow_cv": cv,
        "neighbour_flow_drop_pct": sum(nd) / len(nd),
        "temp_flow_consistency": 1.0 if (ret_now - b("return_c")) > 0.5 * 22.8 * (1 / max(1 - (1 - flow_now / b("flow_lpm")), 0.05) - 1) else 0.0,
    }
    return {k: r3(v) for k, v in feats.items()}


# ---------------------------------------------------------------------------
# 4. Bundle
# ---------------------------------------------------------------------------

def series(raw: dict, rack: str, sig: str, step: int = 10) -> list:
    rows = [x for x in raw["rack"] if x["rack"] == rack]
    return [r3(sum(x[sig] for x in rows[i:i + step]) / len(rows[i:i + step])) for i in range(0, len(rows), step)]


def build_bundle(seed: int = SEED) -> dict:
    models = build_models(seed)
    variants = {}
    for v in VARIANTS:
        raw = build_raw(v, seed)
        cur = curate(raw)
        sweep = []
        for k in (2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 8.0):
            c = curate(raw, k=k)
            sweep.append({"k": k, "ledger_items": len(c["ledger"]), "represented_records": c["represented_records"],
                          **evidence_recall(v, c)})
        bytes_raw = raw_bytes(raw)
        ledger_bytes = len(json.dumps(cur["ledger"], separators=(",", ":"), ensure_ascii=False).encode())
        variants[v.key] = {
            "title": v.title,
            "injected": {"rack": TARGET, "restriction_max_pct": round(100 * v.restriction_max, 1),
                         "onset": hhmm(v.onset), "ramp_min": v.ramp},
            "raw": {"counts": raw_counts(raw), "total": sum(raw_counts(raw).values()), "bytes_json": bytes_raw},
            "curation": {"stages": cur["stages"], "ledger": cur["ledger"], "ledger_bytes_json": ledger_bytes,
                         "represented_records": cur["represented_records"], "k": cur["k"], "min_run": cur["min_run"]},
            "recall": evidence_recall(v, cur),
            "sensitivity_sweep": sweep,
            "features": live_features(raw, cur),
            "series": {"step_min": 10, "racks": {r: {"flow_lpm": series(raw, r, "flow_lpm"), "gpu_c": series(raw, r, "gpu_c")}
                                                 for r in ("R05", "R06", TARGET, "R08")}},
            "supply_c_now": next((x["supply_c"] for x in cur["ledger"] if "supply_c" in x), None),
        }
    return {
        "schema": SCHEMA,
        "seed": seed,
        "evidence_kind": "reproducible_simulation",
        "disclaimer": "Synthetic AI Factory cooling-loop scenario. Reproducible from the seed; not a measurement of any real facility, model or resource use.",
        "decision_time": hhmm(NOW),
        "supply_limit_c": SUPPLY_LIMIT_C,
        "class_labels": CLASS_LABELS,
        "models": models,
        "variants": variants,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--output", type=Path, default=Path("story/data/scenario-v1.json"))
    p.add_argument("--seed", type=int, default=SEED)
    a = p.parse_args()
    bundle = build_bundle(a.seed)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    m = bundle["variants"]["main"]
    print(f"raw records {m['raw']['total']:,} -> ledger {len(m['curation']['ledger'])} items; recall {m['recall']}")
    print(f"subtle recall {bundle['variants']['subtle']['recall']}")
    for k, mod in bundle["models"].items():
        if not k.startswith("_"):
            print(k, mod["evaluation"])


if __name__ == "__main__":
    main()
