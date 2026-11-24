# TERRA RC2 — native runtime integration candidate

Status: TEST_ONLY / HOLD_REAL / HOLD_PRODUCTION. No production routes, database writes, Holochain commits or source admission.

## Implementation
- S3: contracts/terra.property.fixture.schema.json, bounded fixture envelope; runtime core additionally checks date, decimal, positive acreage and USD precision.
- S4: app.terra_property.adapter_descriptor() and run_fixture() implement an isolated disabled-by-default offline adapter. Not registered in the production adapter list or intake endpoints.
- S5: app.terra_property_core is the sole RC1 normalization implementation; original CLI delegates to it. Preserve the RC1 semantic hash format.
- S6: existing app.evidence_batch builder, hash and verifier used for property event references. Property-specific namespace avoids the fixed historical batch identifier; synthetic packaging epoch is fixed, not a source timestamp. No raw observation in batch references. The separate result contains synthetic observations for local replay.
- Evidence Spine P2.2: no POST, no invented claim UID, no database or real custody. Future mapping needs legitimate claim registry, place/system context, independent review and authorization.
- Candidate adapter/source inventory: adapters/terra_source_registry.candidate.json. All nonfixture permissions, licences and retention remain UNKNOWN; no real connectors. This is inventory only, not an active permission registry.

## Local checks
From repository root:
`python3 scripts/validate_contracts.py`
`python3 scripts/s4_guard.py`
`python3 scripts/s5_guard.py`
`python3 scripts/s6_guard.py`
From services/api:
`python3 -m unittest discover -s tests -p test_terra_property.py -v`
From experiments/terra_rc1:
`python3 -m unittest -v`

RC2 tests are in the existing API test collection; do not infer remote CI success before its run completes. Schema validation is covered by the RC2 test suite. No production configuration or global gate changed.

## Next
WP01 source admission and lineage review remain open. WP04 source-specific permissions, authorised read-only adapter pilots and connector contract validation; WP05 reconcile existing workstream records in isolated authorized context; WP06 Evidence Spine mapping review. No real GIS path, paid tools, private contact harvest or financial/legal actions.
