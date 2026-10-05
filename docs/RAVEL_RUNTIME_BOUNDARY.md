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

The runtime normalises supplied scenario probabilities and rejects optimistic structural errors such as mitigated loss greater than gross loss. Missing evidence is never allowed to create a positive VRRC. In v0.1, `VRRC = 0` and `vrrc_status = not_admitted`.

All outputs remain subordinate to the signed Prometheus canon, the current successor candidate, MRV evidence, governance/PRMF, legal review and independent actuarial/underwriting review.
