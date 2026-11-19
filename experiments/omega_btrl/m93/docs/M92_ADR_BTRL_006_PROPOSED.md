# ADR-BTRL-006 — Local Durable Replay Receipts (PROPOSED, NOT RATIFIED)

**Scope:** M9.2 laboratory assurance only. **Status:** PROPOSED, no source-custodian ratification.

## Choice

For a single-host synthetic stage, move from the M9.1 per-process `seen_review_cases` cache to an owner-only SQLite ledger with:

- Canonical case hash key determined by the host, SQLite `PRIMARY KEY` and `BEGIN IMMEDIATE` under POSIX `flock`.
- In the same transaction: insert first accepted replay receipt (if absent), append a row to a restrictive HMAC-chained audit log. A reused case produces an event `REPLAY_BLOCKED`/`HOLD`.
- Separate local audit anchor advanced with atomic rename and fsync. A process crash between DB commit and anchor update must block reopening rather than silently clear history.
- Complete event hash-chain verification **and replay-to-positive-event bijection verification** before processing requests. It is currently O(N), unsuitable for high-volume production.
- Secondary filtered JSONL append-only export. Failure after a committed positive results in HTTP HOLD; the receipt remains consumed.
- Lab host-provisioned per-actor credentials, expiry, revocation, scope checks, temporary mTLS on loopback.

## Rejected alternatives

- In-memory set only: fails after restart or across workers.
- Trust claims supplied by HTTP payload: self-attestation cannot create authority.
- Rebuild an hApp DNA or make Holochain write path: not needed for a read-only sidecar.
- Claim that local SQLite is a distributed consensus ledger, or that HMAC+same-host anchor is WORM: false.

## Consequences

- For outage/reconciliation, a positive may be consumed despite an HTTP 503. This is intentional fail-closed behavior; operators may not reset receipts to make it eligible again.
- A missing or mismatched anchor requires a tracked incident and **manual, independently approved** recovery. Do not delete state to recover eligibility.
- Multi-host service needs a transactionally consistent shared DB and off-host monotonic audit checkpoint; local implementation must not be adopted as-is.
- The prototype creates no real rights, valuations, tokens, claims, certifications or financial permissions.
