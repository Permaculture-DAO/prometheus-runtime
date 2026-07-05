# Prometheus runtime

Development runtime candidate for the Prometheus v1.1 Genesis canon (`PROMETHEUS-CANON-ROOT-v1.1`).

Status: `development runtime; production admission gated`.

This repository candidate is generated from the internal v7.0.3 runtime deployment layer and sanitized according to the internal v7.0.4 Runtime Resynchronization Roadmap S0 requirements. Those `v7.0.x` labels are internal runtime build/process identifiers only; canon authority is the v1.1 Genesis line. See [`docs/CANONICAL_LINEAGE_RECONCILIATION.md`](docs/CANONICAL_LINEAGE_RECONCILIATION.md).

## Not to be confused with `prometheus-happ`

Two public repositories in this org carry runtime scope; they are distinct and complementary:

- **`prometheus-runtime`** (this repo) — the `S0`-`S6` gated data-ingestion pipeline: sensor/device data contracts, gated ingestion, normalization QA, and evidence batch packaging.
- **[`prometheus-happ`](https://github.com/Permaculture-DAO/prometheus-happ)** — the Holochain-native pilot backend (DNA, integrity + coordinator zomes) and the signed `v1.1.3-runtime-proof`.

Both are subordinate to [`prometheus-canon`](https://github.com/Permaculture-DAO/prometheus-canon) and neither redefines canon meaning.

Start with:

- `docs/S0_FREEZE_ROTATE_RECORD.md`
- `docs/RUNTIME_BOUNDARY.md`
- `docs/S2_REMOTE_PUBLICATION_CHECKLIST.md`
- `docs/S3_DATA_CONTRACTS.md`
- `docs/S4_GATED_INGESTION.md`
- `docs/S5_NORMALIZATION_QA.md`
- `docs/S6_EVIDENCE_BATCH_PACKAGING.md`

Do not commit `.env.local`. Copy `.env.example` locally and generate fresh secrets.
