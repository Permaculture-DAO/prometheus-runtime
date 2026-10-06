# RAVEL Runtime Boundary

RAVEL in this repository is a **candidate shadow-underwriting reference implementation**.

It may:
- compute deterministic loss statistics from supplied scenarios;
- compare a regenerative scenario with a matched baseline;
- allocate a declared loss through a transparent capital waterfall;
- apply explicitly parameterised protection contracts;
- aggregate final exposure by economic-control group;
- report EL, VaR/Expected Shortfall, PPCI (when recoveries are supplied), RRDelta, RTE-compatible diagnostics and URBC.

It may not:
- approve credit;
- set or bind an insurance premium;
- create a capital requirement;
- certify ecological performance;
- create PRU/RAP admission;
- create investor, land, token or governance rights;
- trigger covenant/legal consequences;
- represent VRRC as admitted.

## Controlling boundary

**Evaluation, not certification. Shadow underwriting, not underwriting approval.**

The runtime validates declared scenario probabilities without rescaling them and rejects optimistic structural errors such as mitigated loss greater than gross loss. Missing evidence is never allowed to create a positive VRRC. In v0.1, `VRRC = 0` and `vrrc_status = not_admitted`.

All outputs remain subordinate to the signed Prometheus canon, the current successor candidate, MRV evidence, governance/PRMF, legal review and independent actuarial/underwriting review.

## Architecture follow-up — three bounded work items (2026-10-06)

### 1. Internal candidate gate/evidence engine and Risk Record

The architecture intake is context, not an adopted state vocabulary. Under the
steward's temporary assignment during Claude's absence, canon candidate commit
`0857425c14179d4f063953f74dc7fcc5b47dc1c8` proposes the ordinary methodological
vocabulary in RAVEL_FORMAL_SPEC_v0.1 section 13. This is not ratification.
`app/controls.py` derives a pure shadow evaluator and typed transitions from
that proposal. Do not convert GREEN/YELLOW/RED or a caller boolean to PASSED.
`/v1/gates` remains documentary; `/v1/runtime/evaluate` remains a review-package
builder, not PRU computation. No route or database schema is changed.

Candidate contract for Claude's return review (no production enum or route added):
- gate record: stable gate UID, specification/version/hash, defined use,
  prerequisite UIDs, evidence references/hashes, decision reference and reviewer,
  effective time/expiry, state, reasons and superseded decision reference;
- evaluate with an explicit `as_of` input, never an implicit current clock;
  reject duplicate/unknown gate IDs, dangling dependencies, cycles and invalid
  dates; use topological prerequisite order and stable UID ordering for output;
- permit only explicitly passed, in-scope, unexpired prerequisites with intact
  references; no output grants financial/legal authority or creates evidence;
- suggested lifecycle: UNSPECIFIED -> SPECIFIED -> READY_FOR_TEST -> PASSED/FAILED;
  PASSED -> SUSPENDED/EXPIRED on review/invalidation/expiry. Requalification goes
  through READY_FOR_TEST with new evidence and a superseding decision, not a
  direct SUSPENDED/EXPIRED -> PASSED. This edge policy is PROPOSED, not adopted;
- evidence draft sequence RAW -> IDENTIFIED -> PROVENANCE_BOUND -> QA_QC_CHECKED
  -> REVIEWABLE -> VERIFIED_INDICATOR_CANDIDATE -> ADMISSIBLE/REJECTED.
  No status inheritance into PRU/RAVEL/RAP/legal eligibility; those are separate
  gate evaluations, not a single upward evidence enum. Preserve rejected records.

Acceptance matrix after source PR: every allowed edge, every skipped/reversed
edge, missing decision, unknown evidence, stale hashes, rejected evidence,
expiry at the exact boundary, suspension cascade, dependency cycles, duplicate
IDs, input-order independence, repeated evaluation, caller-forged PASSED,
and an upstream failure preventing all materially dependent advancement.
The candidate specifies as_of >= expiry and prohibits future decisions.
The evaluator binds each declared decision to a canonical snapshot SHA256,
checks evidence hashes, explicit scope/validity and revocation references, then
cascades blocked prerequisites. Unknown/untyped or REJECTED evidence states
block even if the content hash matches. Non-rejected evidence is not thereby
admissible: stage requirements remain the declared specification's review policy,
not an inferred upward promotion. A forged PASSED without a matching decision
snapshot fails. Both catalogs are caller-declared too: forging the entire
snapshot/catalog together is outside this integrity check, not authentication.
Custody, reviewer qualifications, appeal and legal authority are not implemented.
Output always says references are not authenticated and denies authority,
certification, capital/underwriting admission and rights.

