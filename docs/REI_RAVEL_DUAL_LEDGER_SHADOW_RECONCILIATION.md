# PROMETHEUS REI — RAVEL two-ledger integrity adapter
**Engineering candidate v0.1 · 2026-10-17 · SHADOW / NON-AUTHORITATIVE**

This candidate stacks on [runtime Draft #32](https://github.com/Permaculture-DAO/prometheus-runtime/pull/32), which stacks on real-estate Draft #31 and signed land-readiness Draft #26. The signed Canon and AETERNA / RAVEL sources remain independent. [Canon source REI Draft](https://github.com/Permaculture-DAO/prometheus-canon/pull/26) is a separate PROPOSED/NOT ADOPTED application source; source reference is not authority.

## Scope and call

`app.rei_ravel_ledger_shadow.evaluate_ledger_consistency(payload)` checks only the internal arithmetic of caller-declared loss/transfer snapshots. It does NOT run RAVEL probability models, create/verify a RAVEL risk object, authenticate evidence or bind any insurance contract. No routes, database, persistence or REAL Holochain write path.

Exact fields: `schema_version`, `project_id`, `as_of`, `currency`, `generation`, `allocation`, `transfers`. Version is `rei-ravel-two-ledger-shadow/v1`. Every array is bounded to at most 100 entries; at least one generation and allocation required; each event/bearer ID is exact Unicode NFC bounded text; amount is explicit bounded decimal string or null; currency is three uppercase ASCII characters; as_of is strictly YYYY-MM-DDTHH:MM:SSZ.

- `generation`: unique `event_id`, `risk_id`, `gross_loss`, `prevented_loss`, `residual_loss`, `evidence_ids`.
- `allocation`: unique event+bearer pair, with `before_transfer`, `after_transfer`, `evidence_ids`.
- `transfers`: unique ID, event, `from_bearer_id`, `to_bearer_id`, `amount`, `evidence_ids`.

The proposed arithmetic invariants are **subject to independent AETERNA/RAVEL methodological review**, and are evaluated only for consistent event, currency, date and units:

1. `gross_declared - prevented_declared == residual_declared`
2. `sum(before_by_bearer) == residual_declared`
3. `sum(after_by_bearer) == residual_declared`
4. `after_by_bearer == before_by_bearer - outgoing + incoming` for each bearer.
5. If an event is missing, a bearer is unallocated, an amount unknown, or declared event/bearer links do not reconcile, the output remains HOLD.

**Important limit:** matching these equations is **not** evidence that prevention occurred or that an insurer will pay. Prevention effectiveness, risk reduction, ultimate bearer legal identity, ability-to-pay, probability/calibration, transfer policy wording, loss scenario causal truth and evidence custody all remain NOT VERIFIED. A single bad event must HOLD the entire dossier. All output authority/capital/certification flags remain false. `GO_FOR_EXTERNAL_REVIEW` is only numeric/internal reconciliation readiness.

The SHADOW v1 algorithm has an intentionally restricted additive ledger: single currency, nonnegative nominal amounts, no FX, discounting, catastrophic dependence, collateral model, deductible, probability distributions or third-party recovery estimation. It cannot claim legal/actuarial or quantitative finance validity.

## Integration boundary

A future qualified runtime integration may attach **verified** ledger evidence and hashes to existing REI `risk_ledger_links` and RAVEL objects without replacing them. Do NOT copy numeric fields into REI as authorized inputs merely because they balance. Keep RAVEL ownership and AETERNA methods; require explicit source steward approval, reviewer signature and source/algorithm version lock.

Target test: `PYTHONPATH=services/api python -m unittest discover -s services/api/tests -p 'test_rei_ravel_*.py' -v`. Tests are synthetic, not externally measured.

## Relevant professional background

Current U.S. actuarial ERM reference is **ASOP 58 Enterprise Risk Management (effective May 1, 2025)**; ASOP 47 and 46 were repealed. ASOP 47 is historical context ONLY. This U.S. framework does not establish actual coverage, counterparty ability-to-pay, legal transfer, actuarial price or assurance of this prototype. Primary sources:

- https://www.actuarialstandardsboard.org/asops/enterprise-risk-management-58/
- https://www.actuarialstandardsboard.org/asops/asop-nos-46-47-risk-evaluation-risk-treatment-repealed/
- Historical ASOP 47 (not current): https://www.actuarialstandardsboard.org/asops/risk-treatment-enterprise-risk-management/

**GO:** source-controlled research and reproducible internal consistency.  
**HOLD:** independent actual risk records, actuarial methodology, insurance pricing, legal risk transfer, source adoption, financial underwriting and production.
