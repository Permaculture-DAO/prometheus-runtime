# M9.2 — Release Gate Decision (noncanonical)

**Decision: GO for LAB candidate / HOLD for release.**

| Gate | Evidence | Result |
|---|---|---|
| M92 local security/regression | 23 new + 28 M9.1/M9 legacy | PASS 51/51 |
| M6 snapshot regression | 96 pass, 2 skip requiring native checkout | PASS 96 / SKIP 2; do not count SKIP as PASS |
| POSIX shared SQLite anti-replay | Lock, single transaction, unique case digest, restart, separate processes | PASS local-only |
| Ledger tampering | HMAC chain; separate local anchor; replay/audit row bijection; injected mid-commit failure | PASS lab |
| Ledger backup | SQLite backup API + local anchor; restored replay remains consumed | PASS lab; not production DR |
| HTTPS/mTLS | Ephemeral CA, two Uvicorn servers on loopback, no client cert denied | PASS local-only |
| Two worker processes | 1 positive advisory, 19 replay HOLD, second identity denied post-restart | PASS local-only |
| Source provenance | Four M6 Git blobs match PR #37 | PASS exact files |
| Github PR #37 | Draft open, two workflows successful, unsigned SHA, zero independent reviews | HOLD for merge |
| Production IAM/KMS, cert binding | No enterprise key issuer, rotation, non-test revocations | HOLD |
| Cross-host replay | SQLite local files only; cannot assume shared NFS consistency | HOLD |
| Independent WORM audit / escrow | Local JSONL and anchor controlled by same host | HOLD |
| Real clock, policy revocation feed | Frozen synthetic fixture timestamp | HOLD |
| VPS stage | No identified separately authorized VPS tested | HOLD |
| Holochain / canonical rights / production | No writes allowed; no deployments | HOLD |

## Release assurance rules

1. Keep **v1.1.2 signed Genesis**, Ω orchestration v1.2, and Beyond-TRL Ω distinct. This package cannot amend Canon.
2. Do not merge an unsigned and unreviewed PR or bypass branch protections. Sign via the legitimate maintainer or approve a documented policy exception independently.
3. Do not represent lab TLS as externally trusted PKI/mTLS or local HMAC as an external auditor.
4. Do not promote an advisory score to rights, capital, certifications or runtime native `admissible`.
5. No user authorization to touch VPS/Holochain/production is inferred from “next milestone”.
