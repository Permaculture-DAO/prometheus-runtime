# S6 — Evidence batch packaging draft

Status: `DRAFT`

S6 packages S5 normalized synthetic events into a deterministic evidence-reference batch.

This stage does not create real evidence, custody authority, Holochain commits, certification, or MRV authority.

## What S6 adds

- `contracts/evidence.batch.schema.json`
- `evidence/batches/synthetic_batch_0001.json`
- deterministic `batch_hash`
- simulated Holochain reference hash
- S6 guard wired into CI
- read-only API exposure for the current synthetic batch package

## Boundary

Allowed:

- synthetic event references;
- batch hash replay;
- simulated Holochain reference hash;
- non-authoritative evidence packaging.

Not allowed:

- raw telemetry in the batch package;
- real field evidence;
- real custody claims;
- Holochain entry commits;
- certification or MRV authority.

The truthful status remains:

```text
development runtime; production admission gated
```
