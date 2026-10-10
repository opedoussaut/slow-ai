<p align="center"><img src="assets/slowai-wordmark.svg" alt="ƧlowAI — Think first. AI when it matters." width="700"></p>

<p align="center"><strong>Open by nature. Lean by design.</strong></p>

# SlowAI

**SlowAI (ƧlowAI)** is an independent, community-driven open-source initiative for deciding **whether AI is necessary, when it creates real value, and how to use the minimum sufficient AI responsibly**.

AI is a tool, not the default answer. We start with the problem, compare non-AI approaches, then assess AI options against quality, cost, energy, environmental impact, privacy, safety and social consequences. We publish assumptions and uncertainty rather than claiming savings without evidence.

### Three guiding questions

1. **Do we need AI?** Test deterministic software, simple statistics and human processes first.
2. **If so, how much AI is enough?** Choose the smallest solution that meets explicit requirements.
3. **What is the full impact?** Measure real outcomes and resource use; consider lifecycle and societal effects.

**This is a personal, independent open-source initiative, not an employer-sponsored program.** Everyone is welcome to inspect, question and contribute.

Read the [Manifesto](MANIFESTO.md), [Roadmap](ROADMAP.md), [Contribution guide](CONTRIBUTING.md), and [Apache 2.0 License](LICENSE).

> **Evidence matters:** The industrial scenarios below are synthetic, and simulated adapters are not measurements of real provider performance. The current benchmark is a starting point, not a validated claim of environmental savings.

---

## Demonstrator 01 — Industrial AI benchmark

The repository's first demonstrator is a side-by-side industrial AI benchmark proof of concept built around one simple hypothesis:

> **Agents should spend tokens on reasoning, not on deterministic data reduction.**

The same synthetic industrial case is evaluated through four architectures:

1. **Agent-only baseline** — agents query a broad raw source universe and the K&KH corpus directly.
2. **Lean / NiFi-assisted** — deterministic preprocessing filters, correlates, normalizes and contextualizes the same evidence before agents reason.
3. **Lean + Jev** — the Lean state is evaluated as typed probabilistic decisions; a frontier reasoner is called only when confidence/ambiguity crosses the escalation policy.
4. **Lean + open zero-shot** — the same typed-decision contract is implemented with an open zero-shot classifier as a control experiment.

## Benchmark scenarios

### Aerospace · Non-conformance investigation

Synthetic dimensional NCR on a structural component. Evidence includes machine telemetry, inspection results, work orders, engineering definition, supplier information, historical NCRs and a small K&KH corpus.

Specialist agents: Quality, Manufacturing, Design and Supervisor.

Human gate: final quality/engineering disposition remains mandatory.

### High-Tech · AI Factory infrastructure anomaly

Synthetic GPU-rack incident during a high-load distributed AI workload. Evidence includes GPU/rack telemetry, liquid cooling/CDU, network fabric, DCIM, workload impact, infrastructure configuration, historical incidents and K&KH content.

Specialist agents: Thermal, Infrastructure, Network, Knowledge and Supervisor.

Human gate: Infrastructure Operations approval remains mandatory before intervention.

## What works now

- Apple-inspired dual-domain investigation UI
- Aerospace / High-Tech scenario selector
- Four-way architecture comparison
- Deterministic NiFi emulation with provenance
- K&KH corpus retrieval
- Optional live OpenAI Responses API calls when `OPENAI_API_KEY` is set
- Optional live TypeSafe Jev calls when `TYPESAFE_API_KEY` is set
- Optional local Hugging Face zero-shot classifier
- Explicit confidence-based frontier escalation
- Benchmark metrics for tokens, context, calls, latency, cost and evidence precision
- Decision traces for Jev and the open classifier
- Calibration workspace with Accuracy, ECE, Brier score, NLL and reliability buckets
- Automated tests for both industrial scenarios
- Docker Compose scaffold with Apache NiFi
- Vercel FastAPI entrypoint

## Architecture

```text
                    OPERATIONAL DATA + K&KH
                              |
                              v
                    NiFi / Lean preprocessing
                              |
                         compact state
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
   Lean + agents          Lean + Jev        Lean + open
   frontier reasoning     typed decisions    typed decisions
          |                   |                   |
          |             confidence gate      confidence gate
          |                /       \             /       \
          |          structured   frontier  structured   frontier
          |             path      reasoner     path      reasoner
          |                \       /             \       /
          +-----------------+-----+---------------+------+
                                  |
                              human gate

Parallel baseline:
raw enterprise data -> agent/tool retrieval -> specialist agents -> supervisor -> human gate
```

**Corpus = what the organization knows.**  
**Deterministic layer = what is relevant now.**  
**Decision models = what can be classified/scored quickly.**  
**Frontier models = what still requires deeper reasoning.**  
**Humans/workflow = what is authorized to happen.**

## Run locally

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088
```

Open `http://localhost:8088`.

Without API keys the application explicitly runs in **simulation mode**.

## Jev

Set:

```bash
TYPESAFE_API_KEY=...
TYPESAFE_MODEL=jev-latest
JEV_CONFIDENCE_THRESHOLD=0.80
JEV_ESCALATION_PROBABILITY=0.50
```

The app sends one shared Lean state with parallel `choice`, `score` and `noul` questions. If confidence is too low or ambiguity is too high, it escalates once to the existing frontier reasoner.

Simulation values must not be presented as measured TypeSafe performance. Review the applicable TypeSafe agreement before publishing live provider benchmark/performance results.

## Open zero-shot control

The default deployment keeps this lane lightweight and simulated. To run a real local Hugging Face control:

```bash
pip install -r requirements-zero-shot.txt
export ZERO_SHOT_MODE=local
export ZERO_SHOT_MODEL=facebook/bart-large-mnli
```

This deliberately implements the same decision surface as Jev so the benchmark tests the architectural hypothesis rather than simply comparing Jev with a much larger generative model.

## Calibration lab

The Calibration tab uses a small labeled industrial smoke-test corpus and reports:

- classification accuracy
- Expected Calibration Error (ECE)
- multiclass Brier score
- negative log loss (NLL)
- confidence-vs-accuracy reliability buckets

The built-in corpus is only a smoke test. For deployment decisions, replace it with **300+ representative labeled examples from the target process**.

When a provider is simulated, the UI marks the calibration results **SIMULATED ADAPTER — NOT MODEL BENCHMARK EVIDENCE**.

## Docker / Apache NiFi

```bash
docker compose up --build
```

App: `http://localhost:8088`  
NiFi: `https://localhost:8443/nifi`

The current application uses a Python implementation of the deterministic NiFi contract so the experiment is runnable immediately. A future step is to replace that adapter with real NiFi Process Groups while preserving the same input/output contract and instrumentation.
