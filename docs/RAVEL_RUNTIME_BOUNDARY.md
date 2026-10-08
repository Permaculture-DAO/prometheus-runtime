# Ravel Runtime Boundary

Ravel in this repository is a **candidate shadow-underwriting reference implementation**.

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

The runtime normalises supplied scenario probabilities and rejects optimistic structural errors such as mitigated loss greater than gross loss. Missing evidence is never allowed to create a positive VRRC. In v0.1, `VRRC = 0` and `vrrc_status = not_admitted`.

All outputs remain subordinate to the signed Prometheus canon, the current successor candidate, MRV evidence, governance/PRMF, legal review and independent actuarial/underwriting review.

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
