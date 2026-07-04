# Prometheus runtime

Development runtime candidate for `PROMETHEUS-CANON-ROOT-v7.0`.

Status: `development runtime; production admission gated`.

This repository candidate is generated from the v7.0.3 runtime deployment layer and sanitized according to the v7.0.4 Runtime Resynchronization Roadmap S0 requirements.

Start with:

- `docs/S0_FREEZE_ROTATE_RECORD.md`
- `docs/RUNTIME_BOUNDARY.md`
- `docs/S2_REMOTE_PUBLICATION_CHECKLIST.md`
- `docs/S3_DATA_CONTRACTS.md`
- `docs/S4_GATED_INGESTION.md`
- `docs/S5_NORMALIZATION_QA.md`
- `docs/S6_EVIDENCE_BATCH_PACKAGING.md`

Do not commit `.env.local`. Copy `.env.example` locally and generate fresh secrets.
