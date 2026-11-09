# Claims Registry projection v0.1

This runtime file is a **subordinate consumer projection** of the signed PROMETHEUS Claims Registry snapshot.

## Upstream

- Signed registry repository: `Permaculture-DAO/prometheus-canonical-releases`
- Path: `registries/claims/v0.1-mapping-only/claims-registry.v0.1-mapping-only.json`
- Registry merge commit: `0151e3f869a819b0833a046f30a92036fe0e3b4d`
- Snapshot SHA-256: `7b2f9b4aec2df0c1ca2262ba27725652b4c119daea754165b623e677e756edb4`
- Signature fingerprint: `D20DFF6CBE331B3A4109DF848C8CB0D48C7F60DA`

## Boundary

This projection does **not**:
- replace `config/canonical_release.json`;
- change the runtime internal v7.0.x documentary lineage;
- override `config/semantic_claims_vnext.json`;
- admit C-002, C-005, C-008 or C-009;
- enable TRBK/payment/investment pathways;
- create legal, market, production or empirical admission;
- make runtime authoritative.

The governing Canon remains signed `v1.1.2-genesis`; the runtime remains subordinate and mapped-not-merged.

## Runtime enforcement

`scripts/validate_runtime.py` fail-closes if the pinned signed-registry hash, 8 mapping-only set, 4 HOLD set, or non-authoritative boundary drifts.
