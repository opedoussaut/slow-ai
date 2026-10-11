#!/usr/bin/env python3
"""SlowAI campus scenario: one simulated hour in a 100 MW-class AI factory.

SYNTHETIC and reproducible from its seed. Scale follows public AI factory
reference designs (100 MW campuses; liquid-cooled racks around 130-150 kW),
but every value below is simulated, not measured.

What happens between 16:00 and 17:00:
- a heat wave raises outdoor air from about 33 to 38 degrees C;
- the strainer on coolant distribution unit CDU-07 fouls, so its 24 racks slowly lose flow;
- at 16:38 a coupling under rack R14 (on CDU-07) starts to weep onto its drip tray;
- at 16:45 the grid operator asks the campus to shed 20 MW for two hours.

Every question is routed to the least intelligence that answers it, and the
generator counts how many times each route was used. Run:

    python -m story.generator.campus --output story/data/campus-v1.json
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

from story.generator.scenario import evaluate, predict, train_softmax

SCHEMA = "slowai-campus-scenario/1"
SEED = 20261011
HALLS, CDUS_PER_HALL, RACKS_PER_CDU = 4, 6, 24
CDUS = [f"CDU-{i + 1:02d}" for i in range(HALLS * CDUS_PER_HALL)]
RACK_KW = 140.0                    # within the 130-150 kW range of public reference designs
SECONDS = 3600                     # 16:00:00 to 16:59:59
FAULT_CDU, LEAK_RACK = "CDU-07", "R14"
LEAK_START = 38 * 60               # 16:38
GRID_REQUEST = 45 * 60             # 16:45
DECISION_AT = 40 * 60              # 16:40, when the four questions are asked
SUPPLY_LIMIT_C = 32.0              # illustrative approved limit
FLOW_ALARM_PCT = 85.0              # illustrative CDU low-flow alarm
THROTTLE_C = 87.0                  # GPU temperature where throttling starts
ROUTE_NAMES = {1: "No AI", 2: "Decision model", 3: "Specialized model", 4: "Frontier model"}


def hhmm(t: int) -> str:
    return f"16:{t // 60:02d}"


def ambient(t: int, rng: random.Random) -> float:
    return 33.0 + 5.0 * t / SECONDS + rng.gauss(0, 0.05)


def cdu_flow_pct(cdu: str, t: int, rng: random.Random) -> float:
    fouling = 18.0 * (t / SECONDS) ** 1.6 if cdu == FAULT_CDU else 0.0
    return 100.0 - fouling + rng.gauss(0, 0.4)


def gpu_temp(load: float, flow_pct: float, amb: float, rng: random.Random) -> float:
    # warmer outside air raises the supply temperature; less flow raises the cold-plate temperature
    return 66.0 + 12.0 * load + 0.55 * (amb - 33.0) + 0.70 * max(0.0, 100.0 - flow_pct) + rng.gauss(0, 0.5)


# ---------------------------------------------------------------------------
# Decision model training data: separate seeded rack trajectories,
# labelled by whether throttling actually occurs within the next 15 minutes.
# ---------------------------------------------------------------------------
THROTTLE_FEATURES = ("gpu_c", "gpu_slope_c_per_10min", "flow_pct", "ambient_c")
SPECIAL_FEATURES = THROTTLE_FEATURES + ("load", "flow_slope_pct_per_10min", "supply_c")


def trajectory(rng: random.Random) -> list[dict]:
    """One rack's minute-by-minute path over 75 minutes with a random cooling degradation."""
    load = rng.uniform(0.80, 1.0)
    drop = rng.choice([0.0, 0.0, rng.uniform(3, 30)])   # one third of racks degrade
    a0 = rng.uniform(28, 36)
    rows = []
    for m in range(75):
        amb = a0 + 5.0 * m / 60
        flow = 100.0 - drop * (m / 75) ** 1.6 + rng.gauss(0, 0.4)
        rows.append({"m": m, "amb": amb, "flow": flow, "load": load, "gpu": gpu_temp(load, flow, amb, rng),
                     "supply": 24.0 + 0.15 * (amb - 30) + rng.gauss(0, 0.1)})
    return rows


def features_at(rows: list[dict], i: int) -> dict:
    r, p = rows[i], rows[max(0, i - 10)]
    return {"gpu_c": r["gpu"], "gpu_slope_c_per_10min": r["gpu"] - p["gpu"], "flow_pct": r["flow"],
            "ambient_c": r["amb"], "load": r["load"], "flow_slope_pct_per_10min": r["flow"] - p["flow"],
            "supply_c": r["supply"]}


def model_dataset(seed: int, n: int):
    rng = random.Random(seed)
    X, y = [], []
    for _ in range(n):
        rows = trajectory(rng)
        for i in range(10, 60, 5):
            future = any(rows[j]["gpu"] >= THROTTLE_C for j in range(i + 1, min(i + 16, len(rows))))
            if rows[i]["gpu"] >= THROTTLE_C:
                continue                       # already throttling: Route 1 handles it
            X.append(features_at(rows, i))
            y.append(int(future))
    return X, y


