# S5 — Normalization and QA draft

Status: `DRAFT`

S5 maps S4 synthetic adapter fixtures into the S3 event contract.

This step does not enable live ingestion, storage admission, Holochain commits, MRV claims, or production use.

## What S5 adds

- deterministic fixture normalization;
- canonical event identity generation;
- synthetic QA labels;
- normalized synthetic artifacts under `adapters/normalized/`;
- CI guard for stale or non-contractual normalized events.

## Boundary

Allowed:

- synthetic fixture normalization;
- schema validation;
- event identity replay checks;
- QA state set to `synthetic`.

Not allowed:

- real TTN uplinks;
- real manual field uploads;
- real lab results;
- live endpoints;
- Holochain commitments;
- MRV authority.

The truthful status remains:

```text
development runtime; production admission gated
```
