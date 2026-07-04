# PROMETHEUS Development Runtime — Core v7.0.1 / Documentary Patch v7.0.2

**Mandatory qualifier:** development runtime; production admission gated.

The core runtime starts PostgreSQL, the evidence-candidate API and a documentary gateway. It loads the current Canonical Root, Claims Register and Gate Review. It cannot certify evidence, create PRU/RAP rights, approve governance, admit payments/capital or represent production admission.

Start with Docker Compose using `scripts/start.sh` or `scripts/start.ps1`. Holochain is an isolated, admission-gated profile and is disabled by default.

The status API explicitly exposes `runtime_stage=development`, `production_admitted=false`, `legal_admitted=false`, `market_admitted=false` and `independent_assurance=unsigned`. Canonical response: `evaluation, not certification`.


## v7.0.3 Audit Convergence control patch

The runtime remains a development runtime. The current critical path is G1 Executable Controls followed by G2 Independent Pilot Readiness. Named-institution readiness claims are prohibited. The API exposes the audit-convergence patch identifier; production, legal and market admission remain false.