def train_models(seed: int) -> dict:
    Xtr, ytr = model_dataset(seed + 1, 500)
    Xte, yte = model_dataset(seed + 2, 250)
    out = {}
    for key, feats in (("throttle_compact", ("gpu_c", "flow_pct")), ("throttle_specialized", SPECIAL_FEATURES)):
        m = train_softmax([[x[f] for f in feats] for x in Xtr], ytr, 2, epochs=500)
        out[key] = {"features": list(feats), "classes": ["no_throttle", "throttle_within_15_min"], **m,
                    "evaluation": evaluate(m, [[x[f] for f in feats] for x in Xte], yte, 2)}
    out["_training"] = {"train_samples": len(ytr), "test_samples": len(yte),
                        "positives_test": sum(yte),
                        "note": "Labels come from the simulation: did the rack actually reach the throttle temperature within 15 minutes."}
    return out


# ---------------------------------------------------------------------------
# The simulated hour
# ---------------------------------------------------------------------------
def simulate(seed: int, models: dict) -> dict:
    rng = random.Random(seed)
    racks = [(cdu, f"R{r + 1:02d}", rng.uniform(0.80, 1.0)) for cdu in CDUS for r in range(RACKS_PER_CDU)]
    counts = {1: 0, 2: 0, 3: 0, 4: 0}
    route1_alarms = {"supply_over_limit": 0, "cdu_low_flow_seconds": 0, "gpu_throttle_rack_seconds": 0}
    raw_samples = 0
    minute_state = {}   # (cdu, rack) -> list of per-minute dicts
    leak_triggers, camera_triggers = [], []
    cdu_log = {c: [] for c in CDUS}
    for t in range(SECONDS):
        amb = ambient(t, rng)
        flows = {c: cdu_flow_pct(c, t, rng) for c in CDUS}
        supplies = {c: 24.0 + 0.15 * (amb - 30) + rng.gauss(0, 0.1) for c in CDUS}
        # Route 1: four limit checks per CDU per second (supply, flow, pressure, pump state)
        for c in CDUS:
            counts[1] += 4
            raw_samples += 4
            if supplies[c] > SUPPLY_LIMIT_C:
                route1_alarms["supply_over_limit"] += 1
            if flows[c] < FLOW_ALARM_PCT:
                route1_alarms["cdu_low_flow_seconds"] += 1
            if t % 60 == 0:
                cdu_log[c].append({"t": t, "flow": round(flows[c], 2), "supply": round(supplies[c], 2)})
        # Route 1: two checks per rack per second (GPU temperature limit, leak rope sensor)
        record_minute = t % 60 == 59
        for cdu, rack, load in racks:
            counts[1] += 2
            raw_samples += 2
            g = gpu_temp(load, flows[cdu], amb, rng)
            if g >= THROTTLE_C:
                route1_alarms["gpu_throttle_rack_seconds"] += 1
            if record_minute:
                minute_state.setdefault((cdu, rack), []).append(
                    {"m": t // 60, "amb": amb, "flow": flows[cdu], "load": load, "gpu": g, "supply": supplies[cdu]})
        # Drip-tray cameras: one frame per rack per second; Route 1 is a pixel-difference trigger.
        counts[1] += len(racks)
        raw_samples += len(racks)
        if rng.random() < 0.0028:                                   # people walking, reflections, door light
            camera_triggers.append({"t": t, "rack": rng.choice(racks)[1], "cdu": rng.choice(CDUS), "true_leak": False})
        if t == LEAK_START + 95:                                    # the weeping coupling becomes visible
            camera_triggers.append({"t": t, "rack": LEAK_RACK, "cdu": FAULT_CDU, "true_leak": True})

    # Curation + Route 2: a rack-minute reaches the decision model only when its GPU temperature
    # rose more than 1.5 C over the last 10 minutes (deterministic change detection).
    compact, special = models["throttle_compact"], models["throttle_specialized"]
    r2_calls, r3_calls, escalations = [], [], []
    for (cdu, rack), rows in minute_state.items():
        for i in range(10, len(rows)):
            f = features_at(rows, i)
            if rows[i]["gpu"] >= THROTTLE_C or f["gpu_slope_c_per_10min"] <= 1.5:
                continue
            counts[2] += 1
            p = predict(compact, [f[k] for k in compact["features"]])[1]
            r2_calls.append({"rack": f"{cdu}/{rack}", "minute": rows[i]["m"], "p": round(p, 3)})
            if 0.2 < p < 0.8:                                       # contract: confident below 0.2 or above 0.8
                counts[3] += 1
                ps = predict(special, [f[k] for k in special["features"]])[1]
                truth = any(r["gpu"] >= THROTTLE_C for r in rows[i + 1:i + 16])
                escalations.append({"rack": f"{cdu}/{rack}", "minute": rows[i]["m"], "p_compact": round(p, 3),
                                    "p_specialized": round(ps, 3), "throttled_within_15_min": truth})
    esc_summary = {
        "count": len(escalations),
        "compact_correct": sum((e["p_compact"] >= 0.5) == e["throttled_within_15_min"] for e in escalations),
        "specialized_correct": sum((e["p_specialized"] >= 0.5) == e["throttled_within_15_min"] for e in escalations),
        "answer_changed": sum((e["p_compact"] >= 0.5) != (e["p_specialized"] >= 0.5) for e in escalations),
    }
    # Route 3: every camera trigger goes to the drip-tray vision model (simulated output).
    for trig in camera_triggers:
        counts[3] += 1
        r3_calls.append({"t": hhmm(trig["t"]), "rack": f"{trig['cdu']}/{trig['rack']}",
                         "leak_probability": 0.94 if trig["true_leak"] else round(0.02 + 0.1 * random.Random(trig["t"]).random(), 2)})
    # Route 4: one call, for the grid request that needs cross-domain judgement (not run).
    counts[4] += 1

    # The four questions at 16:40 about rack R14 on CDU-07
    r14 = minute_state[(FAULT_CDU, LEAK_RACK)]
    f14 = features_at(r14, DECISION_AT // 60)
    p14c = predict(compact, [f14[k] for k in compact["features"]])[1]
    p14s = predict(special, [f14[k] for k in special["features"]])[1]
    throttled_after = next((row["m"] for row in r14 if row["m"] > DECISION_AT // 60 and row["gpu"] >= THROTTLE_C), None)
    cdu07 = cdu_log[FAULT_CDU]
    q = {
        "supply_limit": {"route": 1, "cdu": FAULT_CDU, "supply_c": round(cdu07[DECISION_AT // 60]["supply"], 1),
                         "limit_c": SUPPLY_LIMIT_C, "flow_pct": round(cdu07[DECISION_AT // 60]["flow"], 1)},
        "throttle_risk": {"route": 2, "rack": f"{FAULT_CDU}/{LEAK_RACK}", "p_compact": round(p14c, 3),
                          "escalated": 0.2 < p14c < 0.8, "p_specialized": round(p14s, 3),
                          "features": {k: round(v, 2) for k, v in f14.items()},
                          "actually_throttled_at": hhmm(throttled_after * 60) if throttled_after is not None else None},
        "leak": {"route": 3, "rack": f"{FAULT_CDU}/{LEAK_RACK}", "leak_probability": 0.94, "model_output": "simulated",
                 "camera_triggers_in_hour": len(camera_triggers)},
        "grid": {"route": 4, "request_mw": 20, "duration_h": 2, "at": hhmm(GRID_REQUEST), "status": "not run"},
    }
    it_mw = len(racks) * RACK_KW / 1000
    return {
        "campus": {"halls": HALLS, "cdus": len(CDUS), "racks": len(racks), "rack_kw": RACK_KW,
                   "it_load_mw": round(it_mw, 1), "window": "16:00-17:00"},
        "raw_samples": raw_samples,
        "route_counts": {str(k): v for k, v in counts.items()},
        "route_names": {str(k): v for k, v in ROUTE_NAMES.items()},
        "route1_alarms": route1_alarms,
        "route2_sample": sorted(r2_calls, key=lambda r: -r["p"])[:5],
        "escalations_sample": escalations[:5],
        "escalation_summary": esc_summary,
        "camera_calls": r3_calls,
        "questions": q,
        "cdu07_flow_by_minute": [round(r["flow"], 2) for r in cdu07],
        "r14_gpu_by_minute": [round(r["gpu"], 2) for r in r14],
    }


def build(seed: int = SEED) -> dict:
    models = train_models(seed)
    sim = simulate(seed, models)
    return {"schema": SCHEMA, "seed": seed, "evidence_kind": "reproducible_simulation",
            "disclaimer": "Synthetic 100 MW-class AI factory hour. Scale follows public reference designs; every value is simulated, not measured. The drip-tray vision model output is simulated, not a trained model.",
            "models": {k: v for k, v in models.items()}, **sim}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--output", type=Path, default=Path("story/data/campus-v1.json"))
    a = p.parse_args()
    b = build()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(b, indent=1) + "\n", encoding="utf-8")
    print("campus", b["campus"], "raw samples", f"{b['raw_samples']:,}")
    print("route counts", b["route_counts"])
    print("alarms", b["route1_alarms"])
    print("questions", json.dumps(b["questions"], indent=1))
    for k in ("throttle_compact", "throttle_specialized"):
        print(k, b["models"][k]["evaluation"])
    print("training", b["models"]["_training"])


if __name__ == "__main__":
    main()
