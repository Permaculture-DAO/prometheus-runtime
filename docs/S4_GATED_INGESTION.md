# S4 — Gated ingestion adapters

Status: `DRAFT`

S4 introduces adapter boundaries for future ingestion while keeping all live intake closed.

The current runtime state is intentionally conservative:

- adapter metadata may be discovered;
- synthetic fixtures may be validated;
- intake endpoints remain locked;
- no live TTN, manual, lab, irrigation, or production-world feed is admitted.

## Adapter set

- `ttn_mock` — TTN-shaped synthetic uplink fixture.
- `manual_mock` — synthetic manual observation fixture.
- `lab_mock` — synthetic lab-result fixture.

## Runtime rule

The S4 runtime may describe the path:

```text
adapter → contract normalization → QA/QC → evidence batch reference
```

It must not turn that path into live ingestion until later gates explicitly authorize it.

## Holochain boundary

Holochain remains a provenance and batch-reference layer.

Raw telemetry and high-frequency event streams must not be committed to Holochain.

## Admission boundary

The truthful status remains:

```text
development runtime; production admission gated
```

