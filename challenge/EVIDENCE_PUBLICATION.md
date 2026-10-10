# Steel Evidence Explorer: snapshot publication

The explorer at `challenge/steel.html` tries to load `challenge/evidence/steel-v1.json` automatically on HTTP(S), then falls back to the manual JSON importer if it is not published.

## Generate a reviewed snapshot

1. After merging this PR, run the GitHub Actions workflow **Generate verified steel evidence snapshot** with `workflow_dispatch`.
2. Download the `verified-steel-v1-snapshot` artifact from that run and extract `steel-v1.json`.
3. Check that the source SHA-256, UCI citation, counts, label distribution, and benchmark outputs are correct.
4. Open a **separate reviewed PR** adding that file to `challenge/evidence/steel-v1.json`. Keep the report byte-for-byte except for the filename.
5. Merge only after checking the generated evidence and passing browser tests.

This intentionally **does not** commit automatically to `main` or fabricate benchmark values. Until the reviewed snapshot is committed, the explorer keeps its existing manual-import flow.

The snapshot is an evidence artifact, **not** an independent validation of the dataset's label quality or a claim that ML is necessary. The comparison still uses a deliberately weak majority-class baseline. Do not publish energy/carbon/cost savings without measurement.
