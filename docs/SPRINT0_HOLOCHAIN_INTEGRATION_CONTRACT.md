# Sprint 0 Holochain integration contract

Status: candidate integration boundary.

Target flow:

`sensor/lab/operator → ingestion → schema validation → normalization/QA → evidence batch → transactional outbox → Holochain bridge → zome call → receipt → UI`

## Required controls

- at-least-once delivery with idempotent consumption;
- immutable outbox event ID;
- schema and canon version;
- payload SHA-256;
- retry and dead-letter state;
- recorded zome function and action hash;
- no silent success;
- mock/synthetic/real separation;
- fail closed on schema or canonical mismatch;
- no automatic claim, PRU, RAP, TRBK or financial-right creation.

This contract is not evidence that the integration is already implemented.
