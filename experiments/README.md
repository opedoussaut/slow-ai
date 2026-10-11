# Demonstrator 01 — Minimum sufficient AI: baseline experiment

This is the first **executable, non-AI-first** experiment. It is intentionally separate from the existing industrial benchmark application so its assumptions and limitations remain explicit.

## Run

From the repository root, with Python 3.10+:

```bash
python -m experiments.minimum_ai
python -m experiments.minimum_ai --output baseline-report.json
python -m pytest tests/test_minimum_ai.py
```

The script uses only the Python standard library. Tests use pytest, already listed in the root requirements.

## Design

- **Task:** classify twelve hand-authored synthetic equipment states as `normal`, `inspect` or `stop`.
- **Baselines:** explicit threshold rules and an additive risk score. Both are non-AI.
- **Reference labels:** illustrative, hand-authored labels, **not** independently validated ground truth.
- **Reported:** accuracy, error count, confusion matrix and a local one-pass Python function timing.
- **Not measured:** tokens, financial cost, energy consumption, carbon footprint, real-world outcomes, model quality.

Neither the fixtures nor the thresholds are appropriate for actual equipment or safety decisions. The sample is tiny and may favor its authors' assumptions. Timing is not a stable benchmark without warmups, repetitions, fixed hardware and instrumentation.

## Next experiment

1. Establish a held-out, appropriately licensed and representative task dataset with a documented annotation process.
2. Add a lightweight classifier and small model using the **same input and output contract**, with optional dependencies and explicit offline/live modes.
3. Compare quality under a predeclared acceptance threshold; only escalate to a larger model when simpler options fail.
4. Measure repeatable latency and instrument compute, energy and cost rather than inferring them from model size or token counts.
5. Publish negative findings, uncertainty, limitations and human-oversight requirements.

The existing industrial benchmark is not modified by this experiment.
