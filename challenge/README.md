# ƧlowAI — The Intelligence Challenge

An immersive, self-contained, interactive **non-AI-first** investigation at `challenge/index.html`.

## Run locally

Open `challenge/index.html` in a modern browser. No build, server, API key, CDN, model download or network access is needed.

## What is actually implemented

- Four synthetic AI Factory incident scenarios with live telemetry, evidence timeline and explanation.
- **Deterministic rules** using explicit temperature, vibration and fault-alarm thresholds.
- **Real lightweight ML**: a 3-nearest-neighbor (3-NN) classifier, trained on 180 seeded synthetic samples using normalized squared Euclidean distance, with a deterministic class tie-break.
- **Held-out synthetic test set** of 90 independently generated samples, using a different fixed seed. Neither algorithm trains on the test cases.
- Accuracy and error count for both approaches, with a JSON export of the full training and test data, predictions, methodology, seeds and missing measurements.
- A frontier-AI lane clearly marked **NOT TESTED**, rather than fabricated results.
- Energy, carbon, latency and financial cost clearly marked **NOT MEASURED**.

### Methodological limitations

The synthetic reference labels are produced by an explicit additive-risk policy, not independently annotated industrial ground truth. The test set is therefore **not evidence of real-world performance**, and the policy may favor approaches similar to its own logic. Neither an AI provider nor a real industrial system is used. The browser UI is a demonstration of evaluation mechanics and responsible reporting, not proof that any method is safer, more accurate, greener or cheaper in production. Do not use these rules for equipment safety decisions.

## Before public launch

1. Review and merge the PR.
2. Visually and functionally verify in desktop and mobile browsers, including all scenarios and JSON export.
3. Enable/verify static hosting (e.g. GitHub Pages), then test the actual public URL. No hosting changes are made by this PR.
4. For a **scientifically credible model comparison**, replace the synthetic policy labels with a representative independently annotated, appropriately licensed dataset; preregister acceptance criteria; instrument repeated timing, energy and cost; include uncertainty and negative findings.
5. Only announce **measured** savings if measurements support them. The launch can legitimately showcase the interactive methodology and honest experimental baselines now.

## Design principle

The challenge should feel ambitious without implying that illustrative synthetic outputs are validated empirical results. ƧlowAI asks whether more AI is needed; it does not assume that simpler is always better.
