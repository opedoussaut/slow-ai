# ƧlowAI Interactive Decision Lab

Open [index.html](index.html) locally in a modern browser. No installation, API key, backend or internet connection is required.

The interactive demonstration makes the project's **non-AI-first** philosophy tangible:
- Change three synthetic equipment signals and compare two transparent, deterministic decision strategies.
- View each strategy's accuracy against the same 12 hand-authored examples.
- Download a JSON report containing every case, predicted label and explicit missing measurements.

## Reproducibility and honesty

This is a **teaching demonstration**, not a validated industrial or environmental benchmark. Its small, synthetic, hand-authored labels are not independent ground truth. Neither strategy was trained or evaluated on an independent real-world dataset. No AI model is evaluated. No energy, CO₂e, cost or latency data is measured or estimated. No equipment-safety decision should rely on these rules.

The logic mirrors the separate baseline experiment proposed in PR #6, but the HTML is self-contained and does not depend on that PR being merged.

## How to publish a public interactive URL

After reviewing and merging, a maintainer may enable GitHub Pages for the repository or deploy the static `demo/` directory on an approved static host. **This PR does not enable or deploy anything.** A GitHub file URL shows source code, not the running demo. Before announcing a public interactive URL, verify the deployment and its behavior in a browser.

## Next

Use a larger, licensed, independently labeled dataset; declare acceptance criteria before evaluating; add lightweight ML as a separate candidate; instrument repeated latency and energy measurements and carbon intensity assumptions. Publish negative findings and uncertainty.
