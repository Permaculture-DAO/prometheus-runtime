# ADR proposal — OMEGA-BTRL-M6 GitHub shadow-only candidate

Status: **PROPOSED, NOT RATIFIED, NOT MERGED, NOT DEPLOYED** (2026-11-18).

## Scope

Add `experiments/omega_btrl/` and a path-scoped CI workflow only.
No import from FastAPI, no runtime DB writes or migrations, no Holochain entry,
no `admissible` decision, no token/capital effects and no release-state change.

## Authority

- Signed Canon `v1.1.2-genesis` governs meaning.
- Registered private Omega orchestration `PRM-META-OMEGA-001@1.2.0`
  remains noncanonical and cannot grant deployment authority.
- `prometheus-canon` PR #18 was still draft at preparation; architecture
  proposals are not automatically controlling sources.

## Gate and rollback

- G1 needs explicit repository-owner authorization for a public draft PR;
  this local handoff **is not** that publication.
- G2: CI receipt on exact PR head; independent security/technical review,
  provenance/secret scan and license check; source custodian review.
- G3: steward-approved merge; preserve premerge commit for immediate rollback.
- G4 Holochain: **no DNA change** under this proposal; verify conductor
  compatibility separately before claiming any Holochain proof.
- G5/G6: staging plus backup/restore and human production change window.

## Falsifiability

Fail if synthetic S6 batch becomes MRV-authoritative, any real/native
admission is emitted, the existing API imports the sidecar, native guard
behavior changes, unauthorized network/db writes occur, or GitHub bytes
and CI receipts disagree with this handoff.
