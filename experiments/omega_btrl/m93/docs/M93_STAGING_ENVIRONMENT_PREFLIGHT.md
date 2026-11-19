# M9.3 — Required inventory before any VPS staging activity

This is a **proposed** inventory, not evidence of a configured VPS. No authorization to use `app.heart-intelligence.earth` as a staging endpoint is implied.

1. **Operator boundary:** written approval from VPS custodian, operator identity, hostname, machine identifier, environment designation, staging-only firewall rules, maintenance window, expected costs.
2. **Isolation:** separate VPS/VM/account, private DNS, no secrets or storage shared with production, independent RBAC and egress controls. Document shadow traffic and retention.
3. **Identity:** IAM principal and separate attested client-certificate issuer, key custody/HSM/KMS policy, cryptographic binding between mTLS certificate and IAM actor, expiry and revocation tests.
4. **Replay:** durable shared transactional store for cross-host topology, monotonic external checkpoint, off-host append-only/WORM audit, backup/key recovery and restore rehearsal.
5. **Host controls:** resource/connection limits, request body limits, HTTP rate limiting, read-only filesystem, network egress deny to Holochain/admin/production DB, `NoNewPrivileges`, capability drop and non-root user.
6. **Observability:** metrics, structured non-sensitive logs, tamper alerts, kill switch tests, defined incident responder, clock synchronization and trust-policy expiry.
7. **Acceptance:** separate signed Git SHA and package SHA256, independent reviewer COI, complete synthetic-only end-to-end, rollback rehearsal with documented RTO/RPO, no native admissions or writes, approval to proceed to production explicitly separated.

**Current gate:** HOLD. This package does not configure, modify, or connect to a VPS.
