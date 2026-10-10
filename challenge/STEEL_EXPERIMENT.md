# Experiment 002 — Steel plate fault classification (UCI)

**A genuine published manufacturing dataset, not the synthetic AI Factory scenario.** This is a **seven-class fault classification** task. It is not a cooling-loop safety or anomaly-detection task.

Source: [UCI Steel Plates Faults](https://archive.ics.uci.edu/dataset/198/steel+plates+faults), DOI [10.24432/C5J88N](https://doi.org/10.24432/C5J88N). Dataset creators: M. Buscema, S. Terzi and W. Tastle (2010). **License: CC BY 4.0**. The source lists 1,941 examples, 27 features and seven fault labels. The exact original label-annotation process is not independently documented here; avoid claiming independent expert adjudication.

## Reproduce

```bash
python -m unittest discover -s challenge -p 'test_*.py' -v
python -m challenge.steel_benchmark --download --output /tmp/slowai-steel-evidence.json
```

The official archive is downloaded on request into `challenge/data/`. Do not commit downloaded data. The JSON report includes source URL, citation, license, source SHA-256, deterministic stratified 80/20 split, train-only feature scaling, predictions, accuracy, macro-F1 and per-class metrics.

## Candidates

- **No-model baseline:** predict the most frequent training class for every test record. This is a valid but intentionally weak lower bound, **not** a meaningful domain-rule expert system.
- **Lightweight ML:** 3-nearest neighbors over the 27 normalized features.
- **Frontier AI:** not tested.

A model outperforming a majority-class baseline does not prove AI is necessary. Next, design domain-informed deterministic rules, more substantial conventional algorithms and an explicitly costed AI option; use independent validation and account for grouping and class imbalance.

## Limitations

The labels come from a published dataset, but the annotation process, independence and potential sample grouping are not verified. The fixed split does not establish generalization to other factories. No energy, carbon or cost is measured. The report includes local timing only, which is not hardware-normalized. No safety decisions should be based on these outputs.
