# M9.2 Security Boundary & Threat Model

## Assets and trust zones

- **Untrusted:** JSON case, HTTP headers, body ordering, client claims, perceived eligibility.
- **Host-only:** client credentials registry, signing roots/receipts, revocation epoch floor, replay key, audit HMAC key, emergency stop path.
- **Local durable:** owner-only SQLite receipts + HMAC-chain events + separate local anchor + secondary JSONL. Shared across local POSIX processes, not across VPS nodes.
- **Excluded:** native FastAPI write endpoints, RAVEL decisions, Holochain app/zome/conductor writes, wallets, financing, rights creation and releases.

## Attack tests and residual risks

| Threat | M9.2 defense tested | Remaining risk |
|---|---|---|
| Duplicate identical case across workers | SQLite unique digest + `BEGIN IMMEDIATE`, POSIX flock, durable ledger | No proof on NFS, multiple machines or network partitions |
| Replay after process restart | Persistent row plus HMAC-chain audit and anchor | Key management/rollover, normal transaction semantics not independently reviewed |
| Delete/insert replay row | Each audit's accepted positive digest must match exactly one replay entry | Privileged attacker with HMAC key + anchor can rewrite both |
| Tamper historical audit | Full HMAC chain scan + separate local anchor check before each write | Coherent rollback/truncation with anchor or key compromise needs remote checkpoint |
| Crash after DB commit before anchor write | Future operations refuse to reopen on mismatch | Manual recover/repair plan and off-host escrow not yet available |
| Audit exporter down | HTTP positive suppressed and receipt remains consumed | Secondary local exporter can reorder/lag across concurrent workers; needs outbox/collector ack |
| Forged trust in HTTP JSON | `safe_json` + host-only TrustedStore, case digest computed locally | Real root custody and revocation feed absent |
| Wrong/expired/revoked client | Host registry scope and expiry, duplicate header rejection | Lab bearer token not channel-bound to client cert; leaked bearer plus any valid client cert may be abused |
| No client TLS certificate | Uvicorn mTLS rejects before HTTP | Synthetic CA and certs, not enterprise PKI nor OCSP |
| Emergency stop | Host-only filesystem path, symlink presence treated as stop | In-flight request race at shutdown and OS-level privilege separation not proven |
| Client slowloris / large volume | 32 KiB body cap, no native writes, local-only | No edge rate limit, queue budgets, circuit breaker or bounded upstream signing-provider latency |
| Misleading positive response | `make_advice` hardens authority flags to false | Human operators may misuse recommendations outside technical boundary |

## Independent assurance required

A separate security reviewer must inspect source at a **published immutable Git SHA**, rerun attack tests, map TLA+ invariants to executable code, and attest identity/COI. AI red-team is not human review. At least one reviewer must be organizationally distinct from code author and source/release approver.

The HMAC key must move to a protected service, export receipts to an external monotonic/WORM auditor, and identities to an organization-controlled issuer before staging admission.
