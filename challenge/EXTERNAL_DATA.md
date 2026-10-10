# External-data benchmark protocol (v1)

This is the next step beyond the synthetic, browser-only Intelligence Challenge. **No real dataset is bundled or downloaded.** You supply a licensed, independently labeled CSV and a fixed train/test split.

## Input

Required CSV columns: `id,split,label,temperature_c,vibration_mm_s,alarm`.

- `id`: unique record ID
- `split`: `train` or `test`, assigned before running the benchmark
- `label`: `normal`, `inspect`, or `stop`, established independently of the evaluated rules
- `temperature_c` and `vibration_mm_s`: finite numeric values
- `alarm`: `0`, `1`, `false` or `true`

The variables and thresholds remain illustrative; they are not a claim of industrial applicability.

## Run

```bash
python -m unittest discover -s challenge -p 'test_*.py' -v
python -m challenge.external_benchmark --csv /path/to/licensed_cases.csv --output /tmp/slowai-evidence.json --k 3
```

Outputs include a SHA-256 of the input bytes, counts, predictions, accuracy, per-class precision/recall and explicit nulls for unmeasured energy/carbon/cost/latency.

## Before using results publicly

Document provenance and license, label authorship, label uncertainty, sampling frame, leakage risks (same machine/incident across splits), class balance, and predefined acceptance thresholds. Keep a validation split for selecting hyperparameters. Report confidence intervals and error costs before drawing conclusions. Do not put private industrial data or identifiable records into a public repository. Never describe a dataset as independently labeled unless that is verified.

**This implementation only makes a real-data comparison possible; it does not supply one.** There is still no frontier-AI evaluation or environmental measurement.
