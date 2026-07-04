# S4 gated ingestion adapters

Status: `S4 draft`

This directory declares ingestion adapter shapes only.

The current runtime does not admit live ingestion.

Allowed in this state:

- synthetic TTN-shaped uplink fixtures;
- synthetic manual observation fixtures;
- synthetic lab-result fixtures;
- adapter discovery and locked intake responses.

Not allowed in this state:

- real TTN credentials;
- real lab endpoints;
- real field uploads;
- production-world automation;
- Holochain commitments created from raw telemetry.

See also:

- `docs/S4_GATED_INGESTION.md`
- `scripts/s4_guard.py`
