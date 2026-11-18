# Ω Beyond-TRL — isolated shadow candidate (M6)

**Not Canon. Not production. Not a Holochain DNA change.**

This tree is an isolated Python research adapter copied from the verified M5
handoff. It is intentionally **not imported by FastAPI, bridge, runtime S4–S6,
or Holochain**. `HostStageConfig.enabled` defaults to `False`, and an explicit
host-controlled trust store is required even for synthetic advisory evaluation.

A result `ELIGIBLE_FOR_REVIEW` means only synthetic advisory evaluation. It never
means `admissible`, signed governance approval, legal/ecological attestation,
Holochain entry, capital authorization or deployment admission.

## Run in repo checkout

```bash
python -m pip install -r experiments/omega_btrl/requirements-test.txt
cd experiments/omega_btrl
PYTHONPATH=. python -m pytest -q
# Native S4/S5/S6 continue to run from repo root as in .github/workflows/ci.yml
```

## Governance and test boundaries

- Signed active Canon: `v1.1.2-genesis`, subject to independent verification.
- Registered private agent orchestration: `PRM-META-OMEGA-001@1.2.0`,
  noncanonical; source content is deliberately **not copied here**.
- Architecture PR #18: OPEN DRAFT at preparation, not controlling Canon.
- Original M4 TLC model is included for traceability; no formal Python refinement proof.
- `snapshots/s6_synthetic_evidence_batch.json` is an exact pinned GitHub
  synthetic fixture; tests fail if upstream bytes drift. No real MRV data.
- This module is disabled by default; **no runtime endpoint is mounted**.
- No live signing keys, database migrations or Holochain bundle changes.

A future PR needs independent review, branch CI receipt, and custodian sign-off.