`ShadowRiskRecord` in existing ravel_schemas.py is an internal intake envelope
for declared risk, subject, hazard/exposure/vulnerability, financial state,
model/evidence/bearers, assumptions and missing data. It rejects extra rating or
human-weight fields, coercion of authority flags and nonzero VRRC. It neither
verifies nor stores a new record type. Machine-schema lifting to canonicals waits
for textual freeze; no nine-service architecture is introduced.

Net addition: one pure internal controls module and one exhaustive test module;
existing schema/docs/CI amended. Justification: missing deterministic gate checks
and lifecycle regressions in the reconciled gap map. Removal trigger: remove this
prototype if the reviewed source rejects its vocabulary or an existing control
component provides the same semantics. Cross-review remains pending Claude.

### 2. PRU zero conditions and deterministic golden replay

`app/pru.py` is a pure internal synthetic arithmetic helper, not an HTTP service.
Its zero-uplift specialization is derived from the signed controlling expression:
V_base * LegalGate * MRVGate * (1 + 0 * g(Z)) * Conf_total.
No confidence estimator, Z method, governance uplift ceiling or site valuation
is implemented. Uplift is always disabled and capital value is always policy-zero,
explicitly not a measurement or admission. A caller's gates are not verified.

Numbers are explicit decimal strings; missing values are explicit null. Unknown
remains unknown with shadow_value=null, never imputed zero; known zero flags are
retained separately. Binary gates, finite/nonnegative domains, bounded g(Z)/Conf,
extra authority/weight fields and omitted fields are checked fail-closed.
Fixed Decimal context (50 digits, HALF_EVEN) and canonical sorted UTF-8 JSON
provide reproducibility within this version. Rounding is diagnostic, not a
financial settlement convention.

Golden synthetic input (100, gates 1/1, declared uplift .9, score 1, confidence .8)
produces shadow 80, effective uplift 0 and capital policy-value 0. Input SHA256
is frozen in the test; expected output is literal, not generated by the function
under test. Mutate each of the four controlling zero factors; verify zero and
its reason. Mutate input, expected output or method version; replay must fail.

This is a frozen calculation-bundle replay, NOT full evidence/authority replay,
not cross-language parity and not independent calibration. The release manifest
pins code; full source/decision snapshot replay waits for the gate-source contract.

### 3. Holochain versus simpler store

See ops RAVEL_MODEL_GOVERNANCE_v0.1.md for the threat model, fair benchmark and
conditional retain/simplify decision. Do not infer speed from total sweettest
duration or promote a local SQL append log to independent distributed assurance.

## Local audit hardening — 2026-10-05

Shadow API inputs require horizon, model version and non-empty evidence references
for every scenario. Unknown fields and non-finite values are rejected, rather than
silently dropped. All distributions must declare the same horizon. The response
retains this provenance as **caller-declared, not verified**: equal horizon alone
does not establish causal comparability, compatible currencies or discounting.
Recovery values must already follow the caller's declared PV convention; the engine
does not verify or compute discounting. RRDelta remains a synthetic diagnostic.

Protection factors are mandatory; no missing factor implies perfect protection.
Self-transfers, duplicate contracts and contradictory common-control mappings are
rejected. Every final bearer requires an economic-group mapping. Incomplete
allocation/residual exposure prevents URBC success; it must not be reported as
verified diversification. Loss-conservation violations stop the API response.
Roundoff-only residuals within the declared numerical tolerance are not material
unallocated exposures. Chained protection/reinsurance is rejected in either JSON
order: it requires a separate explicit ordering model, not implicit array order.

Net additions: HTTP regression cases and explicit provenance output are justified
by reproduced false-positive diagnostics. No new capital-facing capability.
