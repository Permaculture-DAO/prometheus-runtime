# Data contracts

Status: `S3 draft`

These contracts define the minimum structure for non-authoritative runtime data entering the Prometheus development runtime.

They are intentionally conservative:

- synthetic fixtures are allowed;
- real field ingestion is not admitted by this repository state;
- Holochain must not be used as the high-frequency telemetry database;
- every event must carry provenance, decoder identity, method version, and reproducibility metadata.

See also:

- `docs/RUNTIME_BOUNDARY.md`
- `docs/S3_DATA_CONTRACTS.md`

