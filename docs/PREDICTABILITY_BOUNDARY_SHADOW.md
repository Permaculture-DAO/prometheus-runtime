# PRM-PRED-001 — Predictability Boundary (candidate, SHADOW)

**Authority:** candidate application implementation under `PRM-ARCH-DET-002@2.0`; NOT an amendment to the signed Genesis Canon, investment approval, financial rating, environmental certification or a change in production admission.

## Endpoint and controls

- `POST /shadow/predictability/evaluate` registers with the existing API, but **`PREDICTABILITY_SHADOW_ENABLED=false` by default**.
- When enabled, it requires the existing `WRITE_API_KEY` provided in `X-API-Key`. Without the key, it cannot be used.
- Does not write database tables, Evidence Spine, RAVEL, PRU/RAP, TRBK, legal rights, claims register, capital gates or Holochain zomes.
- Returns deterministic output for identical frozen inputs and an explicitly supplied `as_of` replay time. No hidden current-clock dependence.
- `REJECTED`: impossible time order or future observation/evaluation leakage.
- `OUT_OF_DOMAIN`: invalid location declaration or horizon beyond declared validation range.
- `STALE`: caller-declared evaluation expiry.
- `UNKNOWN`: missing evidence of independent performance or rights.
- `INSUFFICIENT_SKILL`: declared skill metric fails declared threshold.
- `SHADOW_ONLY`: inputs pass **caller-declared** checks, NOT scientific proof or certified support.

## Non-verified fields

SHA-256 values, declared independent holdouts, model skill, baselines, data licences and geospatial flags are only syntactically screened/caller asserted. Authenticity, evidence custody, valid rights and scientific calibration are **not verified** by this candidate. Server-owned thresholds, signed evidence and independent review are separate release prerequisites.

## Science

Zhang et al. (2026), DOI: `10.1007/s00376-026-5621-8`, propose an estimated upper limit of **129 ± 7 days** for *idealized internal atmospheric predictability*. Neither that value nor 14 + 57 + 57 days is a validated production forecast horizon; it cannot be applied mechanically to land values, crop yields, credit performance or ecological outcomes.

For land underwriting, use domain-/site-/horizon-specific skill estimates, independent holdouts, proper baselines, forecast calibration, and separate scenario logic. No output can override existing G0–G7, title, water-rights, insurance, CAPEX or human review gates.

## Release gates

1. Compare branch with active registry and open PRs; review source authority.
2. Run test suite, security guards and integrity manifest verification. Reconcile local WSL/GitHub mirrors and hashes.
3. Review negative tests with scientific reviewer, runtime maintainer and legal/capital steward.
4. Keep feature disabled in production; explicit rollout and rollback require human authorization.
5. Validate empirical forecast skill before any public claim or application source promotion.
6. Canon amendment only by separate proposal and ratification, **not** by deployment.

**Status:** `proposed_application / non_authoritative / shadow_only`.
